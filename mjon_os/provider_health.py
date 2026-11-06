"""Truthful offline Ollama diagnostics and bounded opt-in model warmup.

A listed binary, an HTTP listener, or downloaded weights do not prove that a
provider can answer. Only an actual generation can produce ready.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
from pathlib import Path
import sys
import time
from typing import Any, Callable

from .local_inference import InferenceUnavailable, OllamaClient, is_cloud_model
from .ollama_policy import eligible_models


@dataclass(frozen=True)
class ProviderStatus:
    state: str
    model: str | None = None
    detail: str = ""

    @property
    def ready(self) -> bool:
        return self.state == "ready"

    def to_dict(self) -> dict[str, Any]:
        return {**asdict(self), "ready": self.ready}


def _choose_model(client: OllamaClient, requested: str | None) -> str:
    if requested is not None and is_cloud_model(requested):
        raise InferenceUnavailable("Ollama cloud models cannot be preloaded in offline mode.")
    available = tuple((name, size) for name, size in client._model_inventory()
                      if not is_cloud_model(name))
    if not available:
        raise InferenceUnavailable("Ollama responde, pero no tiene modelos descargados.")
    models = dict(available)
    if requested is not None and requested not in models:
        raise InferenceUnavailable("El modelo configurado no está descargado en Ollama.")
    budget = int(client._ram_bytes * 0.4) if client._ram_bytes else None
    eligible = eligible_models(available, client._ram_bytes)
    if requested is not None:
        if requested not in eligible:
            if budget is not None and models[requested] is None:
                raise InferenceUnavailable("The model size is unknown; refusing to preload on limited RAM.")
            raise InferenceUnavailable("El modelo supera el límite conservador de RAM.")
        return requested
    if not eligible:
        raise InferenceUnavailable("Ningún modelo descargado cumple el límite de RAM.")
    return min(eligible, key=lambda name: (models[name] is None, models[name] or 0))


def _loaded_models(client: OllamaClient) -> set[str]:
    payload = client._request("/api/ps", timeout=4)
    models = payload.get("models")
    if not isinstance(models, list):
        raise InferenceUnavailable("Ollama no devolvió una lista válida de modelos cargados.")
    return {m.get("name") for m in models if isinstance(m, dict)
            and isinstance(m.get("name"), str)}


def diagnose(client: OllamaClient, *, model: str | None = None,
             verify_generation: bool = False) -> ProviderStatus:
    """Read-only check unless verify_generation explicitly requests a real call."""
    try:
        chosen = _choose_model(client, model)
        loaded = chosen in _loaded_models(client)
        if verify_generation:
            reply = client.ask("Respondé brevemente con OK.", model=chosen)
            if not isinstance(reply, str) or not reply.strip():
                raise InferenceUnavailable("El proveedor no devolvió texto válido.")
            return ProviderStatus("ready", chosen, "Generación local real comprobada.")
        if loaded:
            return ProviderStatus("loaded_unverified", chosen,
                                  "Modelo cargado en RAM; generación no verificada.")
        return ProviderStatus("downloaded_unverified", chosen,
                              "Pesos descargados; modelo no cargado ni probado.")
    except InferenceUnavailable as exc:
        return ProviderStatus("unavailable", model, str(exc))


def preload(client: OllamaClient, *, model: str | None = None,
            keep_alive: str = "5m") -> ProviderStatus:
    """Explicitly warm a locally downloaded model; never pull or use the cloud."""
    if keep_alive not in {"1m", "5m", "10m"}:
        raise ValueError("La precarga solo permite 1m, 5m o 10m.")
    chosen = _choose_model(client, model)
    result = client._request("/api/generate", body={
        "model": chosen, "prompt": "", "stream": False,
        "keep_alive": keep_alive,
        "options": {"num_ctx": 2048, "num_thread": 4},
    }, timeout=90)
    if result.get("done") is not True:
        raise InferenceUnavailable("Ollama returned an incomplete preload response.")
    if chosen not in _loaded_models(client):
        raise InferenceUnavailable("Ollama aceptó la precarga pero no confirmó el modelo en RAM.")
    return ProviderStatus("loaded_unverified", chosen,
                          "Modelo precargado; realizá una generación para comprobar el proveedor.")


def preload_from_config(
    config_file: Path, *, client: OllamaClient | None = None,
    wait_attempts: int = 1, pause_s: float = 1.0,
    sleeper: Callable[[float], None] = time.sleep,
) -> ProviderStatus:
    """Opt-in startup waits a bounded time for an already-managed local server.

    This function never starts Ollama or downloads models. The optional OS
    unit orders a bundled daemon dependency; without a payload, readiness
    retries handle a separately managed system-level daemon.
    """
    if not config_file.exists():
        return ProviderStatus("disabled", detail="No hay configuración de precarga.")
    if config_file.is_symlink() or not config_file.is_file():
        raise ValueError("La configuración de precarga debe ser un archivo regular.")
    config = json.loads(config_file.read_text(encoding="utf-8"))
    if not isinstance(config, dict) or config.get("enabled") is not True:
        return ProviderStatus("disabled", detail="Precarga desactivada.")
    model = config.get("model")
    if not isinstance(model, str) or not model.strip() or len(model) > 200:
        raise ValueError("Configurá explícitamente un modelo local para la precarga.")
    keep_alive = config.get("keep_alive", "5m")
    if not isinstance(keep_alive, str):
        raise ValueError("keep_alive inválido.")
    if not isinstance(wait_attempts, int) or not 1 <= wait_attempts <= 10:
        raise ValueError("wait_attempts must be between 1 and 10.")
    if not isinstance(pause_s, (int, float)) or not 0 <= pause_s <= 3:
        raise ValueError("pause_s must be between 0 and 3 seconds.")
    local_client = client or OllamaClient()
    for attempt in range(wait_attempts):
        try:
            local_client.models()
            break
        except InferenceUnavailable:
            if attempt + 1 == wait_attempts:
                raise
            sleeper(float(pause_s))
    return preload(local_client, model=model.strip(), keep_alive=keep_alive)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Ollama local: estado, verificación y precarga")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--verify", action="store_true", help="Ejecutar consulta real")
    mode.add_argument("--preload", action="store_true", help="Cargar modelo sin generar")
    mode.add_argument("--startup-config", type=Path, help="Precarga opcional desde JSON")
    parser.add_argument("--model", help="Modelo local descargado")
    parser.add_argument("--keep-alive", default="5m", choices=["1m", "5m", "10m"])
    args = parser.parse_args(argv)
    try:
        if args.startup_config:
            status = preload_from_config(args.startup_config, wait_attempts=5, pause_s=2)
        elif args.preload:
            status = preload(OllamaClient(), model=args.model, keep_alive=args.keep_alive)
        else:
            status = diagnose(OllamaClient(), model=args.model,
                              verify_generation=args.verify)
        print(json.dumps(status.to_dict(), ensure_ascii=False))
        return 0 if status.state in {"disabled", "ready", "loaded_unverified", "downloaded_unverified"} else 2
    except (ValueError, InferenceUnavailable, OSError, json.JSONDecodeError) as exc:
        print(json.dumps(ProviderStatus("unavailable", detail=str(exc)).to_dict(),
                         ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
