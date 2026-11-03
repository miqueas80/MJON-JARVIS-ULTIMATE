"""Pure path selection for the OS-native multi-user configuration layout."""
from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path


def config_root(upstream_root: Path, environment: Mapping[str, str]) -> Path:
    """Leave Dodaios unchanged unless the MJON OS launcher explicitly opts in.

    The distribution launcher sets an absolute, per-user configuration directory.
    Other Dodaios installations continue to use their original project root.
    """
    override = environment.get('MJON_AI_OS_CONFIG_ROOT', '').strip()
    if not override:
        return upstream_root
    candidate = Path(override).expanduser()
    if not candidate.is_absolute():
        raise ValueError('MJON_AI_OS_CONFIG_ROOT must be an absolute path')
    return candidate
