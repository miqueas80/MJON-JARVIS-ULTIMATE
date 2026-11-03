"""Native KDE commands should resolve to Linux apps rather than Windows .exe names."""
import os
import unittest
from unittest.mock import patch

from dodaios.brain.local_action_gate import LocalActionMode, match_local_action


class NativeCommandTests(unittest.TestCase):
    def test_spanish_commands_use_kde_apps_in_native_os(self):
        examples = {
            "Jarvis, abrí el bloc de notas": "kate",
            "Abrir calculadora": "kcalc",
            "Jarvis, abrí explorador de archivos": "dolphin",
            "Jarvis, abrí terminal": "konsole",
        }
        with patch.dict(os.environ, {"MJON_NATIVE_OS": "1"}):
            for instruction, app in examples.items():
                with self.subTest(instruction=instruction):
                    plan = match_local_action(instruction, lang="es", _registry=None)
                    self.assertIsNotNone(plan)
                    self.assertEqual(plan.mode, LocalActionMode.DIRECT)
                    self.assertEqual(plan.tool_calls[0].name, "open_app")
                    self.assertEqual(plan.tool_calls[0].args, {"app_name": app})

    def test_upstream_windows_mappings_are_unchanged_outside_native_os(self):
        with patch.dict(os.environ, {}, clear=True):
            plan = match_local_action("abrir calculadora", lang="es", _registry=None)
            self.assertEqual(plan.tool_calls[0].args, {"app_name": "calc"})

    def test_negated_command_never_routes_as_open_app(self):
        with patch.dict(os.environ, {"MJON_NATIVE_OS": "1"}):
            self.assertIsNone(match_local_action("Jarvis, no abras calculadora", lang="es", _registry=None))


if __name__ == "__main__":
    unittest.main()
