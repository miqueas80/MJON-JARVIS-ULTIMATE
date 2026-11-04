"""Virtual boot validation for an experimental ISO without exposing host drives.

A Debian Live ISO can wait indefinitely at the graphical boot menu; QEMU
must explicitly press Enter before a serial-kernel/userspace test is valid.
UEFI requires OVMF CODE and a disposable copy of its matching VARS image.
"""
from __future__ import annotations

import argparse
import os
import selectors
from dataclasses import dataclass
from pathlib import Path
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time


@dataclass(frozen=True)
class BootEvidence:
    kernel: bool
    userspace: bool
    live_user: bool
    plasma: bool
    jarvis: bool
    api: bool
    excerpt: str


_KERNEL_RE = re.compile(r"(?:Linux version \d|Linux kernel|MJON_VM_PROOF KERNEL_RUNNING)")
_USERSPACE_RE = re.compile(r"(?:systemd\[1\]|Welcome to Debian|Reached target|Starting Network Manager|MJON_VM_PROOF DISPLAY_MANAGER_ACTIVE)")


def analyze_serial_log(log: str) -> BootEvidence:
    """Boot menus and ISO signatures are never sufficient proof of kernel boot."""
    lines = log.splitlines()
    excerpt = "\n".join([*lines[:20], "...", *lines[-70:]])
    return BootEvidence(
        bool(_KERNEL_RE.search(log)), bool(_USERSPACE_RE.search(log)),
        'MJON_VM_PROOF LIVE_USER_READY' in log,
        'MJON_VM_PROOF PLASMA_DESKTOP_ACTIVE' in log,
        'MJON_VM_PROOF JARVIS_SERVICE_STABLE' in log,
        'MJON_VM_PROOF JARVIS_API_READY' in log,
        excerpt,
    )


def qemu_command(
    iso: Path, *, firmware: Path | None, firmware_vars: Path | None = None,
    memory_mib: int = 3072,
) -> list[str]:
    if not iso.is_file():
        raise FileNotFoundError(iso)
    if memory_mib < 1024:
        raise ValueError("Boot test needs at least 1 GiB")
    args = [
        "qemu-system-x86_64", "-machine", "q35,accel=tcg", "-m", str(memory_mib),
        "-smp", "2", "-nodefaults", "-device", "VGA",
        "-cdrom", str(iso.resolve()), "-boot", "order=d",
        "-display", "none", "-monitor", "none", "-serial", "stdio",
        "-nic", "none", "-no-reboot", "-snapshot",
    ]
    if firmware is not None:
        if not firmware.is_file():
            raise FileNotFoundError(firmware)
        if firmware_vars is None or not firmware_vars.is_file():
            raise ValueError("UEFI requires an existing disposable OVMF VARS file")
        args.extend([
            "-drive", f"if=pflash,format=raw,unit=0,readonly=on,file={firmware.resolve()}",
            "-drive", f"if=pflash,format=raw,unit=1,file={firmware_vars.resolve()}",
        ])
    elif firmware_vars is not None:
        raise ValueError("VARS is only valid for UEFI")
    return args


def _send_boot_key(monitor: Path, *, delay_seconds: float = 5.0) -> None:
    """Send Enter only to the isolated virtual firmware/boot menu."""
    time.sleep(delay_seconds)
    last_error: OSError | None = None
    for _ in range(20):
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
                sock.settimeout(5)
                sock.connect(str(monitor))
                # SeaBIOS appears quickly; OVMF/GRUB may take longer.
                # Repeated Enter only acts inside this disposable VM.
                sock.sendall(b"sendkey ret\n")
                time.sleep(12)
                sock.sendall(b"sendkey ret\n")
                time.sleep(12)
                sock.sendall(b"sendkey ret\n")
                return
        except OSError as exc:
            last_error = exc
            time.sleep(0.5)
    raise RuntimeError(f"QEMU monitor not ready: {last_error}")



