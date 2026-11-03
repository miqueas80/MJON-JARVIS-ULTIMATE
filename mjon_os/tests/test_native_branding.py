"""One OS brand for the native distribution; no global change to vanilla Dodaios."""
from __future__ import annotations

import os
import subprocess
import sys
import unittest


class BrandIdentityTests(unittest.TestCase):
    def _product_name(self, native: bool) -> str:
        environment = dict(os.environ)
        environment.pop("MJON_NATIVE_OS", None)
        if native:
            environment["MJON_NATIVE_OS"] = "1"
        output = subprocess.run(
            [sys.executable, "-c", "from dodaios.core.branding import PRODUCT_NAME; print(PRODUCT_NAME)"],
            env=environment, capture_output=True, text=True, check=True, timeout=8,
        )
        return output.stdout.strip()

    def test_distributed_native_agent_uses_mjon_brand(self) -> None:
        self.assertEqual(self._product_name(native=True), "MJON AI OS")

    def test_upstream_compatibility_without_native_boot(self) -> None:
        self.assertEqual(self._product_name(native=False), "Dodaios")


if __name__ == "__main__":
    unittest.main()
