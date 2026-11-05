"""Probe the actual configured Ollama brain in a separate native OS process.

This does not prove the desktop UI, speech, or the full agent orchestration.
It verifies the production brain adapter and configuration used for chat.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path
import subprocess
import sys

from .provider_health import ProviderStatus


def verify_jarvis_ollama(config_file: Path) -> ProviderStatus:
    """Isolate module-level config caches from the running GTK Control Center."""
    if not config_file.is_absolute() or not config_file.is_file() or config_file.is_symlink():
        raise ValueError("An absolute regular JARVIS configuration is required.")
    result = subprocess.run(
        [sys.executable, "-m", "mjon_os.jarvis_probe", "--config", str(config_file)],
        env={**os.environ, "MJON_NATIVE_OS": "1", "JARVIS_CONFIG": str(config_file),
             "MJON_AI_OS_CONFIG_ROOT": str(config_file.parent)},
        capture_output=True, text=True, timeout=110, check=False,
    )
    try:
        payload = json.loads(result.stdout)
        return ProviderStatus(payload["state"], payload.get("model"), payload.get("detail", ""))
    except (ValueError, KeyError, TypeError):
        # SDK tracebacks may carry credentials. Keep them out of the GUI.
        return ProviderStatus("unavailable", detail="JARVIS provider probe failed; exit "
                              + str(result.returncode))


async def probe_config(config_file: Path) -> ProviderStatus:
    # Set before the first core import: config locations are module globals.
    os.environ["MJON_NATIVE_OS"] = "1"
    os.environ["JARVIS_CONFIG"] = str(config_file)
    os.environ["MJON_AI_OS_CONFIG_ROOT"] = str(config_file.parent)
    from dodaios.core import config
    from dodaios.core.protocols import BrainMessage, BrainRequest
    from dodaios.plugins.brain.ollama import OllamaBrain
    settings = config.load_config(config_file=config_file)
    provider = settings.brain.providers.get("ollama")
    model = (provider.model if provider else None) or ""
    brain = OllamaBrain(model=model)
    try:
        chosen = await brain._resolve_model()
        request = BrainRequest(messages=(BrainMessage(role="user", content="Reply briefly with OK."),),
                               max_tokens=32, temperature=1.0, stream=True)
        text = []
        async with asyncio.timeout(90):
            async for delta in brain.complete(request):
                if delta.finish_reason in {"error", "failed"}:
                    raise RuntimeError("Provider stream reported failure.")
                if delta.content:
                    text.append(delta.content)
        if not "".join(text).strip():
            raise RuntimeError("The configured JARVIS brain produced no text.")
        return ProviderStatus("ready", chosen,
                              "Actual JARVIS Ollama brain completed a local text response.")
    except Exception as exc:
        return ProviderStatus("unavailable", model or None, str(exc)[:300])
    finally:
        if brain._client is not None:
            await brain._client.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path)
    args = parser.parse_args(argv)
    if not args.config.is_absolute() or not args.config.is_file():
        parser.error("An absolute configuration file is required")
    status = asyncio.run(probe_config(args.config))
    print(json.dumps(status.to_dict()))
    return 0 if status.ready else 2


if __name__ == "__main__":
    raise SystemExit(main())
