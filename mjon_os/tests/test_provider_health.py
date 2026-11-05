"""Regression tests: a green indicator must require a genuine response."""
import json
import tempfile
import unittest
from pathlib import Path

from mjon_os.local_inference import InferenceUnavailable
from mjon_os.provider_health import diagnose, preload, preload_from_config


class FakeClient:
    _ram_bytes = 8 * 1024 ** 3

    def __init__(self, *, models=None, loaded=None, failure=None, answer="OK"):
        self.inventory = models if models is not None else [("small:latest", 600 * 1024**2)]
        self.loaded = list(loaded or [])
        self.failure = failure
        self.answer = answer
        self.requests = []

    def _model_inventory(self):
        if self.failure == "offline":
            raise InferenceUnavailable("Servidor caído")
        return tuple(self.inventory)

    def _request(self, route, *, body=None, timeout=8):
        self.requests.append((route, body))
        if route == "/api/generate":
            if self.failure == "generate":
                raise InferenceUnavailable("Error del proveedor 500")
            self.loaded = [body["model"]]
            return {"done": True}
        if route == "/api/ps":
            return {"models": [{"name": model} for model in self.loaded]}
        raise AssertionError(route)

    def ask(self, prompt, *, model=None):
        self.requests.append(("/api/chat", {"model": model, "prompt": prompt}))
        if self.failure == "generate":
            raise InferenceUnavailable("Error del proveedor 500")
        return self.answer


class ProviderHealthTests(unittest.TestCase):
    def test_downloaded_model_never_means_healthy_provider(self):
        client = FakeClient()
        status = diagnose(client)
        self.assertEqual(status.state, "downloaded_unverified")
        self.assertFalse(status.ready)
        self.assertNotIn("/api/chat", [route for route, _ in client.requests])

    def test_loaded_model_is_not_a_green_inference_check(self):
        self.assertEqual(diagnose(FakeClient(loaded=["small:latest"])).state,
                         "loaded_unverified")

    def test_real_generation_success_is_the_only_green_state(self):
        client = FakeClient(loaded=["small:latest"])
        status = diagnose(client, verify_generation=True)
        self.assertTrue(status.ready)
        self.assertEqual(status.model, "small:latest")
        self.assertIn("/api/chat", [route for route, _ in client.requests])

    def test_provider_fails_after_green_binary_or_loaded_status(self):
        status = diagnose(FakeClient(loaded=["small:latest"], failure="generate"),
                          verify_generation=True)
        self.assertFalse(status.ready)
        self.assertEqual(status.state, "unavailable")
        self.assertIn("proveedor", status.detail)

    def test_offline_server_and_empty_catalog_do_not_look_healthy(self):
        self.assertFalse(diagnose(FakeClient(failure="offline")).ready)
        self.assertFalse(diagnose(FakeClient(models=[])).ready)

    def test_preload_is_local_only_and_checks_resident_model(self):
        client = FakeClient()
        result = preload(client, model="small:latest", keep_alive="5m")
        self.assertEqual(result.state, "loaded_unverified")
        self.assertFalse(result.ready)
        self.assertEqual(client.requests[0][0], "/api/generate")
        self.assertEqual(client.requests[0][1]["prompt"], "")
        self.assertEqual(client.requests[0][1]["keep_alive"], "5m")
        self.assertEqual(client.requests[1][0], "/api/ps")

    def test_preload_rejects_large_models_and_missing_weights(self):
        with self.assertRaisesRegex(InferenceUnavailable, "RAM"):
            preload(FakeClient(models=[("huge", 9 * 1024**3)]), model="huge")
        with self.assertRaisesRegex(InferenceUnavailable, "descargado"):
            preload(FakeClient(), model="not-downloaded")

    def test_preload_config_is_opt_in_and_never_downloads(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ollama-preload.json"
            client = FakeClient()
            self.assertEqual(preload_from_config(path, client=client).state, "disabled")
            self.assertEqual(client.requests, [])
            path.write_text(json.dumps({"enabled": False, "model": "small:latest"}))
            self.assertEqual(preload_from_config(path, client=client).state, "disabled")
            path.write_text(json.dumps({"enabled": True, "model": "small:latest"}))
            self.assertEqual(preload_from_config(path, client=client).state, "loaded_unverified")

    def test_invalid_keep_alive_rejected(self):
        with self.assertRaises(ValueError):
            preload(FakeClient(), keep_alive="-1")


if __name__ == "__main__":
    unittest.main()
