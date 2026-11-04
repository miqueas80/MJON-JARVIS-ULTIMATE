"""HTTP contract tests for the MJON Windows bridge.

These requests never install models or touch the real host; explicit controls
use a strict same-origin browser gate before reaching native Windows APIs.
"""
from __future__ import annotations

from pathlib import Path
from unittest import TestCase
from unittest.mock import Mock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from mjon_windows.routes import router


class WindowsHttpBridgeTests(TestCase):
    def setUp(self):
        app = FastAPI()
        app.include_router(router)
        self.client = TestClient(app, base_url="http://127.0.0.1:8787")
        self.origin = {"Origin": "http://127.0.0.1:8787"}

    @patch("mjon_windows.routes.diagnose_windows")
    @patch("mjon_windows.routes.inspect_windows_catalog")
    def test_overview_returns_observations_without_inventing_readiness(self, catalog, doctor):
        catalog.return_value = [{"id": "ollama", "status": "installed_unverified"}]
        doctor.return_value = {"platform": "Windows", "model_tested": False, "ollama": "installed_unverified"}
        response = self.client.get("/api/mjon/windows/overview")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertFalse(payload["diagnostics"]["model_tested"])
        self.assertEqual(payload["modules"][0]["status"], "installed_unverified")
        self.assertFalse(payload["automatic_installation"])
        self.assertFalse(payload["automatic_cloud_fallback"])

    @patch("mjon_windows.routes.get_local_models")
    def test_local_model_list_does_not_claim_ready_when_service_absent(self, get_models):
        get_models.side_effect = RuntimeError("Ollama no responde")
        response = self.client.get("/api/mjon/windows/models")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["ready"])
        self.assertEqual(response.json()["models"], [])
        self.assertIn("Ollama", response.json()["reason"])

    @patch("mjon_windows.routes.get_local_models", return_value=("small:latest",))
    def test_local_model_list_only_marks_server_available(self, get_models):
        response = self.client.get("/api/mjon/windows/models")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["server_reachable"])
        self.assertFalse(response.json()["generation_tested"])
        self.assertEqual(response.json()["models"], ["small:latest"])

    @patch("mjon_windows.routes.local_chat", return_value="Hola desde Ollama")
    @patch("mjon_windows.routes.read_status")
    def test_explicit_local_inference_passes_memory_and_selected_model(self, status, chat):
        status.return_value = Mock(memory_total_bytes=8*1024**3)
        body = {"prompt": "Hola", "model": "small:latest"}
        response = self.client.post("/api/mjon/windows/models/test", json=body, headers=self.origin)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["answer"], "Hola desde Ollama")
        self.assertEqual(response.json()["provider"], "ollama_local")
        chat.assert_called_once_with("Hola", model="small:latest", ram_bytes=8*1024**3)

    @patch("mjon_windows.routes.local_chat")
    def test_model_test_requires_browser_origin_not_agents(self, chat):
        body = {"prompt": "Hola", "model": "small:latest"}
        self.assertEqual(self.client.post("/api/mjon/windows/models/test", json=body).status_code, 403)
        self.assertEqual(
            self.client.post("/api/mjon/windows/models/test", json=body,
                headers={"Origin": "http://evil.example"}).status_code, 403)
        self.assertEqual(
            self.client.post("/api/mjon/windows/models/test", json=body,
                headers={"Origin": "http://127.0.0.1:8787", "Authorization": "Bearer agent"}).status_code, 403)
        chat.assert_not_called()

    @patch("mjon_windows.routes.local_chat", side_effect=RuntimeError("No hay modelo local"))
    @patch("mjon_windows.routes.read_status")
    def test_unavailable_model_never_falls_back_to_cloud(self, status, chat):
        status.return_value = Mock(memory_total_bytes=8*1024**3)
        response = self.client.post("/api/mjon/windows/models/test", headers=self.origin,
                                    json={"prompt": "Hola", "model": "small:latest"})
        self.assertEqual(response.status_code, 503)
        self.assertIn("No hay modelo local", response.json()["detail"])

    @patch("mjon_windows.routes.windows_settings", return_value="ms-settings:network-wifi")
    def test_settings_open_only_on_explicit_same_origin_control(self, opener):
        data = {"section": "wifi"}
        self.assertEqual(self.client.post("/api/mjon/windows/settings/open", json=data).status_code, 403)
        opened = self.client.post("/api/mjon/windows/settings/open", json=data, headers=self.origin)
        self.assertEqual(opened.status_code, 200, opened.text)
        self.assertEqual(opened.json()["opened"], "ms-settings:network-wifi")
        opener.assert_called_once_with("wifi")

    @patch("mjon_windows.routes.windows_settings", side_effect=ValueError("Sección no autorizada"))
    def test_unknown_settings_are_refused(self, opener):
        opened = self.client.post("/api/mjon/windows/settings/open",
                                  json={"section": "powershell"}, headers=self.origin)
        self.assertEqual(opened.status_code, 400)

    @patch("mjon_windows.routes.available_storage_bytes", return_value=3*1024**3)
    def test_storage_check_refuses_overcommit_without_writes(self, available):
        response = self.client.post(
            "/api/mjon/windows/storage/check",
            headers=self.origin,
            json={"model_bytes": 2*1024**3}
        )
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertFalse(result["allowed"])
        self.assertGreater(result["required_bytes"], result["free_bytes"])
        self.assertFalse(result["started_download"])

    def test_other_host_and_negative_sizes_are_rejected(self):
        self.assertEqual(self.client.post(
            "/api/mjon/windows/storage/check",
            headers={"Origin": "http://127.0.0.1:9000"},
            json={"model_bytes": 1234}).status_code, 403)
        self.assertEqual(self.client.post(
            "/api/mjon/windows/storage/check", headers=self.origin,
            json={"model_bytes": -5}).status_code, 422)
        self.assertEqual(self.client.post(
            "/api/mjon/windows/storage/check", headers=self.origin,
            json={"model_bytes": 10, "free_bytes": 10**15}).status_code, 422)

    def test_routes_are_attached_only_to_explicit_windows_edition(self):
        source = (Path(__file__).resolve().parents[2] / "dodaios/ui/web/server.py").read_text(encoding="utf-8")
        self.assertIn('MJON_WINDOWS_EDITION', source)
        self.assertIn('app.include_router(mjon_windows_router)', source)
        self.assertIn('sys.platform == "win32"', source)
