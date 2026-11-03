"""Dependency-light integration checks against the actual Dodaios action gate."""
from __future__ import annotations

import unittest

from dodaios.brain.local_action_gate import LocalActionMode, is_open_app_intent, match_local_action
from mjon_jarvis.spanish_bridge import parse_spanish_request


class SpanishWindowsRoutingSmoke(unittest.TestCase):
    def test_launches_use_the_original_dodaios_tool(self):
        cases = {
            "Jarvis, abrí el bloc de notas": "notepad",
            "Abrir calculadora": "calc",
            "Iniciá el terminal de Windows": "wt",
            "Jarvis: abre Chrome": "chrome",
            "hey Jarvis, abrí el explorador de archivos": "explorer",
        }
        for phrase, app in cases.items():
            with self.subTest(phrase=phrase):
                plan = match_local_action(phrase, lang="es", _registry=None)
                self.assertEqual(plan.mode, LocalActionMode.DIRECT)
                self.assertEqual(plan.tool_calls[0].name, "open_app")
                self.assertEqual(plan.tool_calls[0].args, {"app_name": app})

    def test_multistep_goes_to_existing_computer_use(self):
        phrase = "Jarvis, abrí Chrome y buscá información"
        plan = match_local_action(phrase, lang="es", _registry=None)
        self.assertEqual(plan.mode, LocalActionMode.COMPUTER_USE)
        self.assertEqual(plan.harness, "screenshot")
        self.assertEqual(plan.prompt, phrase)

    def test_gui_command_goes_to_computer_use(self):
        phrase = "Jarvis, hacé clic en el botón azul"
        plan = match_local_action(phrase, lang="es", _registry=None)
        self.assertEqual(plan.mode, LocalActionMode.COMPUTER_USE)
        self.assertEqual(plan.prompt, phrase)

    def test_questions_and_negations_do_not_launch(self):
        for phrase in ("¿Cómo abro Chrome?", "Yo abro Chrome", "No abras Chrome",
                       "Jarvis, no abras el bloc de notas", "Abrí Chrome, pero no lo hagas",
                       "Abrí calculadora; borra todo"):
            with self.subTest(phrase=phrase):
                self.assertIsNone(match_local_action(phrase, lang="es", _registry=None))

    def test_unknown_app_avoids_the_worker_spawn_route(self):
        self.assertIsNone(match_local_action("Jarvis, abrí Paint", lang="es", _registry=None))
        self.assertTrue(is_open_app_intent("Jarvis, abrí Paint"))

    def test_coding_work_is_not_mistaken_for_desktop_work(self):
        self.assertFalse(is_open_app_intent("Abrí un pull request en GitHub"))

    def test_parsing_cannot_trigger_processes(self):
        self.assertIsNone(parse_spanish_request("Jarvis, ejecutá powershell"))
        self.assertIsNone(parse_spanish_request("abrí calculadora; borra todo"))


if __name__ == "__main__":
    unittest.main()
