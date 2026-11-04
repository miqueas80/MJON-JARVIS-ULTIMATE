"""API bridge for the approved MJON Windows control surface.

No UI markup/styles or Windows changes are introduced here. The existing
Dodaios desktop HTTP server hosts this router *only* when the Windows edition
is explicitly enabled; SurfaceSecurity remains the outer security boundary.

Read-only routes are observational. POST operations require a same-origin
local browser request; command-line/agent Bearer calls are intentionally
rejected for interactive-only actions.
"""
from __future__ import annotations

import asyncio
from dataclasses import asdict
import os
from pathlib import Path
import platform
import shutil
from urllib.parse import urlsplit

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from mjon_jarvis.system_status import read_status
from mjon_os.local_inference import InferenceUnavailable, OllamaClient
from .backend import (
    diagnose_windows, inspect_windows_catalog, local_chat,
    model_directory, storage_budget, windows_settings,
)

router = APIRouter(prefix="/api/mjon/windows", tags=["mjon-windows"])


def _require_local_browser(request: Request) -> None:
    """Refuse cross-origin requests and non-browser Control-API clients.

    Host and Origin must match, including the port, and be loopback addresses.
    The desktop server's existing SurfaceSecurity independently validates
    Origin/Host and optional browser login before any route is reached.
    """
    origin = request.headers.get("origin", "")
    host = request.headers.get("host", "")
    authorization = request.headers.get("authorization", "")
    try:
        parsed = urlsplit(origin)
        if (
            authorization.strip()
            or parsed.scheme not in {"http", "https"}
            or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}
            or parsed.netloc.lower() != host.lower()
            or parsed.username is not None
            or parsed.password is not None
            or parsed.path
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("No es una petición local de la interfaz.")
    except ValueError as exc:
        raise HTTPException(
            status_code=403,
            detail="Control disponible únicamente desde la interfaz local de MJON.",
        ) from exc


class LocalModelTestBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    prompt: str = Field(min_length=1, max_length=1024)
    model: str = Field(min_length=1, max_length=200)


class SettingsOpenBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    section: str = Field(min_length=1, max_length=40)


class StorageCheckBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    model_bytes: int = Field(ge=0, le=1_000_000_000_000)


def get_local_models() -> tuple[str, ...]:
    """Ollama loopback inventory; weights are NOT claimed loadable here."""
    return OllamaClient().models()


def available_storage_bytes() -> int:
    """Free space on the volume selected for model storage, read-only.

    Query the nearest existing ancestor, so a first-run models directory
    need not be created to check storage. Never trust a free-space number
    supplied by the frontend.
    """
    if platform.system() != "Windows":
        raise RuntimeError("El almacenamiento MJON Windows solo se comprueba en Windows.")
    path = Path(str(model_directory()))
    while not path.exists() and path.parent != path:
        path = path.parent
    if not path.exists():
        raise RuntimeError("No se encontró un volumen disponible.")
    return shutil.disk_usage(path).free


@router.get("/overview")
async def overview() -> dict:
    """Observations only: an executable is not a verified AI model."""
    try:
        diagnostics = await asyncio.to_thread(diagnose_windows)
        modules = await asyncio.to_thread(inspect_windows_catalog)
    except (RuntimeError, OSError, ValueError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {
        "product": "MJON AI OS", "platform": "Windows",
        "diagnostics": diagnostics, "modules": modules,
        "automatic_installation": False,
        "automatic_cloud_fallback": False,
    }


@router.get("/models")
async def models() -> dict:
    """Reachable server ≠ an inference model has passed a real generation."""
    try:
        names = await asyncio.to_thread(get_local_models)
    except (RuntimeError, ValueError, OSError) as exc:
        return {
            "ready": False, "server_reachable": False,
            "generation_tested": False, "models": [], "reason": str(exc),
        }
    return {
        "ready": bool(names), "server_reachable": True,
        "generation_tested": False, "models": list(names),
        "reason": ("Modelos descargados; la inferencia aún no se probó."
                   if names else "Ollama responde, pero no tiene modelos descargados."),
    }


@router.post("/models/test")
async def test_model(body: LocalModelTestBody, request: Request) -> dict:
    """User-triggered, local-only generation; NEVER hidden cloud fallback."""
    _require_local_browser(request)
    try:
        status = await asyncio.to_thread(read_status)
        result = await asyncio.to_thread(
            local_chat, body.prompt, model=body.model,
            ram_bytes=status.memory_total_bytes,
        )
    except (RuntimeError, InferenceUnavailable, ValueError, OSError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {
        "ok": True, "provider": "ollama_local", "model": body.model,
        "answer": result, "generation_tested": True,
    }


@router.post("/settings/open")
async def open_settings(body: SettingsOpenBody, request: Request) -> dict:
    """Only the user-facing Microsoft Settings allowlist, never a shell."""
    _require_local_browser(request)
    try:
        opened = await asyncio.to_thread(windows_settings, body.section)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except (RuntimeError, OSError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"opened": opened}


@router.post("/storage/check")
async def check_storage(body: StorageCheckBody, request: Request) -> dict:
    """Actual free space and a dry-run budget; no download occurs."""
    _require_local_browser(request)
    try:
        free = await asyncio.to_thread(available_storage_bytes)
        result = storage_budget(model_bytes=body.model_bytes, free_bytes=free)
    except (RuntimeError, ValueError, OSError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {**asdict(result), "started_download": False}
