"""Regression contracts for an actually configurable MJON AI OS desktop.

The first USB build omitted KDE's graphical system-settings frontend because
APT recommends were disabled. This contract ensures the next Live image has
a visible Windows-like settings center and the underlying applets.
"""
from __future__ import annotations

from configparser import ConfigParser
from pathlib import Path
import tempfile
import unittest

from mjon_os.image_builder import prepare_image


CONFIG = Path(__file__).resolve().parents[1] / "live" / "config"
INCLUDES = CONFIG / "includes.chroot"
MENU = INCLUDES / "usr/share/applications/mjon-control-center.desktop"
DESKTOP = INCLUDES / "etc/skel/Desktop/Centro-de-mando-MJON.desktop"
LAUNCHER = INCLUDES / "usr/local/bin/mjon-control-center"


class ControlCenterTests(unittest.TestCase):
    def test_every_gui_settings_component_is_explicitly_bundled(self):
        packages = (CONFIG / "package-lists/mjon.list.chroot").read_text(encoding="utf-8")
        included = set(packages.splitlines())
        expected = {
            "systemsettings", "plasma-nm", "wpasupplicant", "rfkill",
            "plasma-pa", "bluedevil", "bluez", "powerdevil",
            "kscreen", "kinfocenter", "polkit-kde-agent-1",
            "plasma-systemmonitor", "plasma-discover",
        }
        self.assertEqual(expected - included, set(), "KDE Control Center panels cannot be used")

    def test_menu_and_desktop_open_same_real_graphical_settings_app(self):
        for path in (MENU, DESKTOP):
            with self.subTest(path=str(path)):
                self.assertTrue(path.is_file(), f"Settings shortcut missing: {path}")
                entry = ConfigParser(interpolation=None)
                entry.read(path, encoding="utf-8")
                section = entry["Desktop Entry"]
                self.assertEqual(section["Type"], "Application")
                self.assertEqual(section["Exec"], "/usr/local/bin/mjon-control-center")
                self.assertEqual(section["Terminal"].lower(), "false")
                self.assertIn("Centro de mando", section["Name"])
                self.assertIn("Settings;", section["Categories"])
                self.assertEqual(section["TryExec"], "/usr/bin/systemsettings")

    def test_center_launcher_uses_kde_settings_without_root_or_remote_code(self):
        script = LAUNCHER.read_text(encoding="utf-8")
        self.assertTrue(script.startswith("#!/bin/sh"))
        self.assertIn("exec /usr/bin/systemsettings", script)
        self.assertNotIn("sudo ", script)
        self.assertNotIn("curl ", script)
        self.assertNotIn("pkexec ", script)

    def test_guest_boot_proves_center_is_available_not_just_listed(self):
        proof = (INCLUDES / "usr/local/bin/mjon-vm-proof").read_text(encoding="utf-8")
        self.assertIn("emit CONTROL_CENTER_READY", proof)
        self.assertIn("/usr/bin/systemsettings", proof)
        self.assertIn("/usr/share/applications/mjon-control-center.desktop", proof)

    def test_image_builder_marks_shortcuts_executable(self):
        builder = (CONFIG.parents[1] / "image_builder.py").read_text(encoding="utf-8")
        self.assertIn("'usr/local/bin/mjon-control-center'", builder)
        self.assertIn("'etc/skel/Desktop/Centro-de-mando-MJON.desktop'", builder)
        self.assertIn(".chmod(0o755)", builder)


if __name__ == "__main__":
    unittest.main()
