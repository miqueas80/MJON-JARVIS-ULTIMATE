from __future__ import annotations
import tempfile
import unittest
from pathlib import Path

from mjon_os.vm_capture import screenshot_command


class VMCaptureCommandTests(unittest.TestCase):
    def test_screenshot_never_attaches_host_disk_or_network(self):
        with tempfile.TemporaryDirectory() as directory:
            base=Path(directory)
            iso=base/"test.iso"
            iso.write_bytes(b"iso")
            monitor=base/"mjon.sock"
            args=screenshot_command(iso, firmware=None, monitor=monitor)
            self.assertEqual(args[args.index("-nic")+1], "none")
            self.assertNotIn("-drive", args)
            self.assertNotIn("-hda", args)
            self.assertIn("-snapshot", args)
            self.assertEqual(args[args.index("-monitor")+1], f"unix:{monitor},server,nowait")
            self.assertIn("-display", args)
            self.assertEqual(args[args.index("-display")+1], "none")


    def test_uefi_boot_keeps_firmware_variables_disposable(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            iso, code, vars_path = (base/"test.iso", base/"OVMF_CODE_4M.fd", base/"OVMF_VARS_4M.fd")
            for path in (iso, code, vars_path):
                path.write_bytes(b"stub")
            cmd = screenshot_command(iso, firmware=code, firmware_vars=vars_path, monitor=base/"mjon.sock")
            drives = [cmd[i+1] for i, x in enumerate(cmd) if x == "-drive"]
            self.assertEqual(len(drives), 2)
            self.assertIn("if=pflash", drives[0])
            self.assertIn("readonly=on", drives[0])
            self.assertIn(str(vars_path.resolve()), drives[1])
            self.assertEqual(cmd[cmd.index("-nic")+1], "none")


if __name__=="__main__":
    unittest.main()
