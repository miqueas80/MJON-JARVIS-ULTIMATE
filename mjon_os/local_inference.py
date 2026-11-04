"""Explicit loopback-only Ollama inference adapter for the MJON AI fabric.

It does not install/download a model, start a server or fall back to cloud
providers. The user must intentionally invoke it. All failures are explicit.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from .doctor import parse_memtotal
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from typing import Callable, Any


class InferenceUnavailable(RuntimeError):
    """The local inference service or requested model is not available."""


class OllamaClient:
    DEFAULT_ENDPOINT = "http://127.0.0.1:11434"

    def __init__(self, endpoint: str = DEFAULT_ENDPOINT, *, opener: Callable[..., Any] | None = None,
                 ram_bytes: int | None = None):
        # Prevent accidental credentials or private prompts leaking to remote
        # endpoints or DNS names that merely LOOK local.
        if endpoint != self.DEFAULT_ENDPOINT:
            raise ValueError("MJON offline adapter only permits literal IPv4 loopback Ollama")
        self.endpoint = endpoint
        self._opener = opener or urlopen
        if ram_bytes is None:
            try:
                ram_bytes = parse_memtotal(Path("/proc/meminfo").read_text(encoding="ascii"))
            except OSError:
                ram_bytes = None
        self._ram_bytes = ram_bytes

    def _request(self, route: str, *, body: dict | None = None, timeout: int = 8) -> dict:
        url = self.endpoint + route
        if body is None:
            request = Request(url, method="GET")
        else:
            payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
            request = Request(
                url, data=payload, method="POST",
                headers={"Content-Type": "application/json"},
            )
        try:
            with self._opener(request, timeout=timeout) as response:
                raw = response.read(2 * 1024 * 1024 + 1)
        except (HTTPError, URLError, OSError, TimeoutError) as exc:
            raise InferenceUnavailable("Ollama local no responde; revisá el servicio.") from exc
        if len(raw) > 2 * 1024 * 1024:
            raise InferenceUnavailable("Respuesta local demasiado grande.")
        try:
            result = json.loads(raw)
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise InferenceUnavailable("Ollama devolvió datos que no son JSON válido.") from exc
        if not isinstance(result, dict):
            raise InferenceUnavailable("Ollama devolvió un formato inesperado.")
        return result

    def _model_inventory(self) -> tuple[tuple[str, int | None], ...]:
        payload = self._request("/api/tags", timeout=4)
        models = payload.get("models", [])
        if not isinstance(models, list):
            raise InferenceUnavailable("Ollama no devolvió un catálogo de modelos válido.")
        names: list[tuple[str, int | None]] = []
        for item in models:
            if isinstance(item, dict) and isinstance(item.get("name"), str):
                name = item["name"].strip()
                size = item.get("size")
                if not isinstance(size, int) or isinstance(size, bool) or size < 0:
                    size = None
                if name and len(name) <= 200 and name not in [item[0] for item in names]:
                    names.append((name, size))
        return tuple(names)

    def models(self) -> tuple[str, ...]:
        return tuple(name for name, _ in self._model_inventory())

    def ask(self, prompt: str, *, model: str | None = None) -> str:
        if not isinstance(prompt, str) or not prompt.strip() or len(prompt) > 8192:
            raise ValueError("Escribí una consulta de 1 a 8192 caracteres.")
        available = self._model_inventory()
        if not available:
            raise InferenceUnavailable("Ollama está accesible, pero no tiene ningún modelo local descargado.")
        sizes = {name: size for name, size in available}
        if model is not None and model not in sizes:
            raise InferenceUnavailable("El modelo solicitado no está descargado en Ollama.")
        # A GGUF/disk-size heuristic: 40% physical RAM budget leaves memory
        # for KDE, JARVIS, KV cache and OS overhead. It is not an OOM guarantee.
        max_size = int(self._ram_bytes * 0.40) if self._ram_bytes else None
        candidates = [name for name, size in available
                      if max_size is None or size is None or size <= max_size]
        if model is not None:
            if model not in candidates:
                raise InferenceUnavailable("Modelo rechazado por política conservadora de memoria RAM.")
            chosen = model
        else:
            if not candidates:
                raise InferenceUnavailable("Ningún modelo local cumple la política de memoria RAM.")
            chosen = min(candidates, key=lambda name: sizes[name] if sizes[name] is not None else 2**64)
        response = self._request(
            "/api/chat",
            body={
                "model": chosen,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
                "options": {"num_predict": 256},
            },
            timeout=90,
        )
        message = response.get("message")
        text = message.get("content") if isinstance(message, dict) else None
        if not isinstance(text, str) or not text.strip():
            raise InferenceUnavailable("El modelo local no generó una respuesta válida.")
        return text.strip()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Probar un modelo local Ollama sin servicios externos")
    parser.add_argument("prompt", nargs="?", help="Consulta para Ollama local")
    parser.add_argument("--model", help="Nombre de modelo previamente descargado")
    parser.add_argument("--list-models", action="store_true")
    args = parser.parse_args(argv)
    client = OllamaClient()
    try:
        if args.list_models or not args.prompt:
            print("\n".join(client.models()) or "Ningún modelo local descargado")
        else:
            print(client.ask(args.prompt, model=args.model))
    except (InferenceUnavailable, ValueError) as exc:
        parser.exit(2, str(exc) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
