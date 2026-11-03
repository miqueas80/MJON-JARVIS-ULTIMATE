"""The boot checker must never guess success from an ISO header alone."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from mjon_os.qemu_boot import analyze_serial_log, qemu_command


class BootProbeTests(unittest.TestCase):
    def test_real_kernel_and_userspace_markers(self):
        evidence = analyze_serial_log(
            "[    0.000000] Linux version 6.12.0-amd64\n"
            "[    5.432100] systemd[1]: Started Journal Service.\n"
        )
        self.assertTrue(evidence.kernel)
        self.assertTrue(evidence.userspace)

    def test_el_torito_record_only_is_not_a_boot(self):
        evidence = analyze_serial_log("El Torito boot img : BIOS and EFI entries detected")
        self.assertFalse(evidence.kernel)
        self.assertFalse(evidence.userspace)

    def test_kernel_without_userspace_does_not_count(self):
        evidence = analyze_serial_log("Linux version 6.12.0\nKernel panic - not syncing")
        self.assertTrue(evidence.kernel)
        self.assertFalse(evidence.userspace)

    def test_qemu_never_mounts_host_disks_or_enables_network(self):
        with tempfile.TemporaryDirectory() as temporary:
            iso = Path(temporary) / "image.iso"
            iso.write_bytes(b"stub")
            cmd = qemu_command(iso, firmware=None)
            self.assertIn("-nic", cmd)
            self.assertEqual(cmd[cmd.index("-nic") + 1], "none")
            self.assertIn("-snapshot", cmd)
            self.assertIn("-cdrom", cmd)
            self.assertNotIn("-drive", cmd)
            self.assertNotIn("-hda", cmd)
            self.assertNotIn("-enable-kvm", cmd)

    def test_uefi_uses_explicit_firmware(self):
        with tempfile.TemporaryDirectory() as temporary:
            iso = Path(temporary) / "image.iso"
            iso.write_bytes(b"stub")
            firmware = Path(temporary) / "OVMF_CODE.fd"
            firmware.write_bytes(b"stub")
            cmd = qemu_command(iso, firmware=firmware)
            self.assertIn("-bios", cmd)
            self.assertEqual(cmd[cmd.index("-bios") + 1], str(firmware.resolve()))

    def test_unavailable_image_refuses_to_spawn(self):
        with self.assertRaises(FileNotFoundError):
            qemu_command(Path("/no-such-mjon-live-image.iso"), firmware=None)


if __name__ == "__main__":
    unittest.main()
