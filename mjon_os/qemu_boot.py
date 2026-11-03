"""Virtual boot validation for an experimental ISO, without host disk access."""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import re
import subprocess
import sys


@dataclass(frozen=True)
class BootEvidence:
    kernel: bool
    userspace: bool
    excerpt: str


_KERNEL_RE = re.compile(r"(?:Linux version \d|Linux version|Linux kernel)")
_USERSPACE_RE = re.compile(r"(?:systemd\[1\]|Welcome to Debian|Reached target|Starting Network Manager)")


def analyze_serial_log(log: str) -> BootEvidence:
    """An El Torito entry alone is not proof of a successful kernel boot."""
    excerpt = "\n".join(log.splitlines()[-60:])
    return BootEvidence(bool(_KERNEL_RE.search(log)), bool(_USERSPACE_RE.search(log)), excerpt)


def qemu_command(iso: Path, *, firmware: Path | None, memory_mib: int = 3072) -> list[str]:
    if not iso.is_file():
        raise FileNotFoundError(iso)
    if firmware is not None and not firmware.is_file():
        raise FileNotFoundError(firmware)
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
        args.extend(["-bios", str(firmware.resolve())])
    return args


def boot_probe(iso: Path, *, firmware: Path | None, timeout_seconds: int = 360) -> BootEvidence:
    """Launch an isolated VM without any writable host disk or network device.

    QEMU is expected to remain running after the desktop boots. Timeout is not
    considered an error if serial logs prove kernel AND userspace startup.
    """
    args = qemu_command(iso, firmware=firmware)
    try:
        proc = subprocess.run(
            args, capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=timeout_seconds, check=False,
        )
        output = proc.stdout + "\n" + proc.stderr
    except subprocess.TimeoutExpired as exc:
        # subprocess.run terminates the child process when the timeout expires.
        raw = exc.stdout or b""
        err = exc.stderr or b""
        output = (raw.decode("utf-8", "replace") if isinstance(raw, bytes) else raw) + "\n" + (
            err.decode("utf-8", "replace") if isinstance(err, bytes) else err)
    return analyze_serial_log(output)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check a Live ISO using QEMU without touching host disks")
    parser.add_argument("--iso", type=Path, required=True)
    parser.add_argument("--uefi-firmware", type=Path, default=None)
    parser.add_argument("--timeout", type=int, default=360)
    parser.add_argument("--log", type=Path, required=True)
    args = parser.parse_args(argv)
    evidence = boot_probe(args.iso, firmware=args.uefi_firmware, timeout_seconds=args.timeout)
    args.log.write_text(evidence.excerpt + "\n", encoding="utf-8")
    label = "UEFI" if args.uefi_firmware is not None else "BIOS"
    print(f"{label} boot evidence: kernel={evidence.kernel}, userspace={evidence.userspace}")
    if not evidence.kernel or not evidence.userspace:
        print(evidence.excerpt, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
