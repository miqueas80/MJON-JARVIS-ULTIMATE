"""Explicit loopback-only Ollama inference adapter for the MJON AI fabric.

It does not install/download a model, start a server or fall back to cloud
providers. The user must intentionally invoke it. All failures are explicit.
"""
from __future__ import annotations

import argparse
import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from typing import Callable, Any


class InferenceUnavailable(RuntimeError):
    """The local inference service or requested model is not available."""


class OllamaClient:
    DEFAULT_ENDPOINT = "http://127.0.0.1:11434"

    def __init__(self, endpoint: str = DEFAULT_ENDPOINT, *, opener: Callable[..., Any] | None = None):
        # Prevent accidental credentials or private prompts leaking to remote
        # endpoints or DNS names that merely LOOK local.
        if endpoint != self.DEFAULT_ENDPOINT:
            raise ValueError("MJON offline adapter only permits literal IPv4 loopback Ollama")
        self.endpoint = endpoint
        self._opener = opener or urlopen

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

    def models(self) -> tuple[str, ...]:
        payload = self._request("/api/tags", timeout=4)
        models = payload.get("models", [])
        if not isinstance(models, list):
            raise InferenceUnavailable("Ollama no devolvió un catálogo de modelos válido.")
        names = []
        for item in models:
            if isinstance(item, dict) and isinstance(item.get("name"), str):
                name = item["name"].strip()
                if name and len(name) <= 200 and name not in names:
                    names.append(name)
        return tuple(names)

    def ask(self, prompt: str, *, model: str | None = None) -> str:
        if not isinstance(prompt, str) or not prompt.strip() or len(prompt) > 8192:
            raise ValueError("Escribí una consulta de 1 a 8192 caracteres.")
        available = self.models()
        if not available:
            raise InferenceUnavailable("Ollama está accesible, pero no tiene ningún modelo local descargado.")
        chosen = model or available[0]
        if chosen not in available:
            raise InferenceUnavailable("El modelo solicitado no está descargado en Ollama.")
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
