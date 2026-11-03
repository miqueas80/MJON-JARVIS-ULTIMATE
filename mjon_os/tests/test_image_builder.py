"""Contract tests for the unified MJON AI OS image preparation stage."""
from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

from mjon_os.config_paths import config_root
from mjon_os.image_builder import prepare_image, validate_wheel


class ConfigRootTests(unittest.TestCase):
    def test_default_preserves_upstream(self) -> None:
        self.assertEqual(config_root(Path('/some/checkout'), {}), Path('/some/checkout'))

    def test_native_os_uses_per_user_path(self) -> None:
        target = (Path.cwd() / 'test-user' / '.config' / 'mjon-ai-os').resolve()
        self.assertEqual(config_root(Path('/some/checkout'), {'MJON_AI_OS_CONFIG_ROOT': str(target)}), target)

    def test_empty_override_does_not_change_upstream(self) -> None:
        self.assertEqual(config_root(Path('/some/checkout'), {'MJON_AI_OS_CONFIG_ROOT': '  '}), Path('/some/checkout'))


class LiveImageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.repo = self.base / 'repo'
        self.repo.mkdir()
        for name in ('LICENSE', 'NOTICE', 'dodaios.toml.example'):
            (self.repo / name).write_text('sample for ' + name, encoding='utf-8')
        self.wheel = self.base / 'dodaios-4.1.2-py3-none-any.whl'
        with ZipFile(self.wheel, 'w') as archive:
            archive.writestr('dodaios-4.1.2.dist-info/METADATA', 'Metadata-Version: 2.3\nName: dodaios\nVersion: 4.1.2\n')
            archive.writestr('mjon_jarvis/spanish_bridge.py', '# MJON')
            archive.writestr('mjon_os/config_paths.py', '# MJON')

    def test_wheel_metadata_must_name_dodaios(self) -> None:
        self.assertEqual(validate_wheel(self.wheel), '4.1.2')
        wrong = self.base / 'fake.whl'
        with ZipFile(wrong, 'w') as archive:
            archive.writestr('fake-0.1.dist-info/METADATA', 'Name: fake\nVersion: 0.1\n')
        with self.assertRaises(ValueError):
            validate_wheel(wrong)

    def test_preparation_copies_wheel_and_live_configuration(self) -> None:
        work = self.base / 'work'
        metadata = prepare_image(repo_root=self.repo, wheel=self.wheel, destination=work)
        self.assertEqual(metadata['product'], 'MJON AI OS')
        self.assertEqual(metadata['engine_version'], '4.1.2')
        self.assertEqual(metadata['wheel_sha256'], hashlib.sha256(self.wheel.read_bytes()).hexdigest())
        self.assertTrue((work / 'auto/config').exists())
        self.assertIn('trixie', (work / 'auto/config').read_text())
        self.assertTrue((work / 'config/package-lists/mjon.list.chroot').exists())
        self.assertTrue((work / 'config/hooks/live/90-mjon-agent.hook.chroot').exists())
        self.assertTrue((work / 'config/includes.chroot/opt/mjon-ai-os/wheels' / self.wheel.name).is_file())
        self.assertTrue((work / 'config/includes.chroot/etc/xdg/autostart/mjon-ai-os.desktop').is_file())
        self.assertTrue((work / 'config/includes.chroot/usr/lib/systemd/user/mjon-jarvis.service').is_file())
        saved = json.loads((work / 'mjon-build.json').read_text())
        self.assertEqual(saved, metadata)

    def test_non_empty_directory_is_not_overwritten(self) -> None:
        work = self.base / 'existing'
        work.mkdir()
        important = work / 'untouched.txt'
        important.write_text('preserve', encoding='utf-8')
        with self.assertRaises(FileExistsError):
            prepare_image(repo_root=self.repo, wheel=self.wheel, destination=work)
        self.assertEqual(important.read_text(), 'preserve')

    def test_missing_default_configuration_fails_before_writing(self) -> None:
        (self.repo / 'dodaios.toml.example').unlink()
        work = self.base / 'work'
        with self.assertRaises(FileNotFoundError):
            prepare_image(repo_root=self.repo, wheel=self.wheel, destination=work)
        self.assertFalse(work.exists())


if __name__ == '__main__':
    unittest.main()
