"""Read-only diagnostics for the USB Live environment."""
from __future__ import annotations

import subprocess
import unittest
from unittest.mock import Mock

from mjon_os.doctor import diagnose, parse_memtotal


class MemoryParsingTests(unittest.TestCase):
    def test_linux_memory_is_bytes(self):
        self.assertEqual(parse_memtotal("MemTotal:        8192000 kB\nMemFree: 5000 kB\n"), 8192000 * 1024)

    def test_broken_meminfo_is_unknown(self):
        for raw in ("", "MemFree: 1234 kB", "MemTotal: xyz kB", "MemTotal: -1 kB"):
            with self.subTest(raw=raw):
                self.assertIsNone(parse_memtotal(raw))


class NativeDoctorTests(unittest.TestCase):
    def test_healthy_kde_session(self):
        runner = Mock(return_value=subprocess.CompletedProcess([], 0, "active\n", ""))
        report = diagnose(
            os_name="Linux",
            env={"XDG_CURRENT_DESKTOP": "KDE", "XDG_SESSION_TYPE": "wayland", "WAYLAND_DISPLAY": "wayland-0"},
            meminfo="MemTotal: 8192000 kB\n",
            runner=runner,
            euid=1000,
        )
        self.assertEqual(report["system"], "Linux")
        self.assertEqual(report["checks"]["desktop"], "ok")
        self.assertEqual(report["checks"]["session"], "ok")
        self.assertEqual(report["checks"]["ram"], "ok")
        self.assertEqual(report["checks"]["privilege"], "ok")
        self.assertEqual(report["checks"]["jarvis_service"], "ok")
        self.assertEqual(runner.call_args.kwargs["timeout"], 3)
        self.assertEqual(runner.call_args.args[0], ["systemctl", "--user", "is-active", "mjon-jarvis.service"])

    def test_degraded_headless_system_returns_no_exceptions(self):
        runner = Mock(side_effect=FileNotFoundError("systemctl missing"))
        report = diagnose(os_name="Linux", env={}, meminfo=None, runner=runner, euid=1000)
        self.assertEqual(report["checks"]["desktop"], "unavailable")
        self.assertEqual(report["checks"]["session"], "unavailable")
        self.assertEqual(report["checks"]["ram"], "unknown")
        self.assertEqual(report["checks"]["jarvis_service"], "unavailable")

    def test_root_context_reports_warning(self):
        runner = Mock(return_value=subprocess.CompletedProcess([], 3, "inactive\n", ""))
        report = diagnose(os_name="Linux", env={"XDG_CURRENT_DESKTOP": "KDE"}, meminfo="MemTotal: 4000000 kB\n", runner=runner, euid=0)
        self.assertEqual(report["checks"]["privilege"], "warning")
        self.assertEqual(report["checks"]["ram"], "warning")
        self.assertEqual(report["checks"]["jarvis_service"], "unavailable")

    def test_non_linux_does_not_call_systemd(self):
        runner = Mock()
        report = diagnose(os_name="Windows", env={}, meminfo=None, runner=runner, euid=None)
        self.assertEqual(report["checks"]["jarvis_service"], "not_applicable")
        runner.assert_not_called()

    def test_timeout_is_reported_not_raised(self):
        runner = Mock(side_effect=subprocess.TimeoutExpired(["systemctl"], 3))
        report = diagnose(os_name="Linux", env={"XDG_CURRENT_DESKTOP": "KDE"}, meminfo=None, runner=runner, euid=1000)
        self.assertEqual(report["checks"]["jarvis_service"], "unavailable")


if __name__ == "__main__":
    unittest.main()
