"""Regression for provider health checks falsely succeeding on the first stream event.

A streaming provider may yield metadata or a text chunk and then fail.
The real user turn fails, so a green provider-test outcome is incorrect.
"""
from __future__ import annotations

import unittest

from dodaios.brain.healthcheck import BrainHealthChecker
from dodaios.core.protocols import BrainDelta


class _Registry:
    def __init__(self, deltas: list[BrainDelta], fail_after: bool = False):
        self.deltas = deltas
        self.fail_after = fail_after

    def instantiate(self, provider: str, *, model: str):
        deltas, fail_after = self.deltas, self.fail_after

        class _Brain:
            async def complete(self, _request):
                for delta in deltas:
                    yield delta
                if fail_after:
                    raise RuntimeError("provider failed after a partial stream")

        return _Brain()


class StreamProviderHealthTests(unittest.IsolatedAsyncioTestCase):
    async def test_metadata_only_stream_is_not_a_healthy_provider(self):
        checker = BrainHealthChecker(_Registry([
            BrainDelta(usage={"input_tokens": 1}, finish_reason="stop")
        ]))
        status = await checker.probe("ollama", "small:latest", timeout_s=1)
        self.assertFalse(status.ok)
        self.assertIn("text", (status.error or "").lower())

    async def test_first_text_then_provider_error_is_not_green(self):
        checker = BrainHealthChecker(_Registry(
            [BrainDelta(content="partial")], fail_after=True
        ))
        status = await checker.probe("ollama", "small:latest", timeout_s=1)
        self.assertFalse(status.ok)
        self.assertIn("provider failed", status.error or "")

    async def test_metadata_then_valid_text_is_healthy(self):
        checker = BrainHealthChecker(_Registry([
            BrainDelta(usage={"input_tokens": 1}),
            BrainDelta(content="OK"),
            BrainDelta(finish_reason="stop"),
        ]))
        status = await checker.probe("ollama", "small:latest", timeout_s=1)
        self.assertTrue(status.ok)

    async def test_empty_stream_is_never_healthy(self):
        checker = BrainHealthChecker(_Registry([]))
        status = await checker.probe("ollama", "small:latest", timeout_s=1)
        self.assertFalse(status.ok)


if __name__ == "__main__":
    unittest.main()
