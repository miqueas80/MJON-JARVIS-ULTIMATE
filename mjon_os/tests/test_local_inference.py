"""Tests for the first real offline inference adapter of the MJON OS fabric."""
from __future__ import annotations
import json
import io
import unittest
from urllib.error import HTTPError, URLError

from mjon_os.local_inference import OllamaClient, InferenceUnavailable


class FakeHTTPResponse:
    def __init__(self, data):
        self.data = json.dumps(data).encode()
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False
    def read(self, size=-1):
        return self.data


class OllamaClientTests(unittest.TestCase):
    def test_model_list_is_fetched_only_over_loopback(self):
        requests = []
        def open_fn(request, **kwargs):
            requests.append(request.full_url)
            return FakeHTTPResponse({"models": [{"name": "tiny:latest", "size": 700000}]})
        client = OllamaClient(opener=open_fn)
        self.assertEqual(client.models(), ("tiny:latest",))
        self.assertEqual(requests, ["http://127.0.0.1:11434/api/tags"])

    def test_missing_model_is_not_disguised_as_working_offline_ai(self):
        client = OllamaClient(opener=lambda request, **kw: FakeHTTPResponse({"models": []}))
        with self.assertRaisesRegex(InferenceUnavailable, "modelo"):
            client.ask("hola")

    def test_chat_uses_only_downloaded_local_model(self):
        calls = []
        def opener(request, **kwargs):
            calls.append(request)
            if request.full_url.endswith("/api/tags"):
                return FakeHTTPResponse({"models": [{"name": "tiny:latest", "size": 700000}]})
            return FakeHTTPResponse({"done": True, "message": {"role": "assistant", "content": "Hola desde la PC"}})
        self.assertEqual(OllamaClient(opener=opener).ask("hola"), "Hola desde la PC")
        self.assertEqual(calls[1].full_url, "http://127.0.0.1:11434/api/chat")
        data = json.loads(calls[1].data)
        self.assertEqual(data["model"], "tiny:latest")
        self.assertFalse(data["stream"])
        self.assertEqual(data["messages"][0]["role"], "user")
        self.assertLessEqual(data["options"]["num_predict"], 256)

    def test_eight_gigabytes_chooses_smallest_existing_model(self):
        def responder(request, **kw):
            if request.full_url.endswith("/api/tags"):
                return FakeHTTPResponse({"models": [
                    {"name": "huge", "size": 12*1024**3},
                    {"name": "small", "size": 700*1024**2},
                ]})
            sent = json.loads(request.data)
            self.assertEqual(sent["model"], "small")
            return FakeHTTPResponse({"done": True, "message": {"content": "Modelo chico"} })
        client = OllamaClient(opener=responder, ram_bytes=8*1024**3)
        self.assertEqual(client.ask("hola"), "Modelo chico")

    def test_eight_gigabytes_rejects_an_oversized_ollama_model(self):
        def responder(request, **kw):
            if request.full_url.endswith("/api/tags"):
                return FakeHTTPResponse({"models": [
                    {"name": "oversized", "size": 11*1024**3},
                ]})
            self.fail("No se debe iniciar inferencia con un modelo demasiado grande")
        client = OllamaClient(opener=responder, ram_bytes=8*1024**3)
        with self.assertRaisesRegex(InferenceUnavailable, "memoria"):
            client.ask("hola", model="oversized")

    def test_cloud_model_tag_is_never_used_for_an_offline_chat(self):
        calls = []
        def responder(request, **kw):
            calls.append(request.full_url)
            if request.full_url.endswith("/api/tags"):
                return FakeHTTPResponse({"models": [
                    {"name": "gemma4:cloud", "size": 300000},
                    {"name": "local:tiny", "size": 700000},
                ]})
            return FakeHTTPResponse({"done": True, "message": {"content": "local response"}})
        client = OllamaClient(opener=responder, ram_bytes=8 * 1024**3)
        self.assertEqual(client.ask("hola"), "local response")
        with self.assertRaisesRegex(InferenceUnavailable, "cloud"):
            client.ask("hola", model="gemma4:cloud")
        self.assertEqual(calls.count("http://127.0.0.1:11434/api/chat"), 1)

    def test_local_requests_disable_http_redirect_following(self):
        from mjon_os.local_inference import _NoRedirect
        handler = _NoRedirect()
        self.assertIsNone(handler.redirect_request(None, None, None, None, None, None))

    def test_refuses_unbounded_input_or_remote_endpoints(self):
        with self.assertRaises(ValueError):
            OllamaClient(endpoint="http://8.8.8.8:11434")
        with self.assertRaises(ValueError):
            OllamaClient(endpoint="http://localhost.evil:11434")
        client = OllamaClient(opener=lambda req, **kwargs: FakeHTTPResponse({"models": []}))
        with self.assertRaises(ValueError):
            client.ask("X"*9000)

    def test_200_provider_error_is_not_falsely_reported_as_success(self):
        client = OllamaClient(opener=lambda req, **kw: FakeHTTPResponse(
            {"error": "model runner exited unexpectedly"}))
        with self.assertRaisesRegex(InferenceUnavailable, "runner exited"):
            client.models()

    def test_http_provider_error_preserves_status_and_safe_reason(self):
        def fail(req, **kwargs):
            raise HTTPError(req.full_url, 503, "Service Unavailable", {},
                            io.BytesIO(b'{"error": "model requires more memory"}'))
        with self.assertRaisesRegex(InferenceUnavailable, "HTTP 503: model requires more memory"):
            OllamaClient(opener=fail).models()

    def test_transport_failure_is_reported_not_fabricated(self):
        def fail(req, **kwargs):
            raise URLError("offline")
        with self.assertRaisesRegex(InferenceUnavailable, "Ollama"):
            OllamaClient(opener=fail).models()


if __name__ == "__main__":
    unittest.main()
