"""Isolated, offline-first MJON Windows desktop UI host.

The browser/WebView UI only talks to a random 127.0.0.1 port. No arbitrary
shell, remote models, subprocess downloads, installer tasks or autostart. The
original approved navigation is implemented as local static HTML/CSS/JS.
"""
from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import platform
from typing import Any
from urllib.error import URLError
from urllib.request import urlopen

from mjon_jarvis.system_status import read_status
from mjon_os.local_inference import InferenceUnavailable, OllamaClient
from .backend import diagnose_windows, inspect_windows_catalog, local_chat, windows_settings

WEB_ROOT = Path(__file__).resolve().parent / "web"
FILES = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
    "/style.css": ("style.css", "text/css; charset=utf-8"),
}
SETTINGS = frozenset({
    "wifi", "bluetooth", "ethernet", "sound", "display",
    "power", "storage", "apps", "privacy", "updates",
})
MAX_BODY = 4096
CSP = ("default-src 'none'; script-src 'self'; style-src 'self'; "
       "connect-src 'self'; img-src 'self' data:; font-src 'self'; "
       "base-uri 'none'; form-action 'none'; frame-ancestors 'none'")

class LoopbackServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = False


def create_server(*, port: int = 0) -> LoopbackServer:
    """Bind only IPv4 loopback; passing port 0 creates an unpredictable port."""
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, format: str, *args: Any) -> None:
            # No prompts or model answers in log output.
            pass

        def _headers(self, status: int, mime: str, length: int) -> None:
            self.send_response(status)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", str(length))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("X-Frame-Options", "DENY")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Content-Security-Policy", CSP)
            self.end_headers()

        def _emit(self, status: int, data: Any) -> None:
            raw = json.dumps(data, ensure_ascii=False).encode("utf-8")
            self._headers(status, "application/json; charset=utf-8", len(raw))
            self.wfile.write(raw)

        def _fail(self, status: int, message: str) -> None:
            self._emit(status, {"error": message})

        def _is_loopback_request(self) -> bool:
            return (
                self.client_address[0] == "127.0.0.1"
                and self.headers.get("Host", "") == f"127.0.0.1:{self.server.server_port}"
            )

        def _permitted_post(self) -> bool:
            expected_origin = f"http://127.0.0.1:{self.server.server_port}"
            return (
                self._is_loopback_request()
                and self.headers.get("Origin", "") == expected_origin
                and self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
                == "application/json"
            )

        def do_GET(self) -> None:
            if not self._is_loopback_request():
                self._fail(403, "Solo se permite acceso desde MJON local.")
                return
            path = self.path
            if path in FILES:
                name, mime = FILES[path]
                try:
                    data = (WEB_ROOT / name).read_bytes()
                except OSError:
                    self._fail(503, "Faltan recursos locales del escritorio.")
                    return
                self._headers(200, mime, len(data))
                self.wfile.write(data)
                return
            if path == "/api/health":
                self._emit(200, {"app": "MJON AI OS", "loopback": True, "cloud": False})
                return
            if path == "/api/overview":
                try:
                    diagnostics = diagnose_windows()
                    modules = inspect_windows_catalog()
                except (RuntimeError, ValueError, OSError) as exc:
                    self._fail(503, str(exc))
                    return
                self._emit(200, {
                    "product": "MJON AI OS", "diagnostics": diagnostics,
                    "modules": modules, "automatic_cloud_fallback": False,
                    "automatic_installation": False,
                })
                return
            if path == "/api/models":
                try:
                    models = OllamaClient().models()
                except (RuntimeError, InferenceUnavailable, ValueError, OSError) as exc:
                    self._emit(200, {"models": [], "ready": False, "reason": str(exc)})
                    return
                self._emit(200, {
                    "models": list(models), "ready": False,
                    "reason": "Modelos detectados; elegí uno y probá generación local."
                    if models else "Ollama no tiene modelos locales descargados.",
                })
                return
            self._fail(404, "Ruta inexistente.")

        def do_POST(self) -> None:
            if self.path not in {"/api/settings", "/api/ask"}:
                self._fail(404, "Acción inexistente.")
                return
            if not self._permitted_post():
                self._fail(403, "Origen no autorizado; usá la aplicación MJON local.")
                return
            try:
                length = int(self.headers.get("Content-Length", "-1"))
            except ValueError:
                length = -1
            if length < 2 or length > MAX_BODY:
                self._fail(413, "Solicitud inválida o demasiado grande.")
                return
            try:
                body = json.loads(self.rfile.read(length))
            except (ValueError, UnicodeDecodeError):
                self._fail(400, "JSON inválido.")
                return
            if not isinstance(body, dict):
                self._fail(400, "Se requiere un objeto JSON.")
                return
            if self.path == "/api/settings":
                section = body.get("section")
                if set(body) != {"section"} or section not in SETTINGS:
                    self._fail(400, "Configuración no autorizada.")
                    return
                try:
                    uri = windows_settings(section)
                except (RuntimeError, OSError, ValueError) as exc:
                    self._fail(503, str(exc))
                    return
                self._emit(200, {"opened": uri})
                return
            prompt, model = body.get("prompt"), body.get("model")
            if (set(body) != {"prompt", "model"}
                    or not isinstance(prompt, str)
                    or not isinstance(model, str)
                    or not prompt.strip() or len(prompt) > 1024
                    or not model.strip() or len(model) > 200):
                self._fail(400, "Indicá una consulta y un modelo local instalado.")
                return
            try:
                ram = read_status().memory_total_bytes
                response = local_chat(prompt, model=model, ram_bytes=ram)
            except (RuntimeError, InferenceUnavailable, ValueError, OSError) as exc:
                self._fail(503, str(exc))
                return
            self._emit(200, {
                "provider": "ollama_local", "answer": response, "model": model,
                "generation_tested": True,
            })

    return LoopbackServer(("127.0.0.1", port), Handler)


def self_test() -> int:
    """Headless, non-network smoke check used by Windows CI."""
    server = create_server(port=0)
    import threading
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with urlopen(f"http://127.0.0.1:{server.server_port}/api/health", timeout=5) as stream:
            health = json.load(stream)
        with urlopen(f"http://127.0.0.1:{server.server_port}/", timeout=5) as stream:
            html = stream.read()
        if health.get("loopback") is True and b"MJON AI OS" in html and b"JARVIS" in html:
            return 0
        return 2
    except (URLError, OSError, ValueError):
        return 2
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def main() -> int:
    """Run native WebView2 window; no network endpoints other than localhost."""
    if platform.system() != "Windows":
        raise RuntimeError("La interfaz nativa MJON requiere Windows.")
    try:
        import webview
    except ImportError as exc:
        raise RuntimeError("Falta pywebview/WebView2 para abrir el escritorio MJON.") from exc
    server = create_server(port=0)
    import threading
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        url = f"http://127.0.0.1:{server.server_port}/"
        webview.create_window("MJON AI OS — JARVIS", url, width=1400,
                              height=850, min_size=(900, 580),
                              background_color="#060c1d")
        webview.start(debug=False)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
