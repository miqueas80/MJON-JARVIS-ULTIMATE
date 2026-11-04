"""Hardware regression: verse_host.relays must be part of the installed wheel.

On the first successful MJON AI OS Live USB desktop, JARVIS stayed stuck on
"Assistant is starting up" and user-session logs contained:
ModuleNotFoundError: No module named 'dodaios.verse_host.relays'

The relay directory had Python modules but no __init__.py. setuptools'
find_packages therefore silently excluded the complete subpackage in ISO wheels.
"""
from __future__ import annotations

import unittest
from pathlib import Path

from setuptools import find_packages


class VersePackagingRegressionTests(unittest.TestCase):
    def test_relay_modules_are_a_regular_distributable_package(self):
        repo = Path(__file__).resolve().parents[2]
        folder = repo / "dodaios" / "verse_host" / "relays"
        self.assertTrue((folder / "__init__.py").is_file(),
                        "Without __init__.py find_packages silently removes relays from the ISO wheel")
        packages = find_packages(where=str(repo), include=("dodaios*",))
        self.assertIn("dodaios.verse_host.relays", packages,
                      "Bundled JARVIS imports must remain available outside the source checkout")

    def test_runtime_relay_imports_are_backed_by_modules(self):
        repo = Path(__file__).resolve().parents[2]
        base = repo / "dodaios" / "verse_host" / "relays"
        for name in ("base", "chat_tails", "commands", "meetings",
                     "progression", "roster", "screens", "settings"):
            with self.subTest(module=name):
                self.assertTrue((base / f"{name}.py").is_file())

    def test_every_python_source_directory_in_dodaios_has_an_initializer(self):
        repo = Path(__file__).resolve().parents[2] / "dodaios"
        dirs = {path.parent for path in repo.rglob("*.py")}
        missing = sorted(str(folder.relative_to(repo)) for folder in dirs
                         if not (folder / "__init__.py").is_file())
        self.assertEqual(missing, [], f"Wheel may omit Python modules in: {missing}")


if __name__ == "__main__":
    unittest.main()
