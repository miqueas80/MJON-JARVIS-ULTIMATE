"""Strict USB release checks: checksum, BIOS/UEFI boot records and VM boot evidence."""
from __future__ import annotations

import hashlib
from pathlib import Path
import re
import unittest
from tempfile import TemporaryDirectory

from mjon_os.release_checks import check_candidate


class USBReleaseTests(unittest.TestCase):
    def _inputs(self, root: Path):
        iso = root / "MJON-AI-OS-dev-amd64.iso"
        iso.write_bytes(b"demo ISO")
        sha = root / "MJON-AI-OS-dev-amd64.iso.sha256"
        sha.write_text(f"{hashlib.sha256(iso.read_bytes()).hexdigest()}  {iso.name}\n")
        boot = root / "boot-records.txt"
        boot.write_text("El Torito boot img :   1  BIOS\nEl Torito boot img :   2  UEFI\n")
        bios = root / "boot-bios-serial.txt"
        uefi = root / "boot-uefi-serial.txt"
        for text in (bios, uefi):
            text.write_text(
                "MJON_VM_EVIDENCE kernel=True userspace=True live_user=True plasma=True jarvis=True\n"
                "MJON_VM_PROOF LIVE_USER_READY\n"
                "MJON_VM_PROOF PLASMA_DESKTOP_ACTIVE\n"
                "MJON_VM_PROOF JARVIS_SERVICE_STABLE\n"
            )
        return iso, sha, boot, bios, uefi

    def test_valid_candidate_inputs(self):
        with TemporaryDirectory() as tmp:
            self.assertTrue(check_candidate(*self._inputs(Path(tmp)), min_bytes=1, max_bytes=1000))

    def test_checksum_mismatch_refused(self):
        with TemporaryDirectory() as tmp:
            iso, sha, boot, bios, uefi = self._inputs(Path(tmp))
            iso.write_bytes(b"tampered")
            with self.assertRaisesRegex(ValueError, "checksum"):
                check_candidate(iso, sha, boot, bios, uefi, min_bytes=1)

    def test_boot_entries_are_not_vm_evidence(self):
        with TemporaryDirectory() as tmp:
            iso, sha, boot, bios, uefi = self._inputs(Path(tmp))
            bios.write_text("")
            with self.assertRaisesRegex(ValueError, "BIOS VM"):
                check_candidate(iso, sha, boot, bios, uefi, min_bytes=1)

    def test_release_refuses_greeter_when_live_user_is_missing(self):
        with TemporaryDirectory() as tmp:
            iso, sha, boot, bios, uefi = self._inputs(Path(tmp))
            bios.write_text("MJON_VM_EVIDENCE kernel=True userspace=True live_user=False\n"
                            "MJON_VM_PROOF DISPLAY_MANAGER_ACTIVE\n")
            with self.assertRaisesRegex(ValueError, "Live user"):
                check_candidate(iso, sha, boot, bios, uefi, min_bytes=1)

    def test_release_refuses_login_without_plasma_or_jarvis(self):
        with TemporaryDirectory() as tmp:
            iso, sha, boot, bios, uefi = self._inputs(Path(tmp))
            uefi.write_text(
                "MJON_VM_EVIDENCE kernel=True userspace=True live_user=True plasma=False jarvis=False\n"
                "MJON_VM_PROOF LIVE_USER_READY\n"
            )
            with self.assertRaisesRegex(ValueError, "desktop"):
                check_candidate(iso, sha, boot, bios, uefi, min_bytes=1)

    def test_uefi_is_required(self):
        with TemporaryDirectory() as tmp:
            iso, sha, boot, bios, uefi = self._inputs(Path(tmp))
            boot.write_text("El Torito boot img :   1  BIOS\n")
            with self.assertRaisesRegex(ValueError, "UEFI"):
                check_candidate(iso, sha, boot, bios, uefi, min_bytes=1)

    def test_release_asset_limit_fail_closed(self):
        with TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "size"):
                check_candidate(*self._inputs(Path(tmp)), min_bytes=10**8)


if __name__ == "__main__":
    unittest.main()
