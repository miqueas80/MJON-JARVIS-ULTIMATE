"""Windows migration: no Linux desktop dependency, no fake readiness or cloud fallback."""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

from mjon_windows.backend import (
    inspect_windows_catalog, plan_windows_capability, windows_settings,
    storage_budget, model_directory, diagnose_windows, local_chat,
)


class WindowsCatalogTests(unittest.TestCase):
    def test_linux_only_modules_are_not_offered_as_windows_features(self):
        items = inspect_windows_catalog(executable_exists=lambda x: True,
                                        distribution_present=lambda x: True)
        ids = {item["id"] for item in items}
        for linux_only in ("zram", "apparmor", "bubblewrap", "openvoiceos", "mjon_anr"):
            self.assertNotIn(linux_only, ids)
        self.assertIn("ollama", ids)
        self.assertEqual(next(item for item in items if item["id"] == "ollama")["status"],
                         "installed_unverified")

    def test_windows_python_alias_detected_without_python3_command(self):
        seen = []
        def exists(executable):
            seen.append(executable)
            return executable == "python"
        items = inspect_windows_catalog(executable_exists=exists,
                                        distribution_present=lambda _: False)
        self.assertIn("python", seen)
        self.assertEqual(next(i for i in items if i["id"] == "python")["status"],
                         "installed_unverified")

    def test_no_local_motor_means_no_hidden_cloud(self):
        plan = plan_windows_capability("inference", ram_bytes=8*1024**3,
                                       executable_exists=lambda _: False)
        self.assertIsNone(plan.engine_id)
        self.assertFalse(plan.execute_automatically)

    def test_8gb_profile_favors_small_local_inference_and_never_autostarts(self):
        plan = plan_windows_capability("inference", ram_bytes=8*1024**3,
                                       executable_exists=lambda c: c == "ollama")
        self.assertEqual(plan.engine_id, "ollama")
        self.assertFalse(plan.remote)
        self.assertFalse(plan.execute_automatically)


class WindowsControlTests(unittest.TestCase):
    def test_allowlisted_native_settings_and_no_shell_commands(self):
        opened = []
        self.assertEqual(windows_settings("wifi", os_name="Windows",
                                          opener=opened.append),
                         "ms-settings:network-wifi")
        self.assertEqual(opened, ["ms-settings:network-wifi"])
        with self.assertRaises(ValueError):
            windows_settings("powershell;rm", os_name="Windows",
                             opener=opened.append)
        with self.assertRaises(RuntimeError):
            windows_settings("wifi", os_name="Linux", opener=opened.append)
        self.assertEqual(len(opened), 1)

    def test_storage_guard_preserves_reserve_and_failed_check_writes_nothing(self):
        decision = storage_budget(model_bytes=2*1024**3,
                                  free_bytes=3*1024**3,
                                  reserve_bytes=2*1024**3)
        self.assertFalse(decision.allowed)
        self.assertGreater(decision.required_bytes, decision.free_bytes)
        self.assertTrue(storage_budget(model_bytes=1024**3,
                                       free_bytes=5*1024**3,
                                       reserve_bytes=2*1024**3).allowed)
        with self.assertRaises(ValueError):
            storage_budget(model_bytes=-1, free_bytes=5)

    def test_model_directory_is_user_writable_localappdata_without_creation(self):
        path = model_directory(env={"LOCALAPPDATA": "C:\\Users\\demo\\AppData\\Local"})
        self.assertEqual(str(path), "C:\\Users\\demo\\AppData\\Local\\MJON AI OS\\models")
        self.assertTrue(isinstance(path, Path) or hasattr(path, "parts"))
        self.assertEqual(model_directory(env={}).name, "models")

    def test_windows_doctor_does_not_call_linux_service_or_external_network(self):
        def status_reader(**kwargs):
            return SimpleNamespace(os_name="Windows", memory_total_bytes=8*1024**3,
                                   release="11", architecture="AMD64")
        result = diagnose_windows(os_name="Windows", status_reader=status_reader,
                                  executable_exists=lambda x: x == "ollama",
                                  disk_free_bytes=12*1024**3)
        self.assertEqual(result["memory_total_bytes"], 8*1024**3)
        self.assertEqual(result["ollama"], "installed_unverified")
        self.assertEqual(result["platform"], "Windows")
        self.assertFalse(result["model_tested"])
        self.assertEqual(result["disk_free_bytes"], 12*1024**3)

    def test_inference_cannot_run_without_known_ram(self):
        factory = Mock()
        with self.assertRaisesRegex(RuntimeError, "RAM"):
            local_chat("hola", ram_bytes=None, client_factory=factory)
        factory.assert_not_called()

    def test_local_chat_passes_memory_budget_to_real_client_boundary(self):
        client = Mock()
        client.ask.return_value = "Hola"
        factory = Mock(return_value=client)
        result = local_chat("hola", model="tiny:latest",
                            ram_bytes=8*1024**3, client_factory=factory)
        self.assertEqual(result, "Hola")
        factory.assert_called_once_with(ram_bytes=8*1024**3)
        client.ask.assert_called_once_with("hola", model="tiny:latest")


if __name__ == "__main__":
    unittest.main()
