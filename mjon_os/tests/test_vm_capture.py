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


if __name__=="__main__":
    unittest.main()
