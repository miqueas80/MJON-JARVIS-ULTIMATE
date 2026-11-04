"""Prepare a Debian 13 live-build tree with the fork's own Dodaios wheel.

Preparation uses only Python's standard library and makes no system changes.
An ISO is produced only by a separate explicit ``lb config`` / ``lb build``.
"""
from __future__ import annotations

import argparse
from email.parser import Parser
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import tomllib
from zipfile import BadZipFile, ZipFile


_RESOURCE_ROOT = Path(__file__).resolve().parent / 'live'
_REQUIRED_WHEEL_FILES = frozenset({
    'mjon_jarvis/spanish_bridge.py',
    'mjon_os/config_paths.py',
    'mjon_os/ai_fabric.py',
    'mjon_os/ai_center.py',
    'mjon_os/local_inference.py',
    'dodaios/ui/web/dist/index.html',
    'dodaios/verse_host/relays/__init__.py',
    'dodaios/verse_host/relays/base.py',
    'dodaios/verse_host/relays/chat_tails.py',
    'dodaios/verse_host/relays/commands.py',
    'dodaios/verse_host/relays/meetings.py',
    'dodaios/verse_host/relays/progression.py',
    'dodaios/verse_host/relays/roster.py',
    'dodaios/verse_host/relays/screens.py',
    'dodaios/verse_host/relays/settings.py',
})
_AUTO_CONFIG = '''#!/bin/sh
set -eu
lb config noauto \
  --distribution trixie \
  --architecture amd64 \
  --binary-image iso-hybrid \
  --bootloaders "syslinux grub-efi" \
  --debian-installer none \
  --archive-areas "main contrib non-free-firmware" \
  --apt-recommends false \
  --bootappend-live "boot=live components locales=es_AR.UTF-8 keyboard-layouts=latam console=tty0 console=ttyS0,115200n8 systemd.show_status=1" \
  "${@}"
'''


def validate_wheel(path: Path) -> str:
    """Fail closed if the payload lacks the integrated MJON OS code.

    File validation is not an authenticity signature. Build the wheel yourself
    from the reviewed fork and retain the SHA256 record in the image workspace.
    """
    if not path.is_file() or path.suffix != '.whl':
        raise ValueError('A built local .whl file is required')
    try:
        with ZipFile(path) as archive:
            names = set(archive.namelist())
            metadata_files = [name for name in names if name.endswith('.dist-info/METADATA')]
            if len(metadata_files) != 1:
                raise ValueError('Wheel must contain exactly one METADATA file')
            metadata = Parser().parsestr(archive.read(metadata_files[0]).decode('utf-8'))
            if metadata.get('Name', '').casefold().replace('_', '-') != 'dodaios':
                raise ValueError('Wheel must be the forked Dodaios distribution')
            version = metadata.get('Version', '')
            if not version:
                raise ValueError('Wheel is missing its version')
            missing = _REQUIRED_WHEEL_FILES - names
            if missing:
                if 'dodaios/ui/web/dist/index.html' in missing:
                    raise ValueError('Wheel lacks the built desktop frontend')
                if any(name.startswith('dodaios/verse_host/relays/') for name in missing):
                    raise ValueError('Wheel lacks Verse relays needed by the desktop: ' + ', '.join(sorted(missing)))
                raise ValueError('Wheel lacks native MJON modules: ' + ', '.join(sorted(missing)))
            return version
    except (BadZipFile, UnicodeError, OSError) as exc:
        raise ValueError(f'Invalid wheel: {exc}') from exc


