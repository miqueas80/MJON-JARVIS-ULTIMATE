"""The passive upstream Ollama monitor must not claim green on HTTP alone."""
from __future__ import annotations

import unittest
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
