"""The passive upstream Ollama monitor must not claim green on HTTP alone."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from dodaios.local_models import health_monitor as monitor


class NoFalseGreenOllamaTests(unittest.IsolatedAsyncioTestCase):
    async def test_server_only_check_does_not_mark_model_healthy(self):
        async def server(_root):
            return {"ok": True, "detail": ""}

        async def prohibited_generation(_cfg, _model):
            raise AssertionError("An inactive model must not be loaded")

        with patch.object(monitor, "_configured_roles", return_value={"chat": "local:tiny"}):
            record = await monitor.check_once(
                SimpleNamespace(),
                root="http://127.0.0.1:11434",
                probe=server,
                generate=prohibited_generation,
                in_use=lambda _cfg: (False, "no local role is active"),
                persist=False,
            )
        self.assertEqual(record["status"], "unknown")
        self.assertIn("not checked", record["reason"])

    async def test_legacy_green_record_needs_fresh_generation_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "local_models_health.json"
            path.write_text(json.dumps({
                "status": "ok", "reason": "", "last_ok": "2026-11-04T10:00:00"
            }))
            with patch.object(monitor, "health_path", return_value=path):
                record = monitor.read_health_record()
            self.assertEqual(record["status"], "unknown")
            self.assertIsNone(record["last_ok"])

    async def test_new_generation_verdict_can_still_be_green(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "local_models_health.json"
            with patch.object(monitor, "health_path", return_value=path), \
                    patch.object(monitor, "_evidence_context", return_value="same-config"):
                monitor.write_health_record("ok", "", checked_at="2026-11-05T00:00:00")
                record = monitor.read_health_record()
            self.assertEqual(record["status"], "ok")
            self.assertEqual(record["last_ok"], "2026-11-05T00:00:00")

    async def test_green_record_is_invalidated_when_model_or_endpoint_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "local_models_health.json"
            with patch.object(monitor, "health_path", return_value=path):
                with patch.object(monitor, "_evidence_context", return_value="old-model-endpoint"):
                    monitor.write_health_record("ok", "")
                with patch.object(monitor, "_evidence_context", return_value="new-model-endpoint"):
                    self.assertEqual(monitor.read_health_record()["status"], "unknown")

    async def test_server_only_probe_with_no_chat_model_is_not_green(self):
        async def server(_root):
            return {"ok": True, "detail": ""}

        with patch.object(monitor, "_configured_roles", return_value={"voice": "speech-model"}):
            record = await monitor.check_once(
                SimpleNamespace(),
                root="http://127.0.0.1:11434",
                probe=server,
                in_use=lambda _cfg: (False, "nothing active"),
                persist=False,
            )
        self.assertEqual(record["status"], "unknown")


if __name__ == "__main__":
    unittest.main()
