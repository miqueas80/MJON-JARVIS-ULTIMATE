"""Contract checks for safe user-driven Windows installation media.

These tests do not claim that the ISO has been booted, nor modify a Windows
install. Runtime smoke builds are exercised separately by GitHub Actions.
"""
from __future__ import annotations
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2] / "packaging" / "windows"


class WindowsDesktopMediaContracts(unittest.TestCase):
    def test_bootable_iso_builder_has_distinct_output_and_local_gui(self):
        text = (ROOT / "CREAR_ISO_MJON_ESCRITORIO.cmd").read_text(encoding="utf-8")
        self.assertIn("MJON-Win11-Desktop-Preview.iso", text)
        self.assertIn("Windows11-x64", text)
        self.assertIn("SHA256-DESKTOP.txt", text)
        self.assertIn("MJON-AI-OS.exe", text)
        self.assertIn("INSTALAR-MJON.cmd", text)
        self.assertIn("DESINSTALAR-MJON.cmd", text)
        self.assertIn("oscdimg.exe", text)
        self.assertIn("-bootdata:2", text)
        self.assertIn("if exist \"%OUTPUT%\"", text)
        self.assertIn("Get-AuthenticodeSignature", text)
        self.assertIn("Get-FileHash", text)
        self.assertIn("--self-test", text)

    def test_installer_requires_explicit_consent_and_runs_as_user(self):
        text = (ROOT / "INSTALAR-MJON.cmd").read_text(encoding="utf-8")
        self.assertIn("choice /C SN", text)
        self.assertIn("%LOCALAPPDATA%", text)
        self.assertIn("Get-FileHash", text)
        self.assertNotIn("schtasks", text.lower())
        self.assertNotIn("runas", text.lower())
        self.assertNotIn("reg add", text.lower())
        self.assertNotIn("setup.exe", text.lower())

    def test_uninstall_is_scoped_to_only_mjon_app(self):
        text = (ROOT / "DESINSTALAR-MJON.cmd").read_text(encoding="utf-8")
        self.assertIn("%LOCALAPPDATA%", text)
        self.assertIn("MJON-AI-OS.exe", text)
        self.assertIn("choice /C SN", text)
        self.assertNotIn("rmdir /s", text.lower())
        self.assertNotIn("format ", text.lower())


if __name__ == "__main__":
    unittest.main()
