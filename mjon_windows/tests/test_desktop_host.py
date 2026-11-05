"""Security + behavior contracts for the optional Windows desktop shell."""
from __future__ import annotations

import json
import threading
import unittest
from http.client import HTTPConnection
from pathlib import Path
from unittest.mock import patch

from mjon_windows.desktop_host import create_server


class DesktopHostTests(unittest.TestCase):
    def setUp(self):
        self.server = create_server(port=0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.port = self.server.server_address[1]

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)

    def request(self, path, *, method="GET", body=None, origin=None, host=None):
        conn = HTTPConnection("127.0.0.1", self.port, timeout=3)
        headers = {"Host": host or f"127.0.0.1:{self.port}"}
        if body is not None:
            headers["Content-Type"] = "application/json"
        if origin is not None:
            headers["Origin"] = origin
        conn.request(method, path, body=json.dumps(body) if body is not None else None, headers=headers)
        res = conn.getresponse()
        data = res.read()
        status = res.status
        headers_out = dict(res.getheaders())
        conn.close()
        return status, data, headers_out

    def test_user_interface_is_local_and_identified_as_mjon(self):
        status, data, headers = self.request("/")
        self.assertEqual(status, 200)
        self.assertIn(b"MJON AI OS", data)
        self.assertIn(b"JARVIS", data)
        self.assertIn(b"Modelos IA", data)
        self.assertIn(b"Seguridad", data)
        self.assertIn(b"Rendimiento", data)
        self.assertIn(b"Content-Security-Policy", str(headers).encode())

    def test_native_static_assets_serve_without_public_cdn(self):
        for file_name, marker in [("/app.js", b"api/overview"), ("/style.css", b"orbital")]:
            status, data, headers = self.request(file_name)
            self.assertEqual(status, 200)
            self.assertIn(marker, data)
            self.assertIn(b"'self'", headers["Content-Security-Policy"].encode())
        self.assertEqual(self.request("/../../etc/passwd")[0], 404)

    def test_api_diagnostic_is_actual_backend_observation(self):
        fake = {"platform": "Windows", "memory_total_bytes": 8 * 1024 ** 3, "model_tested": False}
        with patch("mjon_windows.desktop_host.diagnose_windows", return_value=fake), patch(
            "mjon_windows.desktop_host.inspect_windows_catalog", return_value=[]
        ):
            status, data, _ = self.request("/api/overview")
        self.assertEqual(status, 200)
        parsed = json.loads(data)
        self.assertEqual(parsed["diagnostics"], fake)
        self.assertFalse(parsed["automatic_cloud_fallback"])

    def test_cross_site_request_rejected_without_changing_windows(self):
        with patch("mjon_windows.desktop_host.windows_settings") as settings:
            status, _, _ = self.request("/api/settings", method="POST", origin="https://example.org",
                                        body={"section": "wifi"})
        self.assertEqual(status, 403)
        settings.assert_not_called()

    def test_cross_site_get_host_header_rejected(self):
        status, _, _ = self.request("/", host="external.example")
        self.assertEqual(status, 403)

    def test_whitelisted_settings_action_only_with_same_origin(self):
        origin = f"http://127.0.0.1:{self.port}"
        with patch("mjon_windows.desktop_host.windows_settings", return_value="ms-settings:network-wifi") as settings:
            status, data, _ = self.request("/api/settings", method="POST",
                                           origin=origin, body={"section": "wifi"})
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(data)["opened"], "ms-settings:network-wifi")
        settings.assert_called_once_with("wifi")

    def test_refuse_unsanctioned_operations(self):
        origin = f"http://127.0.0.1:{self.port}"
        with patch("mjon_windows.desktop_host.windows_settings") as settings:
            status, _, _ = self.request("/api/settings", method="POST",
                                        origin=origin, body={"section": "powershell.exe"})
        self.assertEqual(status, 400)
        settings.assert_not_called()
        self.assertEqual(self.request("/api/exec", method="POST", origin=origin, body={})[0], 404)

    def test_inference_has_no_remote_fallback(self):
        origin = f"http://127.0.0.1:{self.port}"
        with patch("mjon_windows.desktop_host.read_status") as system, patch(
            "mjon_windows.desktop_host.local_chat", return_value="Hola, desde tu equipo."
        ) as chat:
            system.return_value.memory_total_bytes = 8 * 1024 ** 3
            status, data, _ = self.request("/api/ask", method="POST", origin=origin,
                                          body={"model": "smollm2:135m", "prompt": "Hola"})
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(data)["provider"], "ollama_local")
        self.assertIn("Hola", json.loads(data)["answer"])
        chat.assert_called_once_with("Hola", model="smollm2:135m", ram_bytes=8 * 1024 ** 3)

    def test_invalid_generation_does_not_invoke_local_llm(self):
        origin = f"http://127.0.0.1:{self.port}"
        with patch("mjon_windows.desktop_host.local_chat") as chat:
            status, _, _ = self.request("/api/ask", method="POST", origin=origin,
                                        body={"model": "", "prompt": "Hola"})
        self.assertEqual(status, 400)
        chat.assert_not_called()

    def test_browser_recovery_is_loopback_only_and_explicit(self):
        from unittest.mock import Mock
        from mjon_windows.desktop_host import browser_fallback
        opener = Mock(return_value=True)
        notifier = Mock()
        browser_fallback("http://127.0.0.1:53721/", opener=opener, notifier=notifier)
        opener.assert_called_once_with("http://127.0.0.1:53721/")
        notifier.assert_called_once()
        with self.assertRaises(ValueError):
            browser_fallback("https://unknown.example/", opener=opener, notifier=notifier)
        self.assertEqual(opener.call_count, 1)


if __name__ == "__main__":
    unittest.main()
