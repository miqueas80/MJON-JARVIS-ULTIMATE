import unittest
from mjon_jarvis.commands import interpret_command

class CommandTests(unittest.TestCase):
    def test_spanish_open_notepad(self):
        self.assertEqual(interpret_command("Jarvis, abrí el bloc de notas"), ("launch", "notepad"))
    def test_spanish_open_calculator(self):
        self.assertEqual(interpret_command("abrir calculadora"), ("launch", "calc"))
    def test_no_untrusted_execution(self):
        self.assertIsNone(interpret_command("ejecutá powershell -enc ABC"))
    def test_no_substring_match(self):
        self.assertIsNone(interpret_command("abrí calculadora y borrá todo"))
    def test_whitespace(self):
        self.assertEqual(interpret_command("  JARVIS,   abre   explorador de archivos  "), ("launch", "explorer"))
