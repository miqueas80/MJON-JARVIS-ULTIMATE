"""Capture the actual graphical screen of a network-free, isolated VM."""
from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile
import time

from mjon_os.qemu_boot import qemu_command


def screenshot_command(
    iso: Path, *, firmware: Path | None, monitor: Path,
    firmware_vars: Path | None = None,
) -> list[str]:
    command = qemu_command(iso, firmware=firmware, firmware_vars=firmware_vars)
    command[command.index("-monitor") + 1] = f"unix:{monitor},server,nowait"
    return command


def capture(iso: Path, *, firmware: Path | None, output: Path,
            seconds: int = 75) -> None:
    if seconds < 10 or seconds > 300:
        raise ValueError("Capture interval must be between 10 and 300 seconds")
    if not output.parent.is_dir():
        raise FileNotFoundError(output.parent)
    with tempfile.TemporaryDirectory(prefix="mjon-qemu-") as dirname:
        directory = Path(dirname)
        vars_copy = None
        if firmware is not None:
            template = firmware.with_name(firmware.name.replace("CODE", "VARS"))
            if not template.is_file():
                raise FileNotFoundError(f"Missing matching OVMF VARS: {template}")
            vars_copy = directory / "OVMF_VARS.fd"
            shutil.copyfile(template, vars_copy)
        monitor = directory / "monitor.sock"
        command = screenshot_command(iso, firmware=firmware, monitor=monitor, firmware_vars=vars_copy)
        process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        try:
            time.sleep(5)
            if process.poll() is not None:
                stderr = process.stderr.read().decode("utf-8", "replace") if process.stderr else ""
                raise RuntimeError(f"QEMU exited early ({process.returncode}): {stderr[-1000:]}")
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as channel:
                channel.settimeout(15)
                channel.connect(str(monitor))
                channel.sendall(b"sendkey ret\n")
                time.sleep(seconds - 5)
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
