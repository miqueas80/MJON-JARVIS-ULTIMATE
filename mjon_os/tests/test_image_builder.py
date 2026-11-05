"""Contract tests for the unified MJON AI OS image preparation stage."""
from __future__ import annotations

import hashlib
import json
import os
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
            archive.writestr('mjon_os/ai_fabric.py', '# MJON')
            archive.writestr('mjon_os/ai_center.py', '# MJON')
            archive.writestr('mjon_os/local_inference.py', '# MJON')
            for module in ('ollama_policy', 'jarvis_probe', 'offline_payload'):
                archive.writestr(f'mjon_os/{module}.py', '# MJON')
            archive.writestr('dodaios/ui/web/dist/index.html', '<!doctype html><title>MJON</title>')
            for module in ('__init__', 'base', 'chat_tails', 'commands',
                           'meetings', 'progression', 'roster', 'screens', 'settings'):
                archive.writestr(f'dodaios/verse_host/relays/{module}.py',
                                 '# Test fixture: replace with real source in production')

    def test_wheel_metadata_must_name_dodaios(self) -> None:
        self.assertEqual(validate_wheel(self.wheel), '4.1.2')
        wrong = self.base / 'fake.whl'
        with ZipFile(wrong, 'w') as archive:
            archive.writestr('fake-0.1.dist-info/METADATA', 'Name: fake\nVersion: 0.1\n')
        with self.assertRaises(ValueError):
            validate_wheel(wrong)

    def test_image_declares_required_gtk_desktop_runtime(self) -> None:
        root = Path(__file__).resolve().parents[1] / 'live' / 'config'
        packages = (root / 'package-lists/mjon.list.chroot').read_text(encoding='utf-8')
        for package in ('python3-gi', 'python3-gi-cairo', 'gir1.2-gtk-3.0',
                        'gir1.2-webkit2-4.1', 'xwayland',
                        'kate', 'kcalc', 'dolphin', 'konsole',
                        'sddm', 'sddm-theme-debian-breeze', 'libpam-systemd',
                        'live-boot', 'live-config', 'live-config-systemd',
                        'user-setup', 'sudo', 'pamtester',
                        # Hardware RTL8822CE booted and loaded firmware, yet
                        # NetworkManager showed Wi-Fi unavailable. With
                        # apt-recommends disabled its Wi-Fi backend was omitted.
                        'wpasupplicant', 'wireless-regdb', 'rfkill', 'plasma-nm',
                        'firmware-iwlwifi', 'firmware-realtek', 'firmware-atheros',
                        'firmware-sof-signed'):
            self.assertIn(package, packages.splitlines())
        hook = (root / 'hooks/live/90-mjon-agent.hook.chroot').read_text(encoding='utf-8')
        self.assertIn('--system-site-packages', hook)
        self.assertIn('"$1[desktop]"', hook)
        self.assertIn('mjon_os, webview', hook)
        # The original ISO failed because srt (a Vosk dependency) has no wheel.
        self.assertNotIn('--only-binary=:all:', hook)
        self.assertIn('--prefer-binary', hook)
        guest_probe = (root / 'includes.chroot/usr/local/bin/mjon-vm-proof').read_text(encoding='utf-8')
        self.assertIn('pamtester login user authenticate', guest_probe)
        self.assertIn('LIVE_USER_READY', guest_probe)

    def test_rejects_wheel_without_verse_host_relays(self) -> None:
        # Regression from the actual Live USB: web UI stuck on "Starting..."
        # because find_packages skipped an uninitialized relay directory.
        wheel = self.base / 'missing-relays.whl'
        with ZipFile(wheel, 'w') as archive:
            archive.writestr('dodaios-4.1.2.dist-info/METADATA',
                             'Metadata-Version: 2.3\nName: dodaios\nVersion: 4.1.2\n')
            archive.writestr('mjon_jarvis/spanish_bridge.py', '# MJON')
            archive.writestr('mjon_os/config_paths.py', '# MJON')
            archive.writestr('dodaios/ui/web/dist/index.html', '<title>MJON</title>')
        with self.assertRaisesRegex(ValueError, 'Verse relays'):
            validate_wheel(wheel)

    def test_rejects_wheel_without_built_frontend(self) -> None:
        path = self.base / 'missing-ui.whl'
        with ZipFile(path, 'w') as archive:
            archive.writestr('dodaios-4.1.2.dist-info/METADATA', 'Name: dodaios\nVersion: 4.1.2\n')
            archive.writestr('mjon_jarvis/spanish_bridge.py', '# MJON')
            archive.writestr('mjon_os/config_paths.py', '# MJON')
        with self.assertRaisesRegex(ValueError, 'frontend'):
            validate_wheel(path)

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
        self.assertTrue((work / 'config/includes.chroot/usr/local/bin/mjon-doctor').is_file())
        # First-run graphical configuration must not need a terminal. Plasma
        # refuses to trust a non-executable desktop shortcut on initial login.
        control_desktop = work / 'config/includes.chroot/etc/skel/Desktop/Centro-de-mando-MJON.desktop'
        self.assertTrue(control_desktop.is_file())
        control_launcher = work / 'config/includes.chroot/usr/local/bin/mjon-control-center'
        self.assertTrue(control_launcher.is_file())
        # Windows NTFS/Python do not expose Linux executable mode bits.
        # Verify permissions on the POSIX builder that actually creates the ISO.
        if os.name == 'posix':
            self.assertNotEqual(control_desktop.stat().st_mode & 0o111, 0)
            self.assertNotEqual(control_launcher.stat().st_mode & 0o111, 0)
        self.assertTrue((work / 'config/includes.chroot/usr/local/bin/mjon-vm-proof').is_file())
        service = (work / 'config/includes.chroot/usr/lib/systemd/system/mjon-vm-proof.service').read_text()
        self.assertIn('ConditionVirtualization=vm', service)
        self.assertEqual(json.loads((work / 'config/includes.chroot/usr/share/mjon-ai-os/build-manifest.json').read_text()), metadata)
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
