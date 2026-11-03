"""The boot checker must never guess success from an ISO header alone."""
from __future__ import annotations

import tempfile
import unittest
import socket
import os
import subprocess
import sys
import time
from pathlib import Path
from unittest.mock import patch

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
            variables = Path(temporary) / "OVMF_VARS.fd"
            variables.write_bytes(b"stub")
            cmd = qemu_command(iso, firmware=firmware, firmware_vars=variables)
            self.assertNotIn("-bios", cmd)
            drives = [cmd[i+1] for i, item in enumerate(cmd) if item == "-drive"]
            self.assertEqual(len(drives), 2)
            self.assertIn("if=pflash", drives[0])
            self.assertIn("readonly=on", drives[0])
            self.assertIn(str(firmware.resolve()), drives[0])
            self.assertIn(str(variables.resolve()), drives[1])

    @unittest.skipUnless(hasattr(socket, "AF_UNIX"), "QEMU monitor uses POSIX Unix sockets")
    @patch("mjon_os.qemu_boot.time.sleep")
    @patch("mjon_os.qemu_boot.socket.socket")
    def test_start_key_is_sent_only_to_vm_monitor(self, make_socket, sleep):
        from mjon_os.qemu_boot import _send_boot_key
        _send_boot_key(Path("/tmp/mjon-monitor.sock"), delay_seconds=0)
        instance = make_socket.return_value.__enter__.return_value
        instance.connect.assert_called_once_with("/tmp/mjon-monitor.sock")
        self.assertEqual(instance.sendall.call_count, 3)
        instance.sendall.assert_any_call(b"sendkey ret\n")

    @unittest.skipUnless(os.name == "posix", "selector of subprocess pipes is POSIX-only")
    def test_vm_serial_monitor_stops_when_graphical_marker_arrives(self):
        from mjon_os.qemu_boot import _collect_until_graphical_ready
        child = subprocess.Popen(
            [sys.executable, "-c",
             "import time; print('MJON_VM_PROOF KERNEL_RUNNING', flush=True); "
             "print('MJON_VM_PROOF DISPLAY_MANAGER_ACTIVE', flush=True); time.sleep(30)"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        try:
            start = time.monotonic()
            output = _collect_until_graphical_ready(child, 5)
            self.assertIn("MJON_VM_PROOF DISPLAY_MANAGER_ACTIVE", output)
            self.assertLess(time.monotonic() - start, 3.0)
        finally:
            child.kill()
            child.communicate(timeout=5)

    def test_unavailable_image_refuses_to_spawn(self):
        with self.assertRaises(FileNotFoundError):
            qemu_command(Path("/no-such-mjon-live-image.iso"), firmware=None)


if __name__ == "__main__":
    unittest.main()
