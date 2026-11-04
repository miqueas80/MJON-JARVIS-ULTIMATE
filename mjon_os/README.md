# MJON AI OS — Unified Native Distribution (Development)

**One product, one codebase.** This repository contains the operating-system image definition and the Dodaios-derived intelligence engine. There is no separate Jarvis app repository and no second runtime.

## Architecture

- **Base OS:** Debian 13 (trixie), amd64, KDE Plasma via `live-task-kde`.
- **Built-in agent:** the **fork's own** `dodaios` wheel, including `mjon_jarvis` and `mjon_os`.
- **Desktop start:** `/etc/xdg/autostart/mjon-ai-os.desktop` starts the `mjon-jarvis.service` **user** service.
- **Launch:** `/usr/local/bin/mjon-session` runs `mjon_os.first_boot` and the existing `dodaios.ui.web.launcher`.
- **Private state:** `$XDG_CONFIG_HOME/mjon-ai-os/dodaios.toml` and `$XDG_DATA_HOME/mjon-ai-os` (defaults under `~/.config` and `~/.local/share`).
- **Defaults:** Jarvis wake phrase, Spanish language preference, upstream self-autostart disabled to avoid duplicate instances.
- **Permissions:** logged-in user, no root for AI, `NoNewPrivileges=yes`, upstream approvals retained.
- **Desktop runtime:** Debian GTK 3 + WebKit2 4.1 system bindings and the fork wheel's `[desktop]` extras; the venv explicitly reads system GI bindings.
- **Live diagnostics:** `/usr/local/bin/mjon-doctor --json` checks graphical session, physical memory and the user service without elevating privileges.

### Why we do not fork the Linux kernel

A Linux distribution is a complete OS; native session services and desktop protocols provide OS integration without replacing a proven kernel. The agent is preinstalled in the ISO and starts as part of the OS experience.

## Centro de mando gráfico de MJON AI OS

La distribución incorpora un **Centro de mando MJON unificado y liviano** (GTK), accesible desde el icono del escritorio y el menú de aplicaciones. La pestaña Sistema abre la **configuración real de KDE**; la pestaña Módulos IA detecta opcionales instalados sin importarlos ni iniciarlos; la pestaña IA local puede consultar un Ollama existente exclusivamente por loopback; y la pestaña Seguridad explica los límites de autorización. Si el motor nativo no está disponible, el lanzador conserva un acceso de recuperación a KDE System Settings.

**No se incluyen pesos de modelos locales ni servidores de inferencia pesados en el perfil básico.** Se informa claramente cuando Ollama no está instalado, no responde o no tiene ningún modelo. La política de hardware favorece motores CPU ligeros y evita activar frameworks pesados o proveedores remotos sin consentimiento. La bandeja del panel mantiene los controles de Wi-Fi, volumen y Bluetooth.

Los paquetes se declaran expresamente porque `live-build` desactiva las recomendaciones APT: `systemsettings`, `plasma-nm`, `wpasupplicant`, `plasma-pa`, `pipewire-audio`, `bluedevil`, `bluez`, `powerdevil`, `kscreen`, `kinfocenter`, `polkit-kde-agent-1`, `plasma-systemmonitor` y `plasma-discover`. Esto evita que aparezcan categorías vacías o que el usuario tenga que recurrir a la terminal para las tareas habituales.

La construcción comprueba los binarios y las entradas de menú. El arranque virtual también exige `MJON_VM_PROOF CONTROL_CENTER_READY`; **la operación con hardware Realtek y demás dispositivos todavía debe probarse físicamente**.

**En modo Live sin persistencia, las aplicaciones que se instalen con Discover y los ajustes de usuario pueden perderse al reiniciar.** En ningún caso se instala automáticamente sobre el disco de Windows.

## Plano de control de módulos (implementación inicial)

