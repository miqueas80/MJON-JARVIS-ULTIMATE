#!/usr/bin/env python3
"""Exercise a real native BrainManager text turn with no registered tools.

Downloads nothing. Requires existing CPU Ollama binaries and model weights.
Runs in an isolated Linux network namespace; no GUI or host disks are opened.
This is not acceptance of tools, the desktop UI, voice, or physical hardware.
"""
from __future__ import annotations

import argparse
import asyncio
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import socket
import struct
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def worker(args) -> dict:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        request = struct.pack("16sH14s", b"lo", 0, b"")
        flags = struct.unpack("16sH14s", fcntl.ioctl(sock, 0x8913, request))[1]
        fcntl.ioctl(sock, 0x8914, struct.pack("16sH14s", b"lo", flags | 1, b""))
    interfaces = sorted(line.split(":", 1)[0].strip()
                        for line in Path("/proc/net/dev").read_text().splitlines()
                        if ":" in line)
    if interfaces != ["lo"]:
        raise RuntimeError("Acceptance requires only loopback in a new network namespace")
    with socket.socket() as sock:
        sock.settimeout(.5)
        try:
            sock.connect(("1.1.1.1", 443))
        except OSError as exc:
            blocked = str(exc)
        else:
            raise RuntimeError("External networking is unexpectedly reachable")

    os.environ.update(MJON_NATIVE_OS="1", HTTP_PROXY="http://192.0.2.1:9",
                      HTTPS_PROXY="http://192.0.2.1:9", ALL_PROXY="http://192.0.2.1:9",
                      NO_PROXY="")
    from mjon_os.first_boot import provision_user_config
    from mjon_os.local_inference import OllamaClient, InferenceUnavailable

    with tempfile.TemporaryDirectory(prefix="mjon-manager-") as tmp:
        private = Path(tmp)
        config_file = private / "dodaios.toml"
        provision_user_config(ROOT / "dodaios.toml.example", config_file, private / "data")
        os.environ.update(JARVIS_CONFIG=str(config_file), JARVIS_DATA_DIR=str(private / "data"),
                          MJON_AI_OS_CONFIG_ROOT=str(private))
        env = {**os.environ, "OLLAMA_HOST": "127.0.0.1:11434", "OLLAMA_MODELS": str(args.models),
               "OLLAMA_NO_CLOUD": "1", "OLLAMA_NUM_PARALLEL": "1", "OLLAMA_MAX_LOADED_MODELS": "1",
               "OLLAMA_VULKAN": "0", "CUDA_VISIBLE_DEVICES": "-1"}
        log_path = private / "ollama.log"
        with log_path.open("w") as log:
            server = subprocess.Popen([str(args.ollama), "serve"], env=env, stdout=log, stderr=log)
            try:
                client = OllamaClient()
                for attempt in range(120):
                    try:
                        if client.models():
                            break
                    except InferenceUnavailable:
                        pass
                    if server.poll() is not None:
                        raise RuntimeError("The supplied Ollama daemon exited")
                    time.sleep(.5)
                else:
                    raise RuntimeError("The supplied daemon has no downloaded local model")
                inventory = client._request("/api/tags")["models"]

                async def generate():
                    from dodaios.core.config import load_config
                    from dodaios.core.bus import EventBus
                    from dodaios.brain.manager import BrainManager
                    manager = BrainManager(config=load_config(config_file=config_file),
                                           bus=EventBus(), tools={})
                    before = log_path.read_text().count("/v1/chat/completions")
                    start = time.monotonic()
                    try:
                        async with asyncio.timeout(150):
                            reply = await manager.generate(
                                "Resumí en una frase: el laboratorio conserva sus documentos "
                                "en la computadora y trabaja sin conexión.", use_history=False,
                                publish_response=False, force_output_language="es")
                        return {"reply": reply, "latency_s": round(time.monotonic() - start, 3),
                                "active_provider": manager.active_provider,
                                "failed_providers": manager.failed_providers(),
                                "http_chat_requests": log_path.read_text().count("/v1/chat/completions") - before,
                                "system_prompt_characters": len(manager._build_system_prompt()),
                                "tools_registered": len(manager._tools)}
                    finally:
                        await manager.aclose()

                result = asyncio.run(generate())
                result["resident_models"] = client._request("/api/ps")["models"]
                result["ollama_version"] = client._request("/api/version")["version"]
            finally:
                if server.poll() is None:
                    server.terminate()
                server.wait(timeout=20)
        daemon_log = log_path.read_text()

    tokens = [int(value) for value in re.findall(r"task.n_tokens = (\d+)", daemon_log)]
    contexts = [int(value) for value in re.findall(r"n_ctx_slot = (\d+)", daemon_log)]
    result.update(kind="real-manager-text-only-no-tools", interfaces=interfaces,
                  external_connect_failure=blocked, gui_test=False, physical_hardware_test=False,
                  model_inventory=inventory, binary_sha256=digest(args.ollama),
                  prompt_tokens=tokens, context_slots=contexts,
                  runner_reported_untruncated="truncated = 0" in daemon_log,
                  runner_reported_truncation=bool(re.search(r"truncated = [1-9]|truncating input", daemon_log)))
    result["source_commit"] = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    result["source_worktree_dirty"] = bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip())
    sources = ("scripts/mjon_manager_acceptance.py", "dodaios/brain/manager.py",
               "dodaios/plugins/brain/ollama.py", "mjon_os/first_boot.py", "mjon_os/ollama_policy.py")
    result["source_file_sha256"] = {path: digest(ROOT / path) for path in sources}
    result["passed"] = bool(
        result["reply"].strip() and result["http_chat_requests"] > 0
        and result["active_provider"] == "ollama" and not result["failed_providers"]
        and re.search("laboratorio|document", result["reply"], re.I)
        and result["runner_reported_untruncated"] and not result["runner_reported_truncation"]
        and tokens and contexts and max(tokens) + 256 <= min(contexts))
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ollama", type=Path, required=True)
    parser.add_argument("--models", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    args.ollama, args.models, args.output = args.ollama.resolve(), args.models.resolve(), args.output.resolve()
    if not args.ollama.is_file() or not args.models.is_dir() or args.output.exists():
        parser.error("Supply existing runtime/weights and a new output path")
    if not args.worker:
        return subprocess.run(["unshare", "-Urn", sys.executable, str(Path(__file__).resolve()),
                               "--worker", "--ollama", str(args.ollama), "--models", str(args.models),
                               "--output", str(args.output)], timeout=300).returncode
    result = worker(args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"passed": result["passed"], "latency_s": result["latency_s"],
                      "http_chat_requests": result["http_chat_requests"], "output": str(args.output)}))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
