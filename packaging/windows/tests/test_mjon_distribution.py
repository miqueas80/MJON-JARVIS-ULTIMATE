"""Distribution contract: actual ISO bytes, manifest integrity, no boot claim."""
from __future__ import annotations

import hashlib
import tempfile
from pathlib import Path
from unittest import TestCase

import pycdlib

from packaging.windows.build_mjon_tools_iso import make_distribution


class WindowsToolsDistributionTests(TestCase):
    def test_iso_contains_exact_executable_and_security_manifest(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            exe = root / "MJON-Windows-Tools.exe"
            exe.write_bytes(b"MZ" + bytes(range(64)))
            license_file = root / "LICENSE"
            notice_file = root / "NOTICE"
            license_file.write_text("Apache-2.0 test fixture", encoding="utf-8")
            notice_file.write_text("Copyright information", encoding="utf-8")
            iso_path = root / "MJON-AI-OS-Windows-Tools-Preview.iso"
            result = make_distribution(
                exe, iso_path, license_file=license_file, notice_file=notice_file
            )
            self.assertTrue(iso_path.is_file())
            self.assertGreater(iso_path.stat().st_size, len(exe.read_bytes()))
            self.assertEqual(result["bootable"], False)
            self.assertEqual(result["windows_included"], False)
            self.assertEqual(result["executable_sha256"], hashlib.sha256(exe.read_bytes()).hexdigest())

            disk = pycdlib.PyCdlib()
            disk.open(str(iso_path))
            try:
                for p in ("/MJON.EXE;1", "/LEEME.TXT;1", "/SHA256.TXT;1", "/LICENSE.TXT;1", "/NOTICE.TXT;1"):
                    with self.subTest(path=p):
                        self.assertIsNotNone(disk.get_record(iso_path=p))
                with tempfile.TemporaryFile() as extracted:
                    disk.get_file_from_iso_fp(extracted, iso_path="/MJON.EXE;1")
                    extracted.seek(0)
                    self.assertEqual(extracted.read(), exe.read_bytes())
                with tempfile.TemporaryFile() as extracted:
                    disk.get_file_from_iso_fp(extracted, iso_path="/LEEME.TXT;1")
                    extracted.seek(0)
                    text = extracted.read().decode("utf-8")
                    self.assertIn("NO ES BOOTEABLE", text)
                    self.assertIn("Windows", text)
            finally:
                disk.close()

    def test_refuses_missing_executable_and_cannot_overwrite_it(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            lic = root / "LICENSE"
            noti = root / "NOTICE"
            lic.write_text("test", encoding="utf-8")
            noti.write_text("test", encoding="utf-8")
            with self.assertRaises(FileNotFoundError):
                make_distribution(root / "missing.exe", root / "output.iso",
                                  license_file=lic, notice_file=noti)
