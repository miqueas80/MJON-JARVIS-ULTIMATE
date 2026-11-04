"""Windows-specific, read-only control bridge for MJON AI OS.

This module deliberately reuses the tested, platform-independent AI fabric,
Ollama loopback adapter, and original JARVIS status reader. It never installs
engines, downloads weights, changes security policy, or silently calls cloud
services. The approved Windows UI is a separate responsibility.
"""
from __future__ import annotations

from dataclasses import dataclass
import importlib.metadata
import os
from pathlib import Path, PureWindowsPath
import platform
import shutil
from typing import Any, Callable, Mapping

from mjon_jarvis.system_status import read_status
from mjon_os.ai_fabric import CATALOG, CapabilityPlan
from mjon_os.local_inference import OllamaClient


# Linux-specific services are not Windows features. Optional dependencies
# with no supported native Windows installation path are deliberately withheld.
_WINDOWS_EXCLUDED = frozenset({
    "zram", "apparmor", "bubblewrap", "openvoiceos", "mjon_anr",
    "vllm", "sglang", "unsloth", "axolotl",
})
_EXECUTABLE_ALIASES = {"python3": "python", "code-oss": "code"}

# Fixed Microsoft settings URI allowlist. Caller-controlled shell commands,
# paths, web URLs and arbitrary protocol handlers are never accepted.
_SETTINGS = {
    "wifi": "ms-settings:network-wifi",
    "bluetooth": "ms-settings:bluetooth",
    "ethernet": "ms-settings:network-ethernet",
    "sound": "ms-settings:sound",
    "display": "ms-settings:display",
    "power": "ms-settings:powersleep",
    "storage": "ms-settings:storagesense",
    "apps": "ms-settings:appsfeatures",
    "privacy": "ms-settings:privacy",
    "updates": "ms-settings:windowsupdate",
}
_MIB = 1024 ** 2


def _has_distribution(name: str) -> bool:
    try:
        importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return False
    return True


def _command_present(name: str, checker: Callable[[str], bool]) -> bool:
    return checker(_EXECUTABLE_ALIASES.get(name, name))


def _installed(module: Any, checker: Callable[[str], bool],
               distributions: Callable[[str], bool]) -> bool:
    if module.remote:
        return False
    if module.executable:
        return _command_present(module.executable, checker)
    return bool(module.distribution and distributions(module.distribution))


def inspect_windows_catalog(
    *,
    executable_exists: Callable[[str], bool] | None = None,
    distribution_present: Callable[[str], bool] | None = None,
) -> list[dict[str, Any]]:
    """Detect installed binaries without claiming a usable engine/model.

    Detection alone does not imply that a local server, credentials, weights,
    speech recognition or GPU acceleration actually work.
    """
    checker = executable_exists or (lambda name: shutil.which(name) is not None)
    distributions = distribution_present or _has_distribution
    entries = []
    for module in CATALOG:
        if module.module_id in _WINDOWS_EXCLUDED:
            continue
        status = (
            "remote_opt_in" if module.remote else
            "installed_unverified" if _installed(module, checker, distributions)
            else "not_installed"
        )
        entries.append({
            "id": module.module_id,
            "name": module.title,
            "domain": module.domain,
            "status": status,
            "offline": not module.remote,
            "launch": "manual_only",
            "workstation_only": module.workstation_only,
        })
    return entries


def plan_windows_capability(
    capability: str,
    *,
    ram_bytes: int | None,
    discrete_gpu: bool = False,
    executable_exists: Callable[[str], bool] | None = None,
    distribution_present: Callable[[str], bool] | None = None,
    network_available: bool = False,
    allow_remote: bool = False,
    credentials_present: bool = False,
) -> CapabilityPlan:
    """Candidate recommendation only; never performs an automatic action.

    Unknown RAM is treated conservatively as zero, preventing an optimistic
    choice that could crash an 8 GB machine.
    """
    checker = executable_exists or (lambda name: shutil.which(name) is not None)
    distributions = distribution_present or _has_distribution
    ram_gib = max(0, ram_bytes or 0) / 1024 ** 3
    candidates = sorted(
        (m for m in CATALOG
         if m.domain == capability
         and not m.remote
         and m.module_id not in _WINDOWS_EXCLUDED),
        key=lambda m: (m.workstation_only, m.engine_priority, m.title),
    )
    approval = capability in {"agents", "programming", "automation", "security"}
    for module in candidates:
        if module.min_ram_gib > ram_gib or (module.workstation_only and not discrete_gpu):
            continue
        if _installed(module, checker, distributions):
            return CapabilityPlan(
                capability, module.module_id,
                "Ejecutable detectado; verificar servicio, pesos y permisos antes de utilizar.",
                requires_approval=approval,
            )
    if (capability == "inference" and network_available and
            allow_remote and credentials_present):
        return CapabilityPlan(
            capability, "free_llm_api",
            "Proveedor externo opcional con autorización y credenciales.",
            remote=True, requires_approval=True,
        )
    return CapabilityPlan(
        capability, None,
        "No se detectó motor compatible para este perfil. No se usa la nube automáticamente.",
        requires_approval=approval,
    )


