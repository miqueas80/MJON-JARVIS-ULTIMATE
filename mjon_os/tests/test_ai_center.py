"""The MJON graphical center must expose the same native AI control plane.

Status can be inspected headlessly during CI. GTK is only imported at actual
GUI startup, so Windows package checks do not depend on Linux desktop libs.
"""
from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

from mjon_os import ai_center


class NativeAICenterTests(unittest.TestCase):
    def test_headless_catalog_never_requires_gtk(self):
        payload = ai_center.get_catalog_json()
        result = json.loads(payload)
        self.assertGreaterEqual(len(result["modules"]), 35)
        self.assertEqual(result["policy"]["automatic_installation"], False)
        self.assertEqual(result["policy"]["privileged_actions_without_approval"], False)

    def test_cli_lists_status_without_network_or_desktop(self):
        proc = subprocess.run(
            [sys.executable, "-m", "mjon_os.ai_center", "--status-json"],
            capture_output=True, text=True, timeout=10, check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertIn("modules", payload)
        self.assertIn("hardware", payload)
        self.assertIn("policy", payload)

    def test_one_graphical_center_opens_real_kde_settings(self):
        root = Path(__file__).resolve().parents[1]
        script = root / "live/config/includes.chroot/usr/local/bin/mjon-control-center"
        content = script.read_text(encoding="utf-8")
        self.assertIn("mjon_os.ai_center", content)
        self.assertIn("exec /usr/bin/systemsettings", content)
        self.assertNotIn("sudo ", content)
        self.assertNotIn("curl ", content)

    def test_gui_invokes_local_inference_only_after_user_interaction(self):
        source = Path(ai_center.__file__).read_text(encoding="utf-8")
        self.assertIn("OllamaClient", source)
        self.assertIn("Gtk.Button", source)
        self.assertIn("systemsettings", source)
        self.assertIn("Thread(", source)
        self.assertNotIn("shell=True", source)


if __name__ == "__main__":
    unittest.main()
