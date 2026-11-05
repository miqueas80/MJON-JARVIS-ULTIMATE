"""Executable recovery regressions; SDK tests run only with runtime dependencies.

HTTP transports are simulated here. These tests are not model inference evidence.
"""
from __future__ import annotations

import importlib.util
import json
import os
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from mjon_os.local_inference import InferenceUnavailable, OllamaClient, is_cloud_model


class _Response:
    def __init__(self, value):
        self.value = json.dumps(value).encode()
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False
    def read(self, _limit):
        return self.value


class AdapterRecoveryTests(unittest.TestCase):
    def test_unknown_size_cannot_generate_on_eight_gib(self):
        calls = []
        def respond(req, **kwargs):
            calls.append(req.full_url)
            return _Response({"models": [{"name": "unknown"}]})
        with self.assertRaises(InferenceUnavailable):
            OllamaClient(opener=respond, ram_bytes=8*1024**3).ask("Hello")
        self.assertEqual(len(calls), 1)

    def test_partial_nonstream_response_cannot_be_ready(self):
        def respond(req, **kwargs):
            return _Response({"models": [{"name": "small", "size": 1024}]}
                             if req.full_url.endswith("/tags") else
                             {"message": {"content": "partial answer"}, "done": False})
        with self.assertRaises(InferenceUnavailable):
            OllamaClient(opener=respond).ask("Hello")

    def test_cloud_alias_with_latest_tag_is_still_remote(self):
        self.assertTrue(is_cloud_model("gpt-oss:120b-cloud"))
        self.assertTrue(is_cloud_model("remote-cloud:latest"))

    def test_remote_metadata_cannot_be_treated_as_downloaded_weights(self):
        calls = []
        def respond(req, **kwargs):
            calls.append(req.full_url)
            return _Response({"models": [{"name": "innocent", "size": 1024,
                                          "remote_model": "remote"}]})
        with self.assertRaises(InferenceUnavailable):
            OllamaClient(opener=respond).ask("Hello")
        self.assertEqual(len(calls), 1)


@unittest.skipUnless(all(importlib.util.find_spec(name) for name in
                         ("openai", "httpx", "loguru", "structlog", "keyring")),
                     "Requires actual JARVIS provider runtime dependencies")
class ActualBrainPolicyTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        import httpx
        from dodaios.plugins.brain import ollama
        self.plugin = ollama
        self.rows = [{"name": "small:latest", "size": 1024}]
        self.client_options = []
        real_client = httpx.AsyncClient
        def handler(req):
            if req.url.path == "/api/tags":
                return httpx.Response(200, json={"models": self.rows})
            return httpx.Response(200, json={"capabilities": ["completion", "tools"]})
        def client(**kwargs):
            self.client_options.append(kwargs)
            return real_client(transport=httpx.MockTransport(handler), **kwargs)
        self.enterContext(patch.dict(os.environ, {"MJON_NATIVE_OS": "1", "OLLAMA_HOST": ""}))
        self.enterContext(patch.object(ollama.httpx, "AsyncClient", side_effect=client))
        self.endpoint = SimpleNamespace(base_url="http://127.0.0.1:11434", credential=None,
                                        via_proxy=False)
        self.enterContext(patch.object(ollama.cfg, "resolve_provider_endpoint",
                                      side_effect=lambda *a, **kw: self.endpoint))
        self.enterContext(patch.object(ollama.cfg, "load_config", return_value=SimpleNamespace(
            brain=SimpleNamespace(providers={}))))
        self.enterContext(patch.object(ollama, "physical_memory", return_value=8*1024**3,
                                      create=True))

    async def test_native_rejects_configured_remote_endpoint_before_sdk(self):
        self.endpoint.base_url = "http://gpu.lan:11434"
        with self.assertRaises(ValueError):
            self.plugin.OllamaBrain()._resolve_root()

    async def test_native_rejects_explicit_cloud_model(self):
        self.rows = [{"name": "gpt-oss:120b-cloud", "size": 1024}]
        with self.assertRaises(RuntimeError):
            await self.plugin.OllamaBrain(model=self.rows[0]["name"])._resolve_model()

    async def test_native_rejects_remote_metadata(self):
        self.rows[0]["remote_host"] = "https://ollama.com"
        with self.assertRaises(RuntimeError):
            await self.plugin.OllamaBrain()._resolve_model()

    async def test_native_rejects_pinned_unknown_or_oversized_weights(self):
        for size in (None, 12*1024**3):
            self.rows[0]["size"] = size
            with self.assertRaises(RuntimeError):
                await self.plugin.OllamaBrain(model="small")._resolve_model()

    async def test_discovery_uses_no_environment_proxy_or_redirect(self):
        self.assertEqual(await self.plugin.OllamaBrain()._resolve_model(), "small:latest")
        self.assertTrue(self.client_options)
        for options in self.client_options:
            self.assertIs(options.get("trust_env"), False)
            self.assertIs(options.get("follow_redirects"), False)

    async def test_sdk_uses_no_environment_proxy(self):
        import openai
        captured = {}
        def sdk(**kwargs):
            captured.update(kwargs)
            return object()
        with patch.object(openai, "AsyncOpenAI", side_effect=sdk):
            self.plugin.OllamaBrain()._ensure_client()
        self.assertIn("http_client", captured)
        self.assertFalse(captured["http_client"]._trust_env)
        await captured["http_client"].aclose()

    async def test_native_refuses_excessive_context_without_truncation(self):
        from dodaios.core.protocols import BrainRequest
        brain = self.plugin.OllamaBrain()
        brain.set_context_window(32768)
        with self.assertRaisesRegex(RuntimeError, "native desktop context limit"):
            await brain._prepare_call("small", BrainRequest(messages=()))

    async def test_upstream_mode_preserves_user_lan_and_model(self):
        with patch.dict(os.environ, {"MJON_NATIVE_OS": "0"}):
            self.endpoint.base_url = "http://gpu.lan:11434"
            brain = self.plugin.OllamaBrain(model="user-choice")
            self.assertEqual(brain._resolve_root(), "http://gpu.lan:11434")
            self.assertEqual(await brain._resolve_model(), "user-choice")

    async def test_native_boot_cannot_bypass_opt_in_preload_service(self):
        from dodaios.local_models.autostart import run_once, should_autostart
        config = SimpleNamespace(brain=SimpleNamespace(primary="ollama", providers={}))
        self.assertFalse(should_autostart(config)[0])
        record = await run_once(config,
                                status=lambda: {"running": False, "installed": True},
                                start=lambda: self.fail("Native startup must not spawn a daemon"))
        self.assertFalse(record["started"])
        self.assertEqual(record["warmed"], "")

    async def test_first_boot_sets_actual_typed_fallback_and_output_budget(self):
        from pathlib import Path
        import tomllib
        from mjon_os.first_boot import personalize_template
        from dodaios.core.config import JarvisConfig
        root = Path(__file__).resolve().parents[2]
        raw = personalize_template((root / "dodaios.toml.example").read_text(), root / "test-data")
        config = JarvisConfig.model_validate(tomllib.loads(raw))
        self.assertEqual(config.brain.local_fallback, "ollama")
        self.assertEqual(config.brain.local_fallback_model, "")
        self.assertLess(config.brain.max_tokens, 2048)
        self.assertFalse(config.ack_brain.enabled)

    async def test_native_background_resolver_cannot_append_keyed_cloud_families(self):
        from dodaios.brain.resolver import _resolve_chain
        from dodaios.core.config import JarvisConfig, BrainConfig
        config = JarvisConfig(brain=BrainConfig(primary="ollama"))
        self.assertEqual(_resolve_chain(config), [("ollama", None)])

    async def test_actual_manager_chain_cannot_fall_through_to_cloud(self):
        from dodaios.brain.manager import BrainManager
        from dodaios.core.bus import EventBus
        from dodaios.core.config import JarvisConfig, BrainConfig
        config = JarvisConfig(brain=BrainConfig(primary="ollama", deep_brain="gemini"))
        manager = BrainManager(config=config, bus=EventBus(), tools={})
        manager._active_name = "ollama"
        with patch.object(BrainManager, "_fast_model", return_value="small"), \
                patch.object(BrainManager, "_deep_model", return_value=None), \
                patch.object(manager._registry, "available", return_value=["ollama", "gemini"]), \
                patch.object(BrainManager, "_active_can_call_tools", return_value=True), \
                patch.object(BrainManager, "_keep_off_voice_key", side_effect=lambda chain, **kw: chain):
            self.assertEqual(manager._build_fallback_chain("deep"), [("ollama", "small")])


if __name__ == "__main__":
    unittest.main()
