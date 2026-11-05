#!/usr/bin/env python3
"""Real CPU Ollama acceptance in a new Linux user/network namespace.

Downloads nothing. Requires a supplied runtime and already-downloaded weights.
Never attaches disks, modifies Windows, installs packages or starts the GUI.
The output explicitly limits its claims to adapter/provider acceptance.
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
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def digest(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024**2), b""):
            result.update(chunk)
    return result.hexdigest()


def worker(args) -> dict:
    # Only loopback exists in the new namespace. Use ioctl because minimal
    # containers may disallow netlink sockets even inside a new user namespace.
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        request = struct.pack("16sH14s", b"lo", 0, b"")
        flags = struct.unpack("16sH14s", fcntl.ioctl(sock, 0x8913, request))[1]
        fcntl.ioctl(sock, 0x8914, struct.pack("16sH14s", b"lo", flags | 1, b""))
    interfaces = sorted(line.split(":", 1)[0].strip()
                        for line in Path("/proc/net/dev").read_text().splitlines()
                        if ":" in line)
    if interfaces != ["lo"]:
        raise RuntimeError("Acceptance refuses a namespace with external interfaces")
    with socket.socket() as sock:
        sock.settimeout(.5)
        try:
            sock.connect(("1.1.1.1", 443))
        except OSError as exc:
            blocked = str(exc)
        else:
            raise RuntimeError("External networking is unexpectedly reachable")

    os.environ["MJON_NATIVE_OS"] = "1"
    from mjon_os.first_boot import provision_user_config
    from mjon_os.jarvis_probe import verify_jarvis_ollama
    from mjon_os.local_inference import OllamaClient, InferenceUnavailable
    from mjon_os.provider_health import diagnose, preload, preload_from_config
    from mjon_os.ollama_policy import physical_memory
    from mjon_os.offline_payload import validate_payload
    import psutil
    if args.payload:
        validate_payload(args.payload)

    evidence = {"kind": "real-model-network-isolated-provider-test",
                "desktop_or_physical_hardware_test": False,
                "interfaces": interfaces, "external_connect_failure": blocked,
                "physical_ram_bytes": physical_memory(), "model": args.model,
                "binary_sha256": digest(args.ollama), "checks": {}}
    revision = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                              capture_output=True, text=True, check=False)
    evidence["source_commit"] = revision.stdout.strip() if revision.returncode == 0 else None
    status = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT,
                            capture_output=True, text=True, check=False)
    evidence["source_worktree_dirty"] = bool(status.stdout.strip()) if status.returncode == 0 else None
    sources = ("mjon_os/first_boot.py", "mjon_os/local_inference.py", "mjon_os/provider_health.py",
               "mjon_os/jarvis_probe.py", "mjon_os/ollama_policy.py", "dodaios/plugins/brain/ollama.py",
               "dodaios/brain/manager.py", "dodaios/brain/resolver.py", "mjon_os/offline_payload.py",
               "mjon_os/ai_fabric.py", "dodaios/local_models/health_monitor.py",
               "dodaios/local_models/assistant_test.py", "scripts/mjon_offline_acceptance.py")
    evidence["source_file_sha256"] = {path: digest(ROOT / path) for path in sources}
    checks = evidence["checks"]
    env = {key: value for key, value in os.environ.items() if "proxy" not in key.lower()}
    env.update(OLLAMA_HOST="127.0.0.1:11434", OLLAMA_MODELS=str(args.models),
               OLLAMA_NO_CLOUD="1", OLLAMA_NUM_PARALLEL="1", OLLAMA_MAX_LOADED_MODELS="1",
               OLLAMA_VULKAN="0", CUDA_VISIBLE_DEVICES="-1")

    with tempfile.TemporaryDirectory(prefix="mjon-real-acceptance-") as tmp:
        directory = Path(tmp)
        config = directory / "dodaios.toml"
        provision_user_config(ROOT / "dodaios.toml.example", config, directory / "data")
        os.environ.update(JARVIS_CONFIG=str(config), JARVIS_DATA_DIR=str(directory / "data"),
                          MJON_AI_OS_CONFIG_ROOT=str(directory))
        # Deliberately poison proxies to prove both clients ignore them.
        os.environ.update(HTTP_PROXY="http://127.0.0.1:9", HTTPS_PROXY="http://127.0.0.1:9",
                          ALL_PROXY="http://127.0.0.1:9", NO_PROXY="",
                          http_proxy="http://127.0.0.1:9", https_proxy="http://127.0.0.1:9",
                          all_proxy="http://127.0.0.1:9", no_proxy="")
        server = None
        client = OllamaClient(ram_bytes=8*1024**3)
        samples = []
        stopped = threading.Event()
        def sample():
            while not stopped.wait(.25):
                if server is None:
                    continue
                try:
                    parent = psutil.Process(server.pid)
                    processes = [parent, *parent.children(recursive=True)]
                    samples.append(sum(p.memory_info().rss for p in processes))
                except psutil.Error:
                    pass
        def start():
            process = subprocess.Popen([str(args.ollama), "serve"], env=env,
                                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            for _ in range(60):
                try:
                    client.models()
                    return process
                except InferenceUnavailable:
                    if process.poll() is not None:
                        raise RuntimeError("Ollama exited before readiness")
                    time.sleep(.5)
            process.terminate()
            process.wait(timeout=20)
            raise RuntimeError("Ollama did not start")
        monitor = threading.Thread(target=sample, daemon=True)
        try:
            server = start()
            monitor.start()
            evidence["ollama_version"] = client._request("/api/version")["version"]
            evidence["model_inventory"] = client._request("/api/tags")["models"]
            print("Real acceptance: runtime and weights available in isolated network", flush=True)
            checks["download_visible"] = args.model in client.models()
            warmed = preload(client, model=args.model)
            print("Real acceptance: preload returned", flush=True)
            checks["preload_is_unverified"] = warmed.state == "loaded_unverified" and not warmed.ready
            start_time = time.monotonic()
            reply = client.ask("Respondé en español: cuánto es dos más dos?", model=args.model)
            print("Real acceptance: native adapter returned completed text", flush=True)
            evidence["adapter_reply"] = reply
            evidence["quality_checks"] = {"basic_arithmetic": bool(re.search(r"\b(cuatro|4)\b", reply.casefold()))}
            evidence["quality_limit"] = "A single arithmetic smoke check, not a reasoning or agent benchmark. Transport readiness is reported separately."
            evidence["adapter_latency_s"] = round(time.monotonic()-start_time, 3)
            checks["adapter_nonempty_completed_response"] = bool(reply.strip())
            checks["adapter_verified"] = diagnose(client, model=args.model, verify_generation=True).ready
            before = time.monotonic()
            status = verify_jarvis_ollama(config)
            print("Real acceptance: actual brain probe returned " + status.state, flush=True)
            evidence["jarvis_brain_status"] = status.to_dict()
            evidence["jarvis_brain_latency_s"] = round(time.monotonic()-before, 3)
            checks["actual_jarvis_brain_completed"] = status.ready
            checks["proxy_poisoning_ignored"] = status.ready
            async def tool_probe():
                from dodaios.plugins.brain.ollama import OllamaBrain
                from dodaios.core.protocols import BrainMessage, BrainRequest
                brain = OllamaBrain(model=args.model)
                request = BrainRequest(
                    messages=(BrainMessage("user", "Call get_lab_status with lab set to chemistry."),),
                    tools=({"name": "get_lab_status", "description": "Read a laboratory status.",
                            "input_schema": {"type": "object", "properties": {
                                "lab": {"type": "string"}}, "required": ["lab"]}},),
                    max_tokens=96, temperature=0, stream=True)
                calls = []
                try:
                    async with asyncio.timeout(90):
                        async for delta in brain.complete(request):
                            if delta.tool_call:
                                calls.append(delta.tool_call)
                    return calls
                finally:
                    if brain._client is not None:
                        await brain._client.close()
            calls = asyncio.run(tool_probe())
            evidence["tool_call_output_not_executed"] = calls
            evidence["quality_checks"]["tool_schema"] = any(
                call.get("name") == "get_lab_status" and call.get("input") == {"lab": "chemistry"}
                for call in calls)
            try:
                client.ask("Hello", model="mjon-missing-model:nonexistent")
            except InferenceUnavailable:
                checks["missing_model_refused"] = True
            else:
                checks["missing_model_refused"] = False
            evidence["resident_models"] = client._request("/api/ps")["models"]
            server.terminate()
            server.wait(timeout=20)
            checks["stopped_server_not_green"] = not diagnose(client, verify_generation=True).ready
            server = start()
            startup = directory / "ollama-preload.json"
            startup.write_text(json.dumps({"enabled": True, "model": args.model, "keep_alive": "5m"}))
            checks["startup_preload_after_restart"] = preload_from_config(startup, client=client).state == "loaded_unverified"
            checks["recovery_after_restart"] = diagnose(client, model=args.model, verify_generation=True).ready
        finally:
            stopped.set()
            if monitor.is_alive():
                monitor.join(timeout=2)
            if server is not None and server.poll() is None:
                server.terminate()
                server.wait(timeout=20)
        evidence["sampled_peak_daemon_runner_aggregate_rss_bytes"] = max(samples, default=0)
        evidence["memory_measurement_limit"] = "Sampled aggregate RSS of daemon+runner only; excludes KDE, GUI and probe subprocess. Shared pages may be counted twice. Not an 8 GiB hardware benchmark."
    if args.payload:
        validate_payload(args.payload)
        checks["immutable_payload_unchanged"] = True
    evidence["infrastructure_passed"] = bool(checks) and all(checks.values())
    evidence["passed"] = evidence["infrastructure_passed"] and all(evidence.get("quality_checks", {}).values())
    return evidence


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ollama", type=Path, required=True)
    parser.add_argument("--models", type=Path, required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--payload", type=Path, help="Also verify immutable image payload before and after inference")
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    args.ollama, args.models, args.output = args.ollama.resolve(), args.models.resolve(), args.output.resolve()
    if not args.ollama.is_file() or not args.models.is_dir() or args.output.exists():
        parser.error("Supply existing runtime/weights and a new output path")
    if not args.worker:
        command = ["unshare", "-Urn", sys.executable, str(Path(__file__).resolve()),
                               "--worker", "--ollama", str(args.ollama), "--models", str(args.models),
                               "--model", args.model, "--output", str(args.output)]
        if args.payload:
            command.extend(["--payload", str(args.payload.resolve())])
        return subprocess.run(command, timeout=600).returncode
    result = worker(args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"passed": result["passed"], "checks": result["checks"], "output": str(args.output)}))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
