#!/usr/bin/env python3
"""Reproduce immutable, foreign-owned blob/profile behavior on a disposable CI host.

Run only in a new network namespace, with the supplied test user already
created by the workflow. The runtime must come from the audited ISO artifact.
Root controls fixtures; the actual provider acceptance runs as the test user.
"""
from __future__ import annotations
import argparse
import asyncio
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import pwd
import socket
import struct
import subprocess
import sys
import time
from urllib.error import HTTPError
from urllib.request import build_opener, ProxyHandler, Request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--payload", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--probe-user", required=True)
    args = parser.parse_args()
    if os.geteuid() != 0:
        parser.error("The disposable fixture controller needs root; the provider must not.")
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        request = struct.pack("16sH14s", b"lo", 0, b"")
        flags = struct.unpack("16sH14s", fcntl.ioctl(sock, 0x8913, request))[1]
        fcntl.ioctl(sock, 0x8914, struct.pack("16sH14s", b"lo", flags | 1, b""))
    interfaces = sorted(line.split(":", 1)[0].strip()
                        for line in Path("/proc/net/dev").read_text().splitlines() if ":" in line)
    if interfaces != ["lo"]:
        raise RuntimeError("Refusing a controller namespace with external interfaces")
    os.environ["MJON_NATIVE_OS"] = "1"
    from mjon_os.offline_payload import _files, validate_payload
    manifest = validate_payload(args.payload)
    user = pwd.getpwnam(args.probe_user)
    if user.pw_uid == 0:
        raise RuntimeError("The provider probe must have a different, unprivileged UID")
    binary = args.payload / "runtime/bin/ollama"
    binary_hash = hashlib.file_digest(binary.open("rb"), "sha256").hexdigest()
    if binary_hash != "4a525117528467da41be4188ef8efbc3dbbca9da420fb25cd61cf49d104732fd":
        raise RuntimeError("The artifact does not contain the audited runtime")
    blobs = args.payload / "models/blobs"
    if any(path.stat().st_uid != 0 for path in blobs.iterdir()):
        raise RuntimeError("The fixture weights must belong to root")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    opener = build_opener(ProxyHandler({}))
    base_env = {**os.environ, "OLLAMA_HOST": "127.0.0.1:11434", "OLLAMA_NO_CLOUD": "1",
                "OLLAMA_NUM_PARALLEL": "1", "OLLAMA_MAX_LOADED_MODELS": "1",
                "OLLAMA_VULKAN": "0", "CUDA_VISIBLE_DEVICES": "-1", "MJON_NATIVE_OS": "1"}
    model = manifest["model"]
    def as_user(command):
        return ["runuser", "-u", args.probe_user, "--", "env",
                "GIT_CONFIG_COUNT=1", "GIT_CONFIG_KEY_0=safe.directory",
                "GIT_CONFIG_VALUE_0=" + str(ROOT), *command]
    def request(route, body=None):
        req = Request("http://127.0.0.1:11434" + route,
                      data=json.dumps(body).encode() if body else None,
                      headers={"Content-Type": "application/json"})
        try:
            with opener.open(req, timeout=180) as response:
                return response.status, json.load(response)
        except HTTPError as exc:
            return exc.code, json.loads(exc.read(8192))
    @contextmanager
    def server(models, unprivileged, log_name):
        command = [str(binary), "serve"]
        if unprivileged:
            command = as_user(["OLLAMA_MODELS=" + str(models), *command])
        env = {**base_env, "OLLAMA_MODELS": str(models)}
        with (args.output_dir / log_name).open("w") as log:
            process = subprocess.Popen(command, env=env, stdout=log, stderr=log, cwd=ROOT)
            try:
                for attempt in range(120):
                    try:
                        if request("/api/version")[0] == 200:
                            break
                    except OSError:
                        pass
                    if process.poll() is not None:
                        raise RuntimeError("The fixture daemon exited")
                    time.sleep(.5)
                else:
                    raise RuntimeError("The fixture daemon did not start")
                yield
            finally:
                if process.poll() is None:
                    process.terminate()
                process.wait(timeout=30)
        time.sleep(.5)
    first_store = Path(user.pw_dir) / "mjon-red-models"
    subprocess.run(as_user([sys.executable, "-m", "mjon_os.offline_payload",
                            "--payload", str(args.payload), "--initialize-store", str(first_store)]),
                   cwd=ROOT, env=base_env, check=True)
    with server(first_store, True, "red-daemon.log"):
        status, body = request("/api/create", {"model": "mjon-readonly-red",
                                             "from": model, "parameters": {"num_ctx": 2048},
                                             "stream": False})
    red = {"http_status": status, "body": body, "provider_uid": user.pw_uid,
           "payload_blob_uid": 0, "interfaces": interfaces}
    (args.output_dir / "red-profile-create.json").write_text(json.dumps(red, indent=2) + "\n")
    print("MJON_OWNERSHIP_RED " + json.dumps(red), flush=True)
    # Planned repair: derive the default bounded profile while staging is writable.
    with server(args.payload / "models", False, "prebake-daemon.log"):
        from dodaios.brain.ollama_profiles import ensure_profile
        from dodaios.core.config import OllamaModelOptions
        alias = asyncio.run(ensure_profile(
            "http://127.0.0.1:11434", model,
            OllamaModelOptions(num_ctx=2048, num_thread=4, think=False)))
    manifest["files"] = _files(args.payload)
    (args.payload / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    validate_payload(args.payload)
    second_store = Path(user.pw_dir) / "mjon-green-models"
    subprocess.run(as_user([sys.executable, "-m", "mjon_os.offline_payload",
                            "--payload", str(args.payload), "--initialize-store", str(second_store)]),
                   cwd=ROOT, env=base_env, check=True)
    record_path = Path(user.pw_dir) / "mjon-real-provider.json"
    command = as_user([sys.executable, str(ROOT / "scripts/mjon_offline_acceptance.py"),
                       "--worker", "--ollama", str(binary), "--models", str(second_store),
                       "--payload", str(args.payload), "--require-foreign-owned-payload",
                       "--model", model, "--output", str(record_path)])
    tested = subprocess.run(command, cwd=ROOT, env=base_env, check=False, timeout=600)
    green = json.loads(record_path.read_text()) if record_path.exists() else {"passed": False}
    (args.output_dir / "green-real-provider.json").write_text(json.dumps(green, indent=2) + "\n")
    regular_weight_bytes = sum(path.stat().st_size for path in (second_store / "blobs").iterdir()
                               if not path.is_symlink())
    weight_names = [path.name for path in blobs.iterdir() if path.stat().st_size >= 1024**2]
    linked_weights = bool(weight_names) and all(
        (second_store / "blobs" / name).is_symlink()
        and (second_store / "blobs" / name).resolve() == (blobs / name).resolve()
        for name in weight_names)
    result = {"kind": "real-root-owned-payload-regression", "provider_uid": user.pw_uid,
              "binary_sha256": binary_hash, "prebaked_alias": alias, "red": red,
              "green_exit_code": tested.returncode, "green_passed": green.get("passed") is True,
              "private_regular_blob_bytes": regular_weight_bytes, "weights_stay_linked": linked_weights,
              "scope": "Disposable native CI fixture, not a VM or physical hardware test"}
    result["passed"] = (status >= 400 and "chtimes" in str(body).lower()
                        and tested.returncode == 0 and green.get("passed") is True
                        and regular_weight_bytes < 1024**2 and linked_weights)
    (args.output_dir / "ownership-summary.json").write_text(json.dumps(result, indent=2) + "\n")
    print("MJON_OWNERSHIP_SUMMARY " + json.dumps(result), flush=True)
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
