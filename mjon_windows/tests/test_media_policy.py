"""Pure contract tests for a Windows 11 bootable-media customization workflow.

This prepares a build; it does not claim a Windows ISO is already provided,
and does not redistribute Windows installation files.
"""
import tempfile
import unittest
from pathlib import Path

from mjon_windows.media_policy import (
    calculate_required_space,
    inspect_source_tree,
    inspect_payload,
)


class DiskBudgetTests(unittest.TestCase):
    def test_large_windows_media_requires_space_for_source_copy_and_output(self):
        required = calculate_required_space(
            source_bytes=8 * 1024**3, payload_bytes=200 * 1024**2
        )
        self.assertGreaterEqual(required, 29 * 1024**3)

    def test_invalid_sizes_refuse_unsafe_assumptions(self):
        for source, payload in [(-1, 10), (10, -2), (True, 0), (0, 0)]:
            with self.subTest(source=source, payload=payload):
                with self.assertRaises(ValueError):
                    calculate_required_space(source, payload)


class MediaTreeTests(unittest.TestCase):
    def test_requires_genuine_install_file_layout_and_both_boot_images(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root)
            with self.assertRaises(ValueError):
                inspect_source_tree(path)
            for item in (
                "setup.exe", "sources/boot.wim", "sources/install.esd",
                "boot/etfsboot.com", "efi/microsoft/boot/efisys.bin",
                "efi/boot/bootx64.efi",
            ):
                target = path / item
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(b"MZfixture")
            result = inspect_source_tree(path)
            self.assertEqual(result["install_image"], "install.esd")
            self.assertTrue(result["uefi_files_present"])
            self.assertTrue(result["bios_files_present"])

    def test_payload_must_have_verifiable_windows_executable(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root)
            with self.assertRaises(ValueError):
                inspect_payload(path)
            exe = path / "MJON-Windows-Tools.exe"
            exe.write_bytes(b"MZ" + b"placeholder")
            with self.assertRaises(ValueError):
                inspect_payload(path)
            import hashlib
            sha = hashlib.sha256(exe.read_bytes()).hexdigest()
            (path / "SHA256SUMS.txt").write_text(
                f"{sha}  MJON-Windows-Tools.exe\n", encoding="ascii"
            )
            result = inspect_payload(path)
            self.assertEqual(result["file_count"], 2)
            self.assertEqual(result["executable_sha256"], sha)
            (path / "SHA256SUMS.txt").write_text(
                "0" * 64 + "  MJON-Windows-Tools.exe\n", encoding="ascii"
            )
            with self.assertRaises(ValueError):
                inspect_payload(path)


class LargeIsoBootOrderingTests(unittest.TestCase):
    def test_builder_orders_windows_boot_files_for_media_over_4_5_gb(self):
        script = (
            Path(__file__).resolve().parents[2]
            / "packaging" / "windows" / "build-mjon-win11-media.ps1"
        ).read_text(encoding="utf-8")
        self.assertIn("bootOrder", script)
        self.assertIn("-yo$bootOrder", script)
        self.assertIn("sources\\boot.wim", script)
        self.assertIn("efi\\microsoft\\boot\\bcd", script)
        self.assertIn("Set-Content", script)


if __name__ == "__main__":
    unittest.main()
