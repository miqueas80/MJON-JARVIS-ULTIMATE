"""Release contract: a Live OS must reach KDE and start JARVIS, not only SDDM."""
from __future__ import annotations

import configparser
import unittest
from pathlib import Path

from mjon_os.qemu_boot import analyze_serial_log

CONFIG=Path(__file__).resolve().parents[1]/"live/config/includes.chroot"


class NativeDesktopTests(unittest.TestCase):
    def test_live_autologin_is_explicitly_limited_to_first_login(self):
        settings=CONFIG/"etc/sddm.conf.d/50-mjon-live.conf"
        ini=configparser.ConfigParser()
        self.assertTrue(settings.is_file(), "Missing SDDM Live autologin")
        ini.read(settings, encoding="utf-8")
        self.assertEqual(ini.get("Autologin","User"),"user")
        self.assertEqual(ini.get("Autologin","Session"),"plasma.desktop")
        self.assertFalse(ini.getboolean("Autologin","Relogin"))

    def test_guest_proof_checks_graphical_session_and_jarvis_service(self):
        proof=(CONFIG/"usr/local/bin/mjon-vm-proof").read_text(encoding="utf-8")
        self.assertIn("plasmashell",proof)
        self.assertIn("mjon-jarvis.service",proof)
        self.assertIn("emit PLASMA_DESKTOP_ACTIVE",proof)
        self.assertIn("emit JARVIS_SERVICE_STABLE",proof)

    def test_greeter_only_not_a_usable_desktop(self):
        log=("MJON_VM_PROOF KERNEL_RUNNING\n"
             "MJON_VM_PROOF DISPLAY_MANAGER_ACTIVE\n"
             "MJON_VM_PROOF LIVE_USER_READY\n")
        proof=analyze_serial_log(log)
        self.assertTrue(proof.live_user)
        self.assertFalse(proof.plasma)
        self.assertFalse(proof.jarvis)

    def test_real_desktop_and_service_markers_are_required(self):
        log=("MJON_VM_PROOF KERNEL_RUNNING\n"
             "MJON_VM_PROOF DISPLAY_MANAGER_ACTIVE\n"
             "MJON_VM_PROOF LIVE_USER_READY\n"
             "MJON_VM_PROOF PLASMA_DESKTOP_ACTIVE\n"
             "MJON_VM_PROOF JARVIS_SERVICE_STABLE\n")
        proof=analyze_serial_log(log)
        self.assertTrue(proof.plasma)
        self.assertTrue(proof.jarvis)


if __name__ == "__main__":
    unittest.main()
