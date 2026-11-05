"""Shared native Ollama policy; importing it never touches the network."""
from __future__ import annotations

import os
from pathlib import Path

ENDPOINT = "http://127.0.0.1:11434"
NATIVE_CONTEXT = 2048


def native_mode() -> bool:
    return os.environ.get("MJON_NATIVE_OS") == "1"


def physical_memory() -> int | None:
    try:
        for line in Path("/proc/meminfo").read_text(encoding="ascii").splitlines():
            if line.startswith("MemTotal:"):
                return int(line.split()[1]) * 1024
    except (OSError, ValueError, IndexError):
        pass
    return None


def is_cloud_model(name: str) -> bool:
    name = name.strip().casefold()
    base, separator, tag = name.rpartition(":")
    return (name.endswith(":cloud") or name.endswith("-cloud")
            or bool(separator and base.endswith("-cloud"))
            or bool(separator and tag.endswith("-cloud")))


def eligible_models(inventory: tuple[tuple[str, int | None], ...],
                    ram_bytes: int | None) -> tuple[str, ...]:
    """Known nonzero weight sizes only; reserve RAM for desktop and KV cache.

    Disk size is a conservative filter, not a measured peak-memory guarantee.
    """
    budget = int(ram_bytes * .4) if ram_bytes else None
    return tuple(name for name, size in inventory
                 if not is_cloud_model(name) and isinstance(size, int)
                 and not isinstance(size, bool) and size > 0
                 and (budget is None or size <= budget))


def native_http_options() -> dict:
    """The SDK and every native HTTP side call must ignore environment proxies."""
    return {"trust_env": False, "follow_redirects": False} if native_mode() else {}


def require_native_endpoint(root: str) -> None:
    if native_mode() and root != ENDPOINT:
        raise ValueError("Native offline Ollama requires http://127.0.0.1:11434; "
                         "remote endpoints, credentials and team proxies are not allowed.")
