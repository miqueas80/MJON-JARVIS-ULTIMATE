"""VM screenshot capture (host only): no host disks or network attached to QEMU."""
from __future__ import annotations

import argparse
from pathlib import Path
import socket
import subprocess
import tempfile
import time

from mjon_os.qemu_boot import qemu_command


def screenshot_command(iso: Path, *, firmware: Path | None, monitor: Path) -> list[str]:
    command = qemu_command(iso, firmware=firmware)
    # HMP socket allows a screenshot without a graphical session on the CI host.
    idx = command.index("-monitor") + 1
    command[idx] = f"unix:{monitor},server,nowait"
    return command


def capture(iso: Path, *, firmware: Path | None, output: Path,
            seconds: int = 75) -> None:
    if seconds < 5 or seconds > 300:
        raise ValueError("Capture interval must be between 5 and 300 seconds")
    if not output.parent.is_dir():
        raise FileNotFoundError(output.parent)
    with tempfile.TemporaryDirectory(prefix="mjon-qemu-") as directory:
        monitor = Path(directory) / "monitor.sock"
        command = screenshot_command(iso, firmware=firmware, monitor=monitor)
        process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        try:
            time.sleep(seconds)
            if process.poll() is not None:
                stderr = process.stderr.read().decode("utf-8", "replace") if process.stderr else ""
                raise RuntimeError(f"QEMU exited early ({process.returncode}): {stderr[-1000:]}")
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as channel:
                channel.settimeout(15)
                channel.connect(str(monitor))
                channel.sendall(f"screendump {output.resolve()}\n".encode("utf-8"))
                time.sleep(3)
            if not output.is_file() or output.stat().st_size < 100:
                raise RuntimeError("No usable VM screenshot was captured")
        finally:
            process.terminate()
            try:
                process.communicate(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.communicate(timeout=10)


def main() -> None:
    parser = argparse.ArgumentParser(description="Capture isolated QEMU BIOS or UEFI screen")
    parser.add_argument("--iso", type=Path, required=True)
    parser.add_argument("--firmware", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seconds", type=int, default=75)
    args = parser.parse_args()
    capture(args.iso, firmware=args.firmware, output=args.output, seconds=args.seconds)
    print(f"Captured {args.output} ({args.output.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
