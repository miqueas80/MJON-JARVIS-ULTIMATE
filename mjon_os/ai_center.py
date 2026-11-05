"""MJON AI OS — lightweight unified graphical system and AI Control Center.

GTK is loaded only when the user opens the center. All module information is
read-only and inspectable with --status-json. Optional frameworks are never
installed, started, or given root rights just by opening this window.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import subprocess
from threading import Thread

from .ai_fabric import HardwareProfile, inspect_modules
from .doctor import parse_memtotal
from .local_inference import InferenceUnavailable, OllamaClient
from .provider_health import diagnose as diagnose_ollama, preload as preload_ollama


_LABELS = {
    "inference": "Motores de IA",
    "agents": "Agentes",
    "programming": "Programación",
    "voice": "Voz",
    "vision": "Visión",
    "knowledge": "Memoria y conocimiento",
    "automation": "Automatización",
    "multimedia": "Multimedia",
    "training": "Entrenamiento",
    "optimization": "Optimización",
    "security": "Seguridad",
}


def _hardware() -> HardwareProfile:
    try:
        ram = parse_memtotal(Path("/proc/meminfo").read_text(encoding="ascii"))
    except OSError:
        ram = None
    ram_gib = round(ram / 1024**3, 2) if ram else 0.0

    # An NVIDIA vendor ID alone does not prove sufficient GPU memory. AMD
    # devices may be integrated, so be deliberately conservative here.
    discrete = False
    for device in Path("/sys/class/drm").glob("card*/device/vendor"):
        try:
            if device.read_text().strip().lower() == "0x10de":
                discrete = True
        except OSError:
            pass
    return HardwareProfile(ram_gib=ram_gib, discrete_gpu=discrete, network_available=False)


def get_catalog_json() -> str:
    hw = _hardware()
    return json.dumps({
        "product": "MJON AI OS",
        "hardware": {
            "ram_gib": hw.ram_gib,
            "discrete_gpu_detected": hw.discrete_gpu,
            "remote_service_auto_enabled": False,
        },
        "policy": {
            "automatic_installation": False,
            "automatic_start_of_optional_modules": False,
            "privileged_actions_without_approval": False,
            "remote_provider_consent_required": True,
            "installed_does_not_mean_model_ready": True,
        },
        "modules": inspect_modules(),
    }, indent=2, ensure_ascii=False)


def _launch_system_settings() -> None:
    target = "/usr/bin/systemsettings"
    if not Path(target).is_file():
        raise FileNotFoundError("KDE System Settings no está instalado")
    subprocess.Popen([target], close_fds=True, start_new_session=True)


def run_gui() -> int:
    try:
        import gi
        gi.require_version("Gtk", "3.0")
        from gi.repository import Gtk, GLib
    except (ImportError, ValueError) as exc:
        raise RuntimeError("GTK 3 es necesario para el Centro de mando") from exc

    window = Gtk.Window(title="MJON AI OS · Centro de mando")
    window.set_default_size(1000, 670)
    window.set_border_width(0)
    window.connect("destroy", Gtk.main_quit)

    provider = Gtk.CssProvider()
    provider.load_from_data(b"""
        .mjon-title {font-size: 21px; font-weight: bold;}
        .mjon-muted {opacity: 0.75;}
        .mjon-sidebar {padding: 12px; min-width: 160px;}
        .mjon-page {padding: 20px;}
        .mjon-row {padding: 7px; border-bottom: 1px solid alpha(@theme_fg_color,0.10);}
        .mjon-okay {color: #53ae85;}
        .mjon-warn {color: #ddaa55;}
    """)
    Gtk.StyleContext.add_provider_for_screen(
        window.get_screen(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
    )

    root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
    header = Gtk.HeaderBar()
    header.set_show_close_button(True)
    header.props.title = "MJON AI OS"
    header.props.subtitle = "Sistema · Motores · Agentes · Seguridad"
    window.set_titlebar(header)

    stack = Gtk.Stack()
    stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
    sidebar = Gtk.StackSidebar()
    sidebar.set_stack(stack)
    sidebar.get_style_context().add_class("mjon-sidebar")
    body = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
    body.pack_start(sidebar, False, False, 0)
    separator = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
    body.pack_start(separator, False, False, 0)
    body.pack_start(stack, True, True, 0)
    root.pack_start(body, True, True, 0)

    def page_box() -> object:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        box.get_style_context().add_class("mjon-page")
        return box

    def add_text(box, title: str, explanation: str) -> None:
        name = Gtk.Label(label=title, xalign=0)
        name.get_style_context().add_class("mjon-title")
        box.pack_start(name, False, False, 0)
        subtitle = Gtk.Label(label=explanation, xalign=0)
        subtitle.set_line_wrap(True)
        subtitle.get_style_context().add_class("mjon-muted")
        box.pack_start(subtitle, False, False, 0)

    # ── System page: launch the ACTUAL KDE settings app. ───────────────
    system = page_box()
    add_text(system, "Configuración del equipo",
             "Administrá Wi-Fi, Bluetooth, audio, pantalla, energía, controladores "
             "y otros ajustes del sistema con los paneles reales de KDE Plasma.")
    message = Gtk.Label(xalign=0)
    message.set_line_wrap(True)
    system.pack_start(message, False, False, 0)

    def open_settings(_button):
        try:
            _launch_system_settings()
        except OSError as exc:
            message.set_text("No se pudo abrir la configuración: " + str(exc))

    settings_button = Gtk.Button(label="Abrir configuración completa de KDE")
    settings_button.connect("clicked", open_settings)
    system.pack_start(settings_button, False, False, 0)

    hardware = _hardware()
    overview = Gtk.Label(
        label=f"RAM detectada: {hardware.ram_gib:.1f} GiB · GPU dedicada detectada: "
              + ("sí" if hardware.discrete_gpu else "no confirmada"),
        xalign=0,
    )
    system.pack_start(overview, False, False, 0)
    system.pack_start(Gtk.Label(
        label="En modo USB Live, sin persistencia los cambios pueden perderse al reiniciar.",
        xalign=0,
    ), False, False, 0)
    stack.add_titled(system, "system", "Sistema")

    # ── Module status: NO installation from the privileged Live session. ──
    modules_page = page_box()
    add_text(modules_page, "Motores y agentes",
             "Estado detectado en este equipo. La instalación es opcional, "
             "requiere aprobación y no se ejecuta al abrir el Centro de mando. "
             "Un binario encontrado no garantiza pesos de modelos descargados.")

    filter_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
    selection = Gtk.ComboBoxText()
    selection.append("all", "Todas las capacidades")
    for key, label in _LABELS.items():
        selection.append(key, label)
    selection.set_active_id("all")
    filter_box.pack_start(selection, True, True, 0)
    refresh = Gtk.Button(label="Actualizar estado")
    filter_box.pack_start(refresh, False, False, 0)
    modules_page.pack_start(filter_box, False, False, 0)

    module_list = Gtk.ListBox()
    module_list.set_selection_mode(Gtk.SelectionMode.NONE)
    scrolling = Gtk.ScrolledWindow()
    scrolling.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
    scrolling.add(module_list)
    modules_page.pack_start(scrolling, True, True, 0)

    def render_modules(*_args):
        for row in list(module_list.get_children()):
            module_list.remove(row)
        selected = selection.get_active_id() or "all"
        for module in inspect_modules():
            if selected != "all" and module["domain"] != selected:
                continue
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
            row.get_style_context().add_class("mjon-row")
            name = Gtk.Label(label=module["name"], xalign=0)
            name.set_hexpand(True)
            row.pack_start(name, True, True, 0)
            if module["status"] == "installed_unverified":
                state = "Detectado · modelo no verificado"
                style = "mjon-warn"
            elif module["status"] == "remote_opt_in":
                state = "Proveedor remoto · requiere autorización"
                style = "mjon-warn"
            else:
                state = "Opcional · no instalado"
                style = "mjon-warn"
            status = Gtk.Label(label=state, xalign=1)
            status.get_style_context().add_class(style)
            row.pack_start(status, False, False, 0)
            module_list.add(row)
        module_list.show_all()

    selection.connect("changed", render_modules)
    refresh.connect("clicked", render_modules)
    render_modules()
    stack.add_titled(modules_page, "modules", "Módulos IA")

    # ── Local inference is intentionally user-initiated and loopback-only. ─
    local_page = page_box()
    add_text(local_page, "Probar inteligencia local",
             "La consulta se envía únicamente a Ollama en 127.0.0.1. "
             "Si Ollama o sus modelos no están instalados, verás el problema "
             "en vez de recibir una respuesta inventada o activar la nube.")
    entry = Gtk.Entry()
    entry.set_placeholder_text("Escribí un mensaje para un modelo local descargado...")
    local_page.pack_start(entry, False, False, 0)
    ask_button = Gtk.Button(label="Consultar modelo local")
    local_page.pack_start(ask_button, False, False, 0)
    provider_controls = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
    diagnose_button = Gtk.Button(label="Verificar proveedor con una respuesta real")
    preload_button = Gtk.Button(label="Precargar modelo local (5 min)")
    provider_controls.pack_start(diagnose_button, True, True, 0)
    provider_controls.pack_start(preload_button, True, True, 0)
    local_page.pack_start(provider_controls, False, False, 0)
    note = Gtk.Label(
        label="Detectar un proveedor o cargar pesos no confirma la IA: "
              "solo una respuesta real habilita el estado operativo.",
        xalign=0,
    )
    note.set_line_wrap(True)
    local_page.pack_start(note, False, False, 0)
    answer = Gtk.TextView()
    answer.set_wrap_mode(Gtk.WrapMode.WORD)
    answer.set_editable(False)
    answer.set_cursor_visible(False)
    output_scroll = Gtk.ScrolledWindow()
    output_scroll.add(answer)
    local_page.pack_start(output_scroll, True, True, 0)

    def set_answer(text):
        answer.get_buffer().set_text(text)
        ask_button.set_sensitive(True)
        diagnose_button.set_sensitive(True)
        preload_button.set_sensitive(True)
        return False

    def start_provider_action(operation):
        ask_button.set_sensitive(False)
        diagnose_button.set_sensitive(False)
        preload_button.set_sensitive(False)
        answer.get_buffer().set_text("Comprobando Ollama local...")

        def worker():
            try:
                if operation == "preload":
                    status = preload_ollama(OllamaClient())
                    text = "Precarga: " + status.detail + " Modelo: " + (status.model or "-")
                else:
                    status = diagnose_ollama(OllamaClient(), verify_generation=True)
                    text = ("IA operativa: " if status.ready else "Proveedor no operativo: ")
                    text += status.detail
                    if status.model:
                        text += " Modelo: " + status.model
            except (InferenceUnavailable, ValueError) as exc:
                text = "Proveedor no operativo: " + str(exc)
            GLib.idle_add(set_answer, text)

        Thread(target=worker, daemon=True).start()

    diagnose_button.connect("clicked", lambda _button: start_provider_action("verify"))
    preload_button.connect("clicked", lambda _button: start_provider_action("preload"))

    def on_ask(_button):
        prompt = entry.get_text().strip()
        if not prompt:
            set_answer("Escribí una consulta para probar el motor local.")
            return
        ask_button.set_sensitive(False)
        answer.get_buffer().set_text("Consultando Ollama en este equipo...")

        def worker():
            try:
                text = OllamaClient().ask(prompt)
            except (InferenceUnavailable, ValueError) as exc:
                text = "Motor no disponible: " + str(exc)
            GLib.idle_add(set_answer, text)

        Thread(target=worker, daemon=True).start()

    ask_button.connect("clicked", on_ask)
    stack.add_titled(local_page, "local", "IA local")

    # ── Security page: report real safety invariants (not fake toggles). ─
    security = page_box()
    add_text(security, "Seguridad y autonomía supervisada",
             "JARVIS usa permisos de usuario; instalar software, modificar "
             "el sistema, controlar cuentas o ejecutar agentes sensibles "
             "requiere autorización expresa.")
    policies = [
        "Módulos opcionales: no se instalan ni arrancan automáticamente.",
        "Modelos externos: desactivados por defecto; requieren consentimiento y credenciales.",
        "Tareas de agentes: requieren aprobación antes de acciones sensibles.",
        "Consultas locales: limitadas a la interfaz de loopback del propio equipo.",
        "Almacenamiento Live: la persistencia no está garantizada hasta configurarla.",
        "Sandbox: Bubblewrap/Podman se activarán solo después de pruebas de aislamiento.",
    ]
    for policy in policies:
        label = Gtk.Label(label="• " + policy, xalign=0)
        label.set_line_wrap(True)
        security.pack_start(label, False, False, 0)
    stack.add_titled(security, "security", "Seguridad")

    window.add(root)
    window.show_all()
    Gtk.main()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="MJON AI OS - Centro de mando gráfico de IA")
    parser.add_argument("--status-json", action="store_true",
                        help="Leer estado de motores sin ejecutar GUI, red ni instaladores")
    args = parser.parse_args(argv)
    if args.status_json:
        print(get_catalog_json())
        return 0
    return run_gui()


if __name__ == "__main__":
    raise SystemExit(main())
