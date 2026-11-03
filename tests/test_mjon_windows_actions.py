import unittest
from unittest.mock import patch
from mjon_jarvis.windows_actions import execute_spoken_command

class WindowsActionsTests(unittest.TestCase):
    @patch("mjon_jarvis.windows_actions.subprocess.Popen")
    def test_requires_confirmation(self, popen):
        self.assertIn("Confirmación", execute_spoken_command("abrir calculadora"))
        popen.assert_not_called()
    @patch("mjon_jarvis.windows_actions.sys.platform", "win32")
    @patch("mjon_jarvis.windows_actions.subprocess.Popen")
    def test_uses_fixed_executable_no_shell(self, popen):
        self.assertEqual(execute_spoken_command("Jarvis, abrí calculadora", confirmed=True), "Abriendo calc.")
        popen.assert_called_once_with(["calc.exe"], shell=False)
    @patch("mjon_jarvis.windows_actions.subprocess.Popen")
    def test_rejects_arbitrary_shell(self, popen):
        self.assertIn("no permitida", execute_spoken_command("ejecuta cmd /c del C:", confirmed=True))
        popen.assert_not_called()