def prepare_image(*, repo_root: Path, wheel: Path, destination: Path) -> dict[str, str]:
    """Stage a reproducible live-build workspace without touching user disks."""
    repo_root = repo_root.resolve()
    wheel = wheel.resolve()
    destination = destination.resolve()
    if destination.exists():
        raise FileExistsError(f'Build directory already exists: {destination}')
    for item in ('LICENSE', 'NOTICE', 'dodaios.toml.example'):
        if not (repo_root / item).is_file():
            raise FileNotFoundError(repo_root / item)
    version = validate_wheel(wheel)
    if (repo_root / 'pyproject.toml').is_file():
        project = tomllib.loads((repo_root / 'pyproject.toml').read_text(encoding='utf-8'))
        if project['project']['version'] != version:
            raise ValueError('Wheel version differs from fork pyproject.toml')

    checksum = hashlib.sha256(wheel.read_bytes()).hexdigest()
    metadata = {
        'product': 'MJON AI OS',
        'base': 'Debian 13 (trixie)',
        'desktop': 'KDE Plasma',
        'arch': 'amd64',
        'engine': 'Dodaios (MJON fork)',
        'engine_version': version,
        'wheel': wheel.name,
        'wheel_sha256': checksum,
        'status': 'build candidate: not release-tested',
    }

    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.mjon-stage-', dir=destination.parent) as temporary:
        staging = Path(temporary) / 'workspace'
        shutil.copytree(_RESOURCE_ROOT / 'config', staging / 'config')
        auto_dir = staging / 'auto'
        auto_dir.mkdir()
        config_script = auto_dir / 'config'
        config_script.write_text(_AUTO_CONFIG, encoding='utf-8')
        config_script.chmod(0o755)
        hook = staging / 'config/hooks/live/90-mjon-agent.hook.chroot'
        hook.chmod(0o755)
        launcher = staging / 'config/includes.chroot/usr/local/bin/mjon-session'
        launcher.chmod(0o755)
        doctor = staging / 'config/includes.chroot/usr/local/bin/mjon-doctor'
        doctor.chmod(0o755)
        vm_marker = staging / 'config/includes.chroot/usr/local/bin/mjon-vm-proof'
        vm_marker.chmod(0o755)
        # KDE Plasma only treats desktop shortcuts as trusted when executable.
        # Keep a single installed app entry and a first-login Desktop shortcut.
        for relative in (
            'usr/local/bin/mjon-control-center',
            'etc/skel/Desktop/Centro-de-mando-MJON.desktop',
        ):
            (staging / 'config/includes.chroot' / relative).chmod(0o755)

        includes = staging / 'config/includes.chroot'
        wheels_dir = includes / 'opt/mjon-ai-os/wheels'
        wheels_dir.mkdir(parents=True)
        shutil.copy2(wheel, wheels_dir / wheel.name)
        config_dir = includes / 'usr/share/mjon-ai-os'
        config_dir.mkdir(parents=True)
        shutil.copy2(repo_root / 'dodaios.toml.example', config_dir / 'dodaios.toml.example')
        (config_dir / 'build-manifest.json').write_text(
            json.dumps(metadata, indent=2, ensure_ascii=False) + '\n', encoding='utf-8',
        )
        license_dir = includes / 'usr/share/doc/mjon-ai-os/upstream'
        license_dir.mkdir(parents=True)
        for name in ('LICENSE', 'NOTICE'):
            shutil.copy2(repo_root / name, license_dir / name)
        (staging / 'mjon-build.json').write_text(
            json.dumps(metadata, indent=2, ensure_ascii=False) + '\n', encoding='utf-8',
        )
        # The final rename only occurs after preparation has fully succeeded.
        os.replace(staging, destination)
    return metadata


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Prepare a unified MJON AI OS Debian Live image tree')
    parser.add_argument('--repo-root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--wheel', type=Path, required=True, help='Built wheel from this fork')
    parser.add_argument('--workdir', type=Path, required=True, help='NEW destination; never overwritten')
    args = parser.parse_args(argv)
    try:
        result = prepare_image(repo_root=args.repo_root, wheel=args.wheel, destination=args.workdir)
    except (ValueError, FileExistsError, FileNotFoundError, KeyError) as exc:
        parser.exit(2, f'MJON image preparation failed: {exc}\n')
    print(json.dumps(result, indent=2, ensure_ascii=False))
    print(f'Prepared {args.workdir}. Build explicitly with: cd "{args.workdir}" && sudo lb config && sudo lb build')
    return 0


if __name__ == '__main__':
    sys.exit(main())
