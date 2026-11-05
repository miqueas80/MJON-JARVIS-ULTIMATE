"""Per-user bootstrap contracts: no root writes or overwritten preferences."""
from __future__ import annotations

import os
import tempfile
import tomllib
import unittest
from pathlib import Path

from mjon_os.first_boot import activate_local_brain, personalize_template, provision_user_config


_SAMPLE = '''[trigger.wake_word]
phrase = ""
engine = "auto"
[stt]
language = "auto"
[memory]
data_dir = "./data" # original
[autostart]
enabled = true
[brain]
primary = "gemini"
fallback = "gemini"
deep_brain = "gemini"
routing_provider = "gemini"
routing_model = "gemini-3.5-flash"
[other]
enabled = true
'''


class FirstBootTests(unittest.TestCase):
    def test_real_upstream_config_template_can_be_personalized(self):
        template = Path(__file__).resolve().parents[2] / 'dodaios.toml.example'
        data = (Path.cwd() / 'native-user-data').resolve()
        personalized = personalize_template(template.read_text(encoding='utf-8'), data)
        decoded = tomllib.loads(personalized)
        self.assertEqual(decoded['trigger']['wake_word']['phrase'], 'Jarvis')
        self.assertEqual(decoded['memory']['data_dir'], str(data))
        self.assertEqual(decoded['stt']['language'], 'es')
        self.assertFalse(decoded['autostart']['enabled'])
        self.assertEqual(decoded['brain']['primary'], 'ollama')
        self.assertEqual(decoded['brain']['fallback'], 'ollama')
        self.assertEqual(decoded['brain']['deep_brain'], 'ollama')
        self.assertEqual(decoded['brain']['routing_provider'], 'ollama')
        self.assertEqual(decoded['brain']['routing_model'], '')
        self.assertEqual(decoded['brain']['local_fallback'], 'ollama')
        self.assertEqual(decoded['brain']['local_fallback_model'], '')
        self.assertEqual(decoded['brain']['max_tokens'], 256)


    def test_personalization_preserves_other_fields_and_sets_jarvis(self):
        data_directory = (Path.cwd() / 'test-user' / '.local' / 'share' / 'mjon-ai-os').resolve()
        raw = personalize_template(_SAMPLE, data_directory)
        fields = tomllib.loads(raw)
        self.assertEqual(fields['trigger']['wake_word']['phrase'], 'Jarvis')
        self.assertEqual(fields['stt']['language'], 'es')
        self.assertEqual(fields['memory']['data_dir'], str(data_directory))
        self.assertFalse(fields['autostart']['enabled'])
        self.assertTrue(fields['other']['enabled'])
        self.assertEqual(fields['brain']['primary'], 'ollama')
        self.assertEqual(fields['brain']['routing_provider'], 'ollama')
        self.assertEqual(fields['brain']['routing_model'], '')

    def test_config_creation_is_private_and_writable(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            template = base/'source.toml'
            template.write_text(_SAMPLE, encoding='utf-8')
            config = base/'settings'/'dodaios.toml'
            data = base/'state'
            self.assertTrue(provision_user_config(template, config, data))
            if os.name == 'posix':
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


    def test_existing_untouched_cloud_profile_can_opt_in_to_ollama(self):
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / 'dodaios.toml'
            config.write_text(_SAMPLE, encoding='utf-8')
            self.assertTrue(activate_local_brain(config))
            modified = tomllib.loads(config.read_text(encoding='utf-8'))
            self.assertEqual(modified['brain']['primary'], 'ollama')
            self.assertEqual(modified['brain']['fallback'], 'ollama')
            self.assertEqual(modified['brain']['deep_brain'], 'ollama')
            self.assertEqual(modified['brain']['routing_provider'], 'ollama')
            self.assertEqual(modified['brain']['routing_model'], '')
            self.assertTrue(modified['other']['enabled'])
            backup = config.with_suffix('.toml.bak')
            self.assertEqual(backup.read_text(encoding='utf-8'), _SAMPLE)
            if os.name == 'posix':
                self.assertEqual(backup.stat().st_mode & 0o777, 0o600)
            self.assertFalse(activate_local_brain(config))

    def test_custom_cloud_provider_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / 'dodaios.toml'
            custom = _SAMPLE.replace('primary = "gemini"', 'primary = "openai"')
            config.write_text(custom, encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'personalizado'):
                activate_local_brain(config)
            self.assertEqual(config.read_text(encoding='utf-8'), custom)
            self.assertFalse(config.with_suffix('.toml.bak').exists())

    def test_symlinked_config_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            real = Path(directory) / 'real.toml'
            real.write_text(_SAMPLE, encoding='utf-8')
            link = Path(directory) / 'dodaios.toml'
            link.symlink_to(real)
            with self.assertRaises(ValueError):
                activate_local_brain(link)


if __name__ == '__main__':
    unittest.main()
