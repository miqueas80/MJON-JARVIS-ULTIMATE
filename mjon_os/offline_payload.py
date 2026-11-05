"""Explicit, integrity-checked CPU runtime/weights payload for a Live image.

No downloader or installer runs here. A manifest verifies integrity, not the
authenticity or license of files supplied by a builder.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil

from .ollama_policy import is_cloud_model


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024**2), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _files(root: Path) -> dict[str, str]:
    files = {}
    for path in sorted(root.rglob("*")):
        if not path.resolve().is_relative_to(root.resolve()):
            raise ValueError("Offline payload contains a link outside its root")
        if path.is_file() and path.relative_to(root).as_posix() != "manifest.json":
            files[path.relative_to(root).as_posix()] = sha256(path)
    return files


def validate_payload(root: Path) -> dict:
    manifest = json.loads((root / "manifest.json").read_text())
    if manifest.get("format") != 1 or not isinstance(manifest.get("files"), dict):
        raise ValueError("Unsupported offline payload manifest")
    model = manifest.get("model", "")
    if not re.fullmatch(r"[a-zA-Z0-9._-]+:[a-zA-Z0-9._-]+", model) or is_cloud_model(model):
        raise ValueError("The initial CPU payload requires an explicit local library model tag")
    if _files(root) != manifest["files"]:
        raise ValueError("Offline payload file hashes or inventory do not match")
    if not (root / "runtime/bin/ollama").is_file():
        raise ValueError("Offline payload lacks Ollama")
    if not (root / "runtime/LICENSE").is_file():
        raise ValueError("Offline payload lacks the runtime license")
    if not list((root / "models/manifests").rglob("*")) or not (root / "models/blobs").is_dir():
        raise ValueError("Offline payload lacks model manifests or weights")
    name, tag = model.split(":")
    model_manifest = json.loads((root / "models/manifests/registry.ollama.ai/library" / name / tag).read_text())
    references = [model_manifest["config"], *model_manifest["layers"]]
    if not any(item.get("mediaType") == "application/vnd.ollama.image.model" for item in references):
        raise ValueError("The payload has no actual local model-weight layer")
    if not any(item.get("mediaType") == "application/vnd.ollama.image.license" for item in references):
        raise ValueError("The payload lacks the model license layer")
    for item in references:
        digest = item.get("digest", "")
        if not re.fullmatch(r"sha256:[a-f0-9]{64}", digest):
            raise ValueError("Invalid model blob digest")
        relative = "models/blobs/" + digest.replace(":", "-")
        if (manifest["files"].get(relative) != digest.split(":")[1]
                or (root / relative).stat().st_size != item["size"]):
            raise ValueError("Model manifest references missing or mismatched weights")
    return manifest


def create_payload(runtime: Path, models: Path, destination: Path, *, model: str,
                   runtime_version: str, archive_sha256: str) -> dict:
    """Stage caller-reviewed binaries and weights; refuse existing destinations."""
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(destination)
    if (not (runtime / "bin/ollama").is_file() or not (runtime / "LICENSE").is_file()
            or not (models / "blobs").is_dir()):
        raise ValueError("Existing runtime and downloaded weights are required")
    # Validate sources before dereferencing any symlinks during copy.
    _files(runtime / "bin")
    _files(runtime / "lib/ollama")
    _files(models)
    destination.mkdir(parents=True)
    try:
        (destination / "runtime/bin").mkdir(parents=True)
        shutil.copy2(runtime / "bin/ollama", destination / "runtime/bin/ollama")
        shutil.copy2(runtime / "LICENSE", destination / "runtime/LICENSE")
        shutil.copytree(runtime / "lib/ollama", destination / "runtime/lib/ollama",
                        ignore=shutil.ignore_patterns("cuda*", "rocm*", "vulkan*", "mlx*"))
        shutil.copytree(models, destination / "models")
        manifest = {"format": 1, "model": model, "runtime_version": runtime_version,
                    "source_archive_sha256": archive_sha256,
                    "policy": "CPU, loopback, cloud disabled; no model downloads at login",
                    "files": _files(destination)}
        (destination / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
        validate_payload(destination)
        return manifest
    except BaseException:
        shutil.rmtree(destination)
        raise


def initialize_model_store(payload: Path, store: Path) -> bool:
    """Keep weights in squashfs, copy only small writable manifests per user.

    Existing user stores are never replaced. The immutable blobs are linked so
    a Live session does not copy a gigabyte of weights into its RAM overlay.
    Profile aliases can be created in the private writable manifests directory.
    """
    if store.is_symlink():
        raise ValueError("Refusing a symlink as the per-user model store")
    if store.exists():
        if (store / "blobs").is_symlink():
            raise ValueError("Legacy blob-directory link is unsafe for generated profiles; preserve it and initialize a new store")
        if (store / ".mjon-payload-sha256").read_text().strip() != sha256(payload / "manifest.json"):
            raise ValueError("Existing model store belongs to another payload; preserve and migrate explicitly")
        return False
    validate_payload(payload)
    store.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    store.mkdir(mode=0o700)
    try:
        shutil.copytree(payload / "models/manifests", store / "manifests")
        # Ollama creates small parameter/config blobs for derived profiles.
        # Link each immutable blob individually, keeping the directory itself
        # writable so those new blobs never alter the image payload.
        (store / "blobs").mkdir()
        for blob in (payload / "models/blobs").iterdir():
            if not blob.is_file():
                raise ValueError("Model blobs must be regular files")
            (store / "blobs" / blob.name).symlink_to(blob.resolve())
        (store / ".mjon-payload-sha256").write_text(sha256(payload / "manifest.json") + "\n")
    except BaseException:
        shutil.rmtree(store)
        raise
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--payload", type=Path, required=True)
    parser.add_argument("--initialize-store", type=Path)
    args = parser.parse_args()
    if args.initialize_store:
        initialize_model_store(args.payload, args.initialize_store)
    else:
        validate_payload(args.payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