def _collect_until_graphical_ready(process: subprocess.Popen, timeout_seconds: int) -> str:
    """Read a live VM serial stream, stop only on a proven graphical guest target.

    This avoids waiting for the whole timeout after a successful boot. The
    sentinel is emitted exclusively from inside the disposable Linux guest.
    """
    chunks: list[bytes] = []
    total_bytes = 0
    selector = selectors.DefaultSelector()
    try:
        for stream in (process.stdout, process.stderr):
            if stream is not None:
                selector.register(stream, selectors.EVENT_READ)
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline and selector.get_map():
            for key, _ in selector.select(timeout=1):
                piece = os.read(key.fileobj.fileno(), 65536)
                if not piece:
                    selector.unregister(key.fileobj)
                    continue
                chunks.append(piece)
                total_bytes += len(piece)
            if total_bytes > 10 * 1024 * 1024:
                break
            observed = b"".join(chunks)
            if (b"MJON_VM_PROOF KERNEL_RUNNING" in observed
                    and b"MJON_VM_PROOF DISPLAY_MANAGER_ACTIVE" in observed
                    and b"MJON_VM_PROOF LIVE_USER_READY" in observed
                    and b"MJON_VM_PROOF PLASMA_DESKTOP_ACTIVE" in observed
                    and b"MJON_VM_PROOF JARVIS_SERVICE_STABLE" in observed
                    and b"MJON_VM_PROOF JARVIS_API_READY" in observed):
                break
    finally:
        selector.close()
    return b"".join(chunks).decode("utf-8", "replace")


def boot_probe(iso: Path, *, firmware: Path | None, timeout_seconds: int = 300) -> BootEvidence:
    """Boot ISO in a disposable network-free, host-disk-free VM.

    QEMU remains running after Linux starts. We terminate it at the bound and
    consider success only when its serial output proves kernel + userspace.
    """
    with tempfile.TemporaryDirectory(prefix="mjon-boot-") as dirname:
        directory = Path(dirname)
        vars_copy: Path | None = None
        if firmware is not None:
            template = firmware.with_name(firmware.name.replace("CODE", "VARS"))
            if not template.is_file():
                raise FileNotFoundError(f"Missing matching OVMF VARS template: {template}")
            vars_copy = directory / "OVMF_VARS.fd"
            shutil.copyfile(template, vars_copy)
        monitor = directory / "monitor.sock"
        args = qemu_command(iso, firmware=firmware, firmware_vars=vars_copy)
        args[args.index("-monitor") + 1] = f"unix:{monitor},server,nowait"
        process = subprocess.Popen(
            args, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=False,
        )
        try:
            _send_boot_key(monitor)
            output = _collect_until_graphical_ready(process, timeout_seconds)
        finally:
            if process.poll() is None:
                process.kill()
            stdout, stderr = process.communicate(timeout=20)
        output += stdout.decode("utf-8", "replace") + "\n" + stderr.decode("utf-8", "replace")
        return analyze_serial_log(output)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify Linux kernel/userspace boot using QEMU")
    parser.add_argument("--iso", type=Path, required=True)
    parser.add_argument("--uefi-firmware", type=Path)
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--log", type=Path, required=True)
    args = parser.parse_args(argv)
    evidence = boot_probe(args.iso, firmware=args.uefi_firmware, timeout_seconds=args.timeout)
    args.log.write_text(
        f"MJON_VM_EVIDENCE kernel={evidence.kernel} userspace={evidence.userspace} live_user={evidence.live_user} plasma={evidence.plasma} jarvis={evidence.jarvis} api={evidence.api}\n"
        + evidence.excerpt + "\n", encoding="utf-8",
    )
    label = "UEFI" if args.uefi_firmware is not None else "BIOS"
    print(f"{label} boot evidence: kernel={evidence.kernel}, userspace={evidence.userspace}, live_user={evidence.live_user}, plasma={evidence.plasma}, jarvis={evidence.jarvis}, api={evidence.api}")
    if not all((evidence.kernel, evidence.userspace, evidence.live_user, evidence.plasma, evidence.jarvis, evidence.api)):
        print(evidence.excerpt, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
