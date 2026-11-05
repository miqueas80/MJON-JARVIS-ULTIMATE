"""Create user-writable native settings once, without changing upstream data."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import tomllib

_REQUIRED = ('trigger.wake_word', 'stt', 'memory', 'autostart')
_OVERRIDES = {
    ('trigger.wake_word', 'phrase'): 'Jarvis',
    ('stt', 'language'): 'es',
    ('autostart', 'enabled'): False,
    # The upstream template is cloud-first (Gemini). A fresh MJON Live profile
    # must instead select the real local provider, without requiring API keys.
    # Ollama discovers existing local weights; this does not install or pull any.
    ('brain', 'primary'): 'ollama',
    ('brain', 'fallback'): 'ollama',
    ('brain', 'deep_brain'): 'ollama',
    ('brain', 'routing_provider'): 'ollama',
    ('brain', 'routing_model'): '',
}


def personalize_template(source: str, data_directory: Path) -> str:
    """Set native offline brain, private data, Spanish defaults, preserving other options.

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



# Only an untouched cloud-first config is eligible for opt-in migration.
# Personalized cloud provider choices must never be silently overwritten.
_CLOUD_BRAIN_DEFAULTS = {
    'primary': 'gemini',
    'fallback': 'gemini',
    'deep_brain': 'gemini',
    'routing_provider': 'gemini',
    'routing_model': 'gemini-3.5-flash',
}
_LOCAL_BRAIN_DEFAULTS = {
    'primary': 'ollama',
    'fallback': 'ollama',
    'deep_brain': 'ollama',
    'routing_provider': 'ollama',
    'routing_model': '',
}


def activate_local_brain(config_file: Path) -> bool:
    """Opt-in migration of an existing, uncustomized cloud-first native profile.

    Preserve all unrelated settings, retain a private backup and atomically
    replace the per-user TOML. Does not install models or restart any service.
    """
    if not config_file.is_absolute() or config_file.is_symlink() or not config_file.is_file():
        raise ValueError('Se requiere un archivo de configuración regular y absoluto.')
    raw = config_file.read_text(encoding='utf-8')
    settings = tomllib.loads(raw)
    brain = settings.get('brain')
    if not isinstance(brain, dict):
        raise ValueError('Falta la sección [brain] de la configuración.')
    if all(brain.get(key) == value for key, value in _LOCAL_BRAIN_DEFAULTS.items()):
        return False
    if any(brain.get(key) != value for key, value in _CLOUD_BRAIN_DEFAULTS.items()):
        raise ValueError('El proveedor ya fue personalizado; no se cambiará automáticamente.')

    table = ''
    seen: set[str] = set()
    output: list[str] = []
    for line in raw.splitlines(keepends=True):
        section = re.match(r'^\s*\[([^\]]+)\]\s*(?:#.*)?$', line.strip())
        if section:
            table = section.group(1).strip()
        assignment = re.match(r'^(\s*)([a-zA-Z_][a-zA-Z_0-9-]*)\s*=(.*)$', line)
        if table == 'brain' and assignment and assignment.group(2) in _LOCAL_BRAIN_DEFAULTS:
            key = assignment.group(2)
            output.append(f'{assignment.group(1)}{key} = {json.dumps(_LOCAL_BRAIN_DEFAULTS[key])}\n')
            seen.add(key)
        else:
            output.append(line)
    if seen != set(_LOCAL_BRAIN_DEFAULTS):
        raise ValueError('No se encontraron todas las opciones de [brain].')
    updated = ''.join(output)
    tomllib.loads(updated)

    backup = config_file.with_suffix(config_file.suffix + '.bak')
    # O_EXCL prevents overwriting an existing backup (including a symlink).
    with os.fdopen(os.open(backup, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600),
                   'w', encoding='utf-8') as handle:
        handle.write(raw)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile('w', encoding='utf-8',
                                         dir=config_file.parent, prefix='.mjon-brain-',
                                         delete=False) as handle:
            temporary = Path(handle.name)
            os.chmod(temporary, 0o600)
            handle.write(updated)
        os.replace(temporary, config_file)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Provision MJON AI OS user profile')
    parser.add_argument('--template', type=Path)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--data', type=Path)
    parser.add_argument('--activate-ollama', action='store_true',
                        help='Opt-in local provider for an unchanged native cloud profile')
    args = parser.parse_args(argv)
    if args.activate_ollama:
        try:
            changed = activate_local_brain(args.config)
        except (OSError, ValueError, tomllib.TOMLDecodeError) as exc:
            parser.exit(2, str(exc) + '\n')
        print('Proveedor Ollama configurado.' if changed
              else 'JARVIS ya usa Ollama; sin cambios.')
        return 0
    if args.template is None or args.data is None:
        parser.error('--template y --data son obligatorios para la configuración inicial')
    provision_user_config(args.template, args.config, args.data)
    return 0


if __name__ == '__main__':
    sys.exit(main())