- `mjon_os.ai_fabric`: catálogo de capacidades y política conservadora de RAM/CPU/GPU, sin auto-instalar ni auto-ejecutar agentes.
- `mjon_os.local_inference`: prueba real de Ollama vía `http://127.0.0.1:11434`, con detección de pesos antes de enviar una pregunta. No habilita nube automáticamente.
- `mjon_os.ai_center`: Centro de mando GTK unificado y diagnóstico sin GUI `python3 -m mjon_os.ai_center --status-json`.
- `systemd-zram-generator`: swap comprimida de tamaño `min(ram/4, 2048 MiB)`, no RAM física adicional; utilidad para entornos de 8 GiB.
- `AppArmor` y `Bubblewrap` en la base. **No es evidencia de aislamiento de agentes** hasta que se creen y prueben perfiles concretos.
- Free LLM API, OpenClaw, OpenCode, vLLM, SGLang, frameworks de entrenamiento, visión y voz avanzada siguen como módulos optativos. El catálogo no demuestra que estén instalados o funcionales.
- Integración completa del plano de control dentro de cada conversación de JARVIS, instalación gráfica segura de componentes, persistencia USB y pruebas físicas offline con un modelo siguen pendientes.

## Validated locally

```shell
python3 -m unittest discover -s mjon_os/tests -p 'test_*.py' -v
```

The preparer is side-effect-free for host system settings. It writes only a **new** build workspace; it never overwrites a preexisting directory. It checks the wheel's metadata and that the engine includes MJON's integration modules. A hash in `mjon-build.json` records the wheel used.

## Build preparation (developer/Linux host only)

1. Review the upstream source and the fork's changes; keep `LICENSE` and `NOTICE`.
2. Build the real frontend **before** packaging the wheel. An image without the desktop bundle is rejected:
   ```shell
   cd dodaios/ui/web/frontend
   npm ci
   npm run build
   cd ../../../..
   ```
3. Build the repository's own wheel using its existing `pyproject.toml`/setuptools setup:
   ```shell
   python3 -m pip install --upgrade 'setuptools>=84.1.0' wheel build
   python3 -m build --wheel --no-isolation -o /tmp/mjon-wheels
   ```
4. Prepare the Debian live-build workspace from **that** wheel:
   ```shell
   python3 -m mjon_os.image_builder --wheel /tmp/mjon-wheels/dodaios-4.1.2-py3-none-any.whl --workdir /tmp/mjon-live
   ```
5. On a controlled Debian 13 build host with `live-build` installed, explicitly run:
   ```shell
   cd /tmp/mjon-live
   sudo lb config
   sudo lb build
   ```

The final commands can download many packages and consume substantial CPU, RAM, disk and network. They are **not** executed on the user's Windows machine. The preparer does not create an ISO by itself.

The optional [experimental USB ISO workflow](../.github/workflows/mjon-live-iso.yml) performs that build on a disposable CI runner and checks the ISO boot records. **An image still must pass VM boot and desktop tests before being offered for USB use.** The [hardware runbook](USB_LIVE_TEST.md) records the eventual safe USB procedure.

## Release blockers — NOT a finished OS

- Build an actual `.iso` artifact successfully and validate boot on UEFI and BIOS VMs.
- Validate KDE login, agent service startup, and first-run configuration in the live image.
- Verify the upstream frontend assets are bundled in the wheel and the desktop UI is usable.
- Test STT, TTS, wake word and GUI automation under KDE Wayland; assess permissions and portal behavior.
- Verify offline command execution and disclose that local LLM model weights are not yet bundled.
- Measure idle/peak RAM on 8 GB hardware, including recovery from model and network failures.
- Exercise destructive-action approvals and ensure cancellation, logs, uninstall and recovery.
- Verify packaging provenance and upstream notices; code derived from Dodaios remains attributed.
- Produce a signed or checksummed release ISO and clear rollback/testing instructions.

**Status:** native OS build foundation, not installable product release.
