"""Read-only and explicit opt-in command line for the Windows migration.

Usage:
    python -m mjon_windows --catalog
    python -m mjon_windows --doctor
    python -m mjon_windows --models
    python -m mjon_windows --ask "Hola" --model "example:tag"
    python -m mjon_windows --settings wifi

No startup side effects; Windows-specific operations are denied on Linux.
"""
from __future__ import annotations

import argparse
import json
import sys

from mjon_jarvis.system_status import read_status
from mjon_os.local_inference import InferenceUnavailable, OllamaClient
from .backend import (
    diagnose_windows, inspect_windows_catalog, local_chat,
    model_directory, windows_settings,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="MJON AI OS · Diagnóstico y control Windows sin instalación automática"
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--catalog", action="store_true", help="Motores opcionales detectados")
    mode.add_argument("--doctor", action="store_true", help="Diagnóstico del equipo Windows")
    mode.add_argument("--models", action="store_true", help="Modelos en Ollama local")
    mode.add_argument("--ask", metavar="PROMPT", help="Consultar explícitamente al modelo local")
    mode.add_argument("--settings", metavar="SECTION", help="Abrir una sección autorizada de Windows")
    parser.add_argument("--model", help="Nombre de modelo Ollama instalado")
    args = parser.parse_args(argv)
    try:
        if args.catalog:
            result = {
                "product": "MJON AI OS", "platform_target": "Windows",
                "models_ready": False, "installed_is_not_ready": True,
                "automatic_installation": False, "cloud_fallback": False,
                "modules": inspect_windows_catalog(),
            }
            print(json.dumps(result, ensure_ascii=False, indent=2))
        elif args.doctor:
            report = diagnose_windows()
            report["model_directory"] = str(model_directory())
            print(json.dumps(report, ensure_ascii=False, indent=2))
        elif args.models:
            print("\n".join(OllamaClient().models()) or "No hay modelos locales instalados.")
        elif args.ask is not None:
            ram = read_status().memory_total_bytes
            print(local_chat(args.ask, model=args.model, ram_bytes=ram))
        else:
            target = windows_settings(args.settings)
            print("Se abrió Configuración de Windows:", target)
    except (RuntimeError, ValueError, InferenceUnavailable, OSError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
