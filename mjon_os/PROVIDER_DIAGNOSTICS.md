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


## Por qué JARVIS fallaba aunque el Centro de mando detectara Ollama

La plantilla original de Dodaios apuntaba a Gemini como `brain.primary`,
`brain.fallback`, `brain.deep_brain` y `brain.routing_provider`. El
Centro de mando tenía un cliente Ollama independiente: un test local exitoso
NO configuraba automáticamente el cerebro de JARVIS.

Los perfiles nuevos de MJON AI OS seleccionan ahora `ollama` como proveedor
de cerebro y dejan vacío `routing_model` para descubrir un modelo local
existente. Si no hay Ollama, el servidor no está iniciado o no hay pesos,
el sistema debe informar que aún no puede generar texto. La ISO sigue sin
incluir el ejecutable ni los pesos de Ollama.

### Recuperar un perfil de una ISO anterior

1. Instalá Ollama desde su fuente oficial mediante una acción consciente del
   usuario y con Internet, y obtené un modelo local compatible con tu RAM.
   Por ejemplo, con 8 GiB y espacio persistente: `ollama pull qwen3:1.7b`
   (aproximadamente 1,4 GB de descarga). No uses la etiqueta `:latest`
   sin revisar su tamaño.
2. Confirmá que el servidor y el modelo responden:
   `/opt/mjon-ai-os/venv/bin/python -m mjon_os.provider_health --verify`
3. En una nueva ISO con este cambio, abrí Centro de mando > IA local y pulsá
   **Usar Ollama en JARVIS (reinicia el asistente)**. Este botón solo cambia
   los valores iniciales de Gemini **después de una generación local real**.
   Guarda una copia privada `dodaios.toml.bak` y reinicia el servicio de
   usuario sin privilegios de administrador.
4. Si la GUI no funciona, hacé la migración opcional desde Konsole:
   `/opt/mjon-ai-os/venv/bin/python -m mjon_os.first_boot --activate-ollama --config "$HOME/.config/mjon-ai-os/dodaios.toml"`
   y luego `systemctl --user restart mjon-jarvis.service`. Solo modifica
   configuraciones con los cinco valores Gemini predeterminados. Si ya
   elegiste otro proveedor, se niega a reemplazar tus preferencias.

Una ISO antigua no adquiere estas correcciones por estar disponible el
código fuente en GitHub: hace falta iniciar una imagen construida con el
commit corregido. En USB Live sin persistencia, los modelos descargados y
la configuración de usuario pueden perderse tras el reinicio.

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
