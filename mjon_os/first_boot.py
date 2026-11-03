"""Create user-writable native settings once, without changing upstream data."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import sys
import tomllib

_REQUIRED = ('trigger.wake_word', 'stt', 'memory', 'autostart')
_OVERRIDES = {
    ('trigger.wake_word', 'phrase'): 'Jarvis',
    ('stt', 'language'): 'es',
    ('autostart', 'enabled'): False,
}


def personalize_template(source: str, data_directory: Path) -> str:
    """Set private data storage and Spanish defaults while preserving all other options.

    The upstream autostart is disabled because the OS already supervises a
    single session process through the graphical-user systemd service.
    """
    if not data_directory.is_absolute():
        raise ValueError('Native user data path must be absolute')
    table = ''
    seen: set[tuple[str, str]] = set()
    overrides = {**_OVERRIDES, ('memory', 'data_dir'): str(data_directory)}
    result: list[str] = []
    for line in source.splitlines(keepends=True):
        match = re.match(r'^\s*\[([^\]]+)\]\s*(?:#.*)?$', line.strip())
        if match:
            table = match.group(1).strip()
            result.append(line)
            continue
        assignment = re.match(r'^(\s*)([a-zA-Z_][a-zA-Z_0-9-]*)\s*=(.*)$', line)
        if assignment and (table, assignment.group(2)) in overrides:
            key = (table, assignment.group(2))
            value = overrides[key]
            encoded = 'true' if value is True else 'false' if value is False else json.dumps(value, ensure_ascii=False)
            result.append(f'{assignment.group(1)}{key[1]} = {encoded}\n')
            seen.add(key)
        else:
            result.append(line)
    if seen != set(overrides):
        missing = ', '.join(f'{table}.{key}' for table, key in sorted(set(overrides) - seen))
        raise ValueError('Native config template missing required settings: ' + missing)
    personalized = ''.join(result)
    # Refuse a malformed template rather than leaving an unbootable profile.
    parsed = tomllib.loads(personalized)
    if not all(part in parsed for part in ('memory', 'stt', 'autostart')):
        raise ValueError('Invalid configuration template')
    return personalized


def provision_user_config(template: Path, config_file: Path, data_directory: Path) -> bool:
    """Create a private config only if absent; never modify existing preferences.

    Returns True only if this process created it. O_EXCL also rejects symlinks
    and closes the race between two simultaneous graphical startup requests.
    """
    if not config_file.is_absolute() or not data_directory.is_absolute():
        raise ValueError('Native state paths must be absolute')
    config_file.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    data_directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    if config_file.exists() or config_file.is_symlink():
        return False
    personalized = personalize_template(template.read_text(encoding='utf-8'), data_directory)
    try:
        descriptor = os.open(config_file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        return False
    try:
        with os.fdopen(descriptor, 'w', encoding='utf-8') as handle:
            handle.write(personalized)
    except BaseException:
        config_file.unlink(missing_ok=True)
        raise
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Provision MJON AI OS user profile')
    parser.add_argument('--template', type=Path, required=True)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--data', type=Path, required=True)
    args = parser.parse_args(argv)
    provision_user_config(args.template, args.config, args.data)
    return 0


if __name__ == '__main__':
    sys.exit(main())
