"""Fail-closed release candidate verification. No flashing or disk modification."""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import re
import sys


_ASSET_LIMIT_BYTES = 2 * 1024 ** 3  # GitHub Releases requires each file under 2 GiB.


def check_candidate(iso: Path, checksum: Path, boot_records: Path,
                    bios_log: Path, uefi_log: Path, *,
                    min_bytes: int = 100_000_000,
                    max_bytes: int = _ASSET_LIMIT_BYTES) -> bool:
    if not iso.is_file():
        raise ValueError("ISO not found")
    size = iso.stat().st_size
    if not min_bytes <= size < max_bytes:
        raise ValueError(f"ISO size {size} is outside permitted release bounds")
    parts = checksum.read_text(encoding="ascii").split()
    if len(parts) != 2 or not re.fullmatch(r"[a-fA-F0-9]{64}", parts[0]):
        raise ValueError("Malformed SHA256 checksum file")
    if Path(parts[1].lstrip("*")).name != iso.name:
        raise ValueError("Checksum file refers to a different ISO")
    digest = hashlib.sha256()
    with iso.open("rb") as stream:
        for chunk in iter(lambda: stream.read(2 ** 20), b""):
            digest.update(chunk)
    if digest.hexdigest() != parts[0].lower():
        raise ValueError("ISO checksum mismatch")

    records = boot_records.read_text(encoding="utf-8")
    for firmware in ("BIOS", "UEFI"):
        if not re.search(rf"El Torito boot img\s*:\s*\d+\s+{firmware}\b", records):
            raise ValueError(f"Missing ISO {firmware} boot image")

    for label, logpath in (("BIOS", bios_log), ("UEFI", uefi_log)):
        log = logpath.read_text(encoding="utf-8")
        if "MJON_VM_EVIDENCE kernel=True userspace=True" not in log:
            raise ValueError(f"Missing {label} VM kernel/userspace proof")
        if ("MJON_VM_EVIDENCE kernel=True userspace=True live_user=True" not in log
                or "MJON_VM_PROOF LIVE_USER_READY" not in log):
            raise ValueError(f"Missing {label} VM Live user account and password proof")
        if ("plasma=True jarvis=True" not in log
                or "MJON_VM_PROOF PLASMA_DESKTOP_ACTIVE" not in log
                or "MJON_VM_PROOF JARVIS_SERVICE_STABLE" not in log):
            raise ValueError(f"Missing {label} VM KDE desktop or stable JARVIS service proof")
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify a USB-ready experimental ISO before publication")
    for arg in ("iso", "checksum", "boot-records", "bios-log", "uefi-log"):
        parser.add_argument("--" + arg, type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        check_candidate(args.iso, args.checksum, args.boot_records,
                        args.bios_log, args.uefi_log)
    except (OSError, ValueError) as exc:
        print(f"USB candidate verification failed: {exc}", file=sys.stderr)
        return 1
    print("USB candidate inputs verified: ISO checksum, BIOS/UEFI entries and virtual boot evidence")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
