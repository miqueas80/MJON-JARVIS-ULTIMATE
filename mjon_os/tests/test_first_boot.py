"""Per-user bootstrap contracts: no root writes or overwritten preferences."""
from __future__ import annotations

import tempfile
import tomllib
import unittest
from pathlib import Path

from mjon_os.first_boot import personalize_template, provision_user_config


_SAMPLE = '''[trigger.wake_word]
phrase = ""
engine = "auto"
[stt]
language = "auto"
[memory]
data_dir = "./data" # original
[autostart]
enabled = true
[other]
enabled = true
'''


class FirstBootTests(unittest.TestCase):
    def test_personalization_preserves_other_fields_and_sets_jarvis(self):
        raw = personalize_template(_SAMPLE, Path('/home/demouser/.local/share/mjon-ai-os'))
        fields = tomllib.loads(raw)
        self.assertEqual(fields['trigger']['wake_word']['phrase'], 'Jarvis')
        self.assertEqual(fields['stt']['language'], 'es')
        self.assertEqual(fields['memory']['data_dir'], '/home/demouser/.local/share/mjon-ai-os')
        self.assertFalse(fields['autostart']['enabled'])
        self.assertTrue(fields['other']['enabled'])

    def test_config_creation_is_private_and_writable(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            template = base/'source.toml'
            template.write_text(_SAMPLE, encoding='utf-8')
            config = base/'settings'/'dodaios.toml'
            data = base/'state'
            self.assertTrue(provision_user_config(template, config, data))
            self.assertEqual(config.stat().st_mode & 0o777, 0o600)
            self.assertTrue(data.is_dir())
            self.assertEqual(tomllib.loads(config.read_text())['memory']['data_dir'], str(data))

    def test_existing_user_configuration_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            template = base/'source.toml'
            template.write_text(_SAMPLE, encoding='utf-8')
            config = base/'config'/'dodaios.toml'
            config.parent.mkdir()
            config.write_text('customized = true\n', encoding='utf-8')
            self.assertFalse(provision_user_config(template, config, base/'data'))
            self.assertEqual(config.read_text(), 'customized = true\n')

    def test_reject_incomplete_template(self):
        with self.assertRaises(ValueError):
            personalize_template('[other]\nanswer = 42\n', Path('/tmp/data'))

    def test_relative_data_directory_is_rejected(self):
        with self.assertRaises(ValueError):
            personalize_template(_SAMPLE, Path('data'))


if __name__ == '__main__':
    unittest.main()
