# MJON AI OS: Ollama provider diagnostics and model preload

The Debian 13 KDE experimental image DOES NOT bundle the Ollama binary or any
model weights. Installing them and enabling model startup remain explicit
user actions. The new tools neither pull models nor fall back to the cloud.

## What each provider state means

* unavailable: server offline, missing model, RAM guard, invalid response or
  actual provider failure.
* downloaded_unverified: local model weights exist but generation was not tested.
* loaded_unverified: Ollama reports the model in RAM, but generation is untested.
* ready: an actual nonempty local response has succeeded.
* disabled: no opt-in startup preload is configured.

The old catalog used the presence of a binary to show a reassuring green
indicator. A detected executable is not a verified provider.

## Test in the desktop interface

Open MJON AI OS - Centro de mando - IA local. Use the new button to verify
the provider with a real response or the other button to warm a local model.

Terminal equivalents, running as the graphical user:

    /opt/mjon-ai-os/venv/bin/python -m mjon_os.provider_health
    /opt/mjon-ai-os/venv/bin/python -m mjon_os.provider_health --verify
    /opt/mjon-ai-os/venv/bin/python -m mjon_os.provider_health --preload --model MY_MODEL

The first checks model inventory and process residency without generating.
The second performs a short real local generation. The third preloads the
already-downloaded model with a bounded five-minute keep-alive, then checks
the Ollama /api/ps response. Only 127.0.0.1:11434 is permitted.

## Optional startup preload (disabled by default)

First verify that Ollama is installed, running, and the exact model tag
appears in the output of the ollama list command. Create a configuration
file at ~/.config/mjon-ai-os/ollama-preload.json:

    {
      "enabled": true,
      "model": "MY_ALREADY_DOWNLOADED_MODEL_TAG",
      "keep_alive": "5m"
    }

Then explicitly enable the optional user service:

    systemctl --user daemon-reload
    systemctl --user enable --now mjon-ollama-preload.service
    systemctl --user status mjon-ollama-preload.service --no-pager

Disable it any time:

    systemctl --user disable --now mjon-ollama-preload.service

This service does not install Ollama, download a model, elevate privileges
or enable cloud providers. It requires the local Ollama service to be ready
before it attempts warmup. Live USB without persistence loses user changes
and downloaded models on reboot.

## Investigating the Doraimon green-then-error report

A green executable indicator was insufficient. To diagnose a specific
Doraimon provider error conclusively, collect the actual configured endpoint
and model tag, a redacted provider error, and the result of an end-to-end
generation. Do not assume Doraimon uses Ollama or automatically change its
provider configuration: the exact Doraimon instance has not been identified
in this repository yet.

The branch changes are not an ISO release. Boot testing on real hardware,
the new user service, and end-to-end model generation are still required.

## Provider stream health: reason for a misleading green status

The inherited brain health checker previously stopped on its first streamed
event. That event might be metadata, whitespace, a partial answer, or be
followed by a provider failure. It now drains the complete bounded probe,
requires nonblank text, and reports late errors. The passive local-model
monitor no longer writes a successful generation verdict when it checked only
Ollama's server status. Pre-upgrade green records lacking generation evidence
are invalidated until a fresh check succeeds.

The installation must still be tested with a real model on the actual laptop;
passing unit tests does not prove an installed provider works.

## Important: 127.0.0.1 alone is not an air gap

Ollama supports cloud model tags even through a locally running daemon.
MJON's offline adapter refuses documented ':cloud' and '-cloud' model names
and never follows HTTP redirects. For a strict local-only Ollama installation,
the server administrator should also disable its cloud capabilities at the
daemon level, e.g. OLLAMA_NO_CLOUD=1 when starting the Ollama service, or use
the disable_ollama_cloud option in the daemon server.json file, and confirm
that its logs state cloud is disabled. Setting this variable only on the MJON
client would not disable cloud on an already-running Ollama server.

Ollama reference: https://docs.ollama.com/faq

An offline hardware test remains required, and users must not rely on the
loopback address alone as proof that all optional engines stay offline.
