"""Strict policy checks before building a Windows 11 ISO on a local Windows PC.

The Windows ISO must be acquired separately and legitimately from Microsoft.
This module never downloads Windows, publishes Microsoft media, bypasses TPM,
overrides the Microsoft license, or claims to implement the final MJON desktop.
"""
from __future__ import annotations

import hashlib
from pathlib import Path


GIB = 1024**3


def calculate_required_space(source_bytes: int, payload_bytes: int) -> int:
    """Conservative space: original ISO + extracted copy + new ISO + overhead.

    Reports capacity planning only, not a guarantee for a specific media layout.
    """
    if isinstance(source_bytes, bool) or not isinstance(source_bytes, int) or source_bytes <= 0:
        raise ValueError("Source ISO size must be a positive integer.")
    if isinstance(payload_bytes, bool) or not isinstance(payload_bytes, int) or payload_bytes < 0:
        raise ValueError("Payload size must be a nonnegative integer.")
    return 3 * source_bytes + 2 * payload_bytes + 5 * GIB


def inspect_source_tree(root: Path) -> dict:
    """Check expected installation/boot files (not a cryptographic authenticity proof)."""
    root = Path(root)
    required = [
        "setup.exe",
        "sources/boot.wim",
        "boot/etfsboot.com",
        "efi/microsoft/boot/efisys.bin",
        "efi/boot/bootx64.efi",
    ]
    missing = [name for name in required if not (root / name).is_file()]
    image = next(
        (name for name in ("install.wim", "install.esd", "install.swm")
         if (root / "sources" / name).is_file()),
        None,
    )
    if missing or image is None:
        raise ValueError(
            f"No es un medio Windows 11 x64 completo. Faltan: {', '.join(missing) or 'sources/install.wim|esd|swm'}"
        )
    return {
        "install_image": image,
        "uefi_files_present": True,
        "bios_files_present": True,
    }


def inspect_payload(root: Path) -> dict:
    """Verify a small MJON Windows tools bundle against its SHA256SUMS file.

    A verified tools executable is NOT evidence that the approved visual shell
    exists; this is intentionally an integration-preview payload.
    """
    root = Path(root)
    exe = root / "MJON-Windows-Tools.exe"
    sums = root / "SHA256SUMS.txt"
    if not exe.is_file() or not sums.is_file():
        raise ValueError("Faltan MJON-Windows-Tools.exe o SHA256SUMS.txt.")
    h = hashlib.sha256()
    with exe.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    actual = h.hexdigest()
    lines = sums.read_text(encoding="ascii").splitlines()
    if not any(
        line.strip().lower() == f"{actual}  mjon-windows-tools.exe"
        for line in lines
    ):
        raise ValueError("El checksum SHA256 del ejecutable MJON no coincide.")
    return {
        "file_count": len([p for p in root.iterdir() if p.is_file()]),
        "executable_sha256": actual,
    }