def windows_settings(
    section: str,
    *,
    os_name: str | None = None,
    opener: Callable[[str], Any] | None = None,
) -> str:
    """Explicit user-requested navigation to native Windows Settings.

    The call only opens Microsoft Settings; it never changes a system value,
    runs a command interpreter, requests admin rights or bypasses UAC.
    """
    if (os_name or platform.system()) != "Windows":
        raise RuntimeError("Este control solamente funciona en Windows.")
    if section not in _SETTINGS:
        raise ValueError("Sección de Configuración no autorizada.")
    target = _SETTINGS[section]
    action = opener or getattr(os, "startfile", None)
    if action is None:
        raise RuntimeError("No está disponible el lanzador de configuración de Windows.")
    action(target)
    return target


@dataclass(frozen=True)
class StorageBudget:
    allowed: bool
    free_bytes: int
    required_bytes: int
    reserve_bytes: int
    reason: str


def storage_budget(
    *,
    model_bytes: int,
    free_bytes: int,
    reserve_bytes: int = 2 * 1024 ** 3,
    overhead_bytes: int | None = None,
) -> StorageBudget:
    """No-write disk safety check before any future model download.

    Requires room for model, temporary extraction/downloads and a system
    reserve. This is a preliminary conservative check, not an installation.
    """
    values = (model_bytes, free_bytes, reserve_bytes)
    if any(not isinstance(n, int) or isinstance(n, bool) or n < 0 for n in values):
        raise ValueError("Los tamaños deben ser números enteros no negativos.")
    if overhead_bytes is None:
        overhead_bytes = max(256 * _MIB, model_bytes // 10)
    if not isinstance(overhead_bytes, int) or overhead_bytes < 0:
        raise ValueError("Margen temporal inválido.")
    total = model_bytes + reserve_bytes + overhead_bytes
    allowed = free_bytes >= total
    return StorageBudget(
        allowed=allowed, free_bytes=free_bytes, required_bytes=total,
        reserve_bytes=reserve_bytes,
        reason=("Espacio suficiente para la operación." if allowed
                else "Espacio insuficiente; seleccioná otra unidad o liberá espacio."),
    )


def model_directory(
    *, env: Mapping[str, str] | None = None, home: Path | None = None,
) -> Path | PureWindowsPath:
    """Suggest a persistent per-user path. Does not create or modify it."""
    variables = os.environ if env is None else env
    local = variables.get("LOCALAPPDATA", "").strip()
    if local:
        path = PureWindowsPath(local)
        if not path.is_absolute() or local.startswith("\\\\"):
            raise ValueError("LOCALAPPDATA debe ser una ruta local absoluta.")
        return path / "MJON AI OS" / "models"
    return (home or Path.home()) / "AppData" / "Local" / "MJON AI OS" / "models"



def ollama_model_directory(
    *, env: Mapping[str, str] | None = None, home: Path | None = None,
) -> Path | PureWindowsPath:
    """Resolve Ollama's actual model volume, not the MJON-owned GGUF directory.

    Ollama uses OLLAMA_MODELS when configured and otherwise stores user
    models under %USERPROFILE%\\.ollama\\models on Windows. Observational
    only: no paths are created and UNC/relative overrides are refused.
    """
    variables = os.environ if env is None else env
    explicit = variables.get("OLLAMA_MODELS", "").strip()
    profile = variables.get("USERPROFILE", "").strip()
    root = explicit or profile
    if root:
        path = PureWindowsPath(root)
        if not path.is_absolute() or root.startswith("\\\\") or ".." in path.parts:
            raise ValueError("Ruta de modelos Ollama inválida; debe ser local y absoluta.")
        return path if explicit else path / ".ollama" / "models"
    return (home or Path.home()) / ".ollama" / "models"


def diagnose_windows(
    *,
    os_name: str | None = None,
    status_reader: Callable[..., Any] = read_status,
    executable_exists: Callable[[str], bool] | None = None,
    disk_free_bytes: int | None = None,
) -> dict[str, Any]:
    """Observational host report. Never accesses /proc, systemd or the cloud."""
    current = os_name or platform.system()
    if current != "Windows":
        raise RuntimeError("El diagnóstico de Windows requiere Windows.")
    snapshot = status_reader(os_name=current)
    checker = executable_exists or (lambda c: shutil.which(c) is not None)
    if disk_free_bytes is None:
        try:
            disk_free_bytes = shutil.disk_usage(Path.home()).free
        except OSError:
            disk_free_bytes = None
    return {
        "product": "MJON AI OS",
        "platform": current,
        "release": snapshot.release,
        "architecture": snapshot.architecture,
        "memory_total_bytes": snapshot.memory_total_bytes,
        "disk_free_bytes": disk_free_bytes,
        "ollama": ("installed_unverified" if checker("ollama") else "not_installed"),
        "model_tested": False,
        "remote_provider_auto_enabled": False,
        "linux_desktop_services": "not_applicable",
    }


def local_chat(
    prompt: str,
    *,
    ram_bytes: int | None,
    model: str | None = None,
    client_factory: Callable[..., Any] = OllamaClient,
) -> str:
    """Explicit local Ollama request with fail-closed host-memory awareness."""
    if not isinstance(ram_bytes, int) or ram_bytes <= 0:
        raise RuntimeError("No se pudo verificar la RAM; se bloqueó la carga del modelo.")
    return client_factory(ram_bytes=ram_bytes).ask(prompt, model=model)
