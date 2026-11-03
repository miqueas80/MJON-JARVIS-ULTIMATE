import subprocess
import unittest
from unittest.mock import Mock
from mjon_jarvis.system_status import parse_total_memory, read_status


class MemoryParsingTests(unittest.TestCase):
    def test_valid_integer(self):
        self.assertEqual(parse_total_memory('8589934592\r\n'), 8589934592)

    def test_rejects_injected_or_malformed_text(self):
        for value in ('123\n456', '123; rm -rf /', '-1', '0', '18446744073709551616', '1.2'):
            with self.subTest(value=value):
                self.assertIsNone(parse_total_memory(value))

    def test_non_windows_does_not_spawn_process(self):
        runner = Mock()
        result = read_status(runner=runner, os_name='Linux')
        self.assertEqual(result.os_name, 'Linux')
        runner.assert_not_called()

    def test_windows_uses_bounded_read_only_query(self):
        runner = Mock(return_value=subprocess.CompletedProcess([], 0, '8589934592\n', ''))
        result = read_status(runner=runner, os_name='Windows')
        self.assertEqual(result.memory_total_bytes, 8589934592)
        kwargs = runner.call_args.kwargs
        self.assertEqual(kwargs['timeout'], 5)
        self.assertFalse(kwargs['shell'])
        self.assertFalse(kwargs['check'])

    def test_windows_timeout_degrades_gracefully(self):
        runner = Mock(side_effect=subprocess.TimeoutExpired('powershell', 5))
        self.assertIsNone(read_status(runner=runner, os_name='Windows').memory_total_bytes)
