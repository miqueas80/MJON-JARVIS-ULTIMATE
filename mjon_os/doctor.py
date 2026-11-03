"""Read-only diagnostic report for the MJON AI OS Live session.

No writes, no root actions, no network.  Designed for USB field testing.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import platform
import re
import subprocess
from typing import Any, Callable, Mapping


def parse_memtotal(text: str | None) -> int | None:
    """Convert /proc/meminfo MemTotal kB to bytes, returning None on invalid data."""
    if not isinstance(text, str):
        return None
    m = re.search(r"(?m)^MemTotal:\s+([0-9]+)\s+kB\s*$", text)
    if m is None:
        return None
    count = int(m.group(1))
    return count * 1024 if 0 < count < 2**53 else None


def diagnose(
    *,
    os_name: str,
    env: Mapping[str, str],
    meminfo: str | None,
    runner: Callable[..., Any],
    euid: int | None,
) -> dict[str, Any]:
    """Only inspects state. All subprocess arguments are fixed and read-only."""
    checks: dict[str, str] = {}
    is_linux = os_name == "Linux"
    desk = env.get("XDG_CURRENT_DESKTOP", "").casefold()
    checks["desktop"] = "ok" if "kde" in desk or "plasma" in desk else "unavailable"
    session = env.get("XDG_SESSION_TYPE", "").casefold()
    is_graphical = bool(env.get("WAYLAND_DISPLAY") or env.get("DISPLAY"))
    checks["session"] = "ok" if is_graphical and session in {"wayland", "x11"} else "unavailable"
    total = parse_memtotal(meminfo)
    checks["ram"] = "unknown" if total is None else ("ok" if total >= 6 * 1024**3 else "warning")
    checks["privilege"] = "warning" if euid == 0 and is_linux else "ok"

    if not is_linux:
        checks["jarvis_service"] = "not_applicable"
    else:
        try:
            completed = runner(
                ["systemctl", "--user", "is-active", "mjon-jarvis.service"],
                capture_output=True, text=True, timeout=3, check=False, shell=False,
            )
            checks["jarvis_service"] = (
                "ok" if completed.returncode == 0 and completed.stdout.strip() == "active"
                else "unavailable"
            )
        except (OSError, subprocess.TimeoutExpired):
            checks["jarvis_service"] = "unavailable"
    return {"product": "MJON AI OS", "system": os_name, "memory_total_bytes": total, "checks": checks}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read-only MJON AI OS USB Live diagnostics")
    parser.add_argument("--json", action="store_true", dest="json_mode")
    args = parser.parse_args(argv)
    try:
        memory = Path("/proc/meminfo").read_text(encoding="ascii")
    except OSError:
        memory = None
    report = diagnose(
        os_name=platform.system(),
        env=os.environ,
        meminfo=memory,
        runner=subprocess.run,
        euid=os.geteuid() if hasattr(os, "geteuid") else None,
    )
    if args.json_mode:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("MJON AI OS - read-only diagnostics")
        for key, state in report["checks"].items():
            print(f"{key}: {state}")
        print(f"RAM: {report['memory_total_bytes']} bytes" if report["memory_total_bytes"] else "RAM: unknown")
    return 0 if all(value in {"ok", "not_applicable"} for value in report["checks"].values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
