"""Behavior contracts for the MJON AI OS native module control plane.

These tests intentionally require a real policy engine, not a decorative
listing of products. Optional frameworks never install or start automatically.
"""
from __future__ import annotations

import unittest
from mjon_os.ai_fabric import CATALOG, HardwareProfile, inspect_modules, plan_capability


class AIFabricTests(unittest.TestCase):
    def test_all_requested_domains_have_a_real_catalog_entry(self):
        expected = {"inference", "agents", "programming", "voice", "vision",
                    "knowledge", "automation", "multimedia", "training",
                    "optimization", "security"}
        self.assertFalse(expected - {m.domain for m in CATALOG})
        ids = [m.module_id for m in CATALOG]
        self.assertEqual(len(ids), len(set(ids)))

    def test_requested_engines_have_explicit_optional_install_contract(self):
        ids = {m.module_id: m for m in CATALOG}
        for name in ("llama_cpp", "ollama", "localai", "onnxruntime", "openvino",
                     "vllm", "sglang", "openclaw", "langgraph", "crew_ai",
                     "goose", "openfang", "pydantic_ai", "free_llm_api"):
            self.assertIn(name, ids)
            self.assertFalse(ids[name].auto_install)
            self.assertFalse(ids[name].auto_start)

    def test_eight_gigabyte_no_gpu_is_never_sent_to_workstation_only_engine(self):
        hw = HardwareProfile(ram_gib=8, discrete_gpu=False, network_available=False)
        commands = {"ollama", "vllm", "sglang", "llama-cli"}
        plan = plan_capability("inference", hw, executable_exists=lambda name: name in commands)
        self.assertEqual(plan.engine_id, "llama_cpp")
        self.assertFalse(plan.remote)
        self.assertFalse(plan.execute_automatically)

    def test_offline_never_selects_remote_provider(self):
        hw = HardwareProfile(ram_gib=8, discrete_gpu=False, network_available=False)
        plan = plan_capability("inference", hw, executable_exists=lambda cmd: False,
                               allow_remote=True, credentials_present=True)
        self.assertIsNone(plan.engine_id)
        self.assertIn("disponible", plan.reason)

    def test_remote_not_selected_without_explicit_consent_and_credentials(self):
        hw = HardwareProfile(ram_gib=32, discrete_gpu=True, network_available=True)
        for allow, creds in ((False, True), (True, False)):
            with self.subTest(allow=allow, creds=creds):
                plan = plan_capability("inference", hw, executable_exists=lambda name: False,
                                       allow_remote=allow, credentials_present=creds)
                self.assertIsNone(plan.engine_id)
        plan = plan_capability("inference", hw, executable_exists=lambda name: False,
                               allow_remote=True, credentials_present=True)
        self.assertEqual(plan.engine_id, "free_llm_api")
        self.assertTrue(plan.remote)
        self.assertFalse(plan.execute_automatically)

    def test_agents_and_privileged_tasks_always_require_approval(self):
        hw = HardwareProfile(ram_gib=32, discrete_gpu=True, network_available=True)
        plan = plan_capability("agents", hw, executable_exists=lambda cmd: True)
        self.assertFalse(plan.execute_automatically)
        self.assertTrue(plan.requires_approval)

    def test_status_never_claims_preinstalled_when_command_missing(self):
        modules = inspect_modules(executable_exists=lambda name: False)
        ollama = next(m for m in modules if m["id"] == "ollama")
        self.assertEqual(ollama["status"], "not_installed")
        self.assertEqual(ollama["launch"], "manual_only")

    def test_catalog_cannot_execute_network_install_commands(self):
        for module in CATALOG:
            self.assertNotIn("curl | sh", repr(module))
            self.assertNotIn("sudo ", repr(module))


if __name__ == "__main__":
    unittest.main()
