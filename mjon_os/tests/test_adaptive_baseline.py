"""Essential 8 GiB Live hardware and security baseline contracts."""
from __future__ import annotations

from configparser import ConfigParser
from pathlib import Path
import unittest


BASE = Path(__file__).resolve().parents[1] / "live/config"
INCLUDES = BASE / "includes.chroot"


class AdaptiveSystemBaselineTests(unittest.TestCase):
    def test_low_memory_base_has_on_demand_zram_not_gpu_heavy_frameworks(self):
        list_file = BASE / "package-lists/mjon.list.chroot"
        packages = {line.strip() for line in list_file.read_text(encoding="utf-8").splitlines()
                    if line.strip() and not line.lstrip().startswith("#")}
        for package in ("systemd-zram-generator", "apparmor", "bubblewrap",
                        "sqlite3", "git", "pciutils", "usbutils"):
            self.assertIn(package, packages)
        for heavy in ("vllm", "sglang", "comfyui", "pytorch", "qdrant"):
            self.assertNotIn(heavy, packages)

    def test_zram_reserves_swap_but_is_not_falsely_claimed_to_expand_physical_ram(self):
        config = INCLUDES / "etc/systemd/zram-generator.conf"
        self.assertTrue(config.is_file())
        parser = ConfigParser(interpolation=None)
        parser.read(config, encoding="utf-8")
        self.assertIn("zram0", parser)
        self.assertEqual(parser["zram0"]["zram-size"], "min(ram / 4, 2048)")
        self.assertEqual(parser["zram0"]["compression-algorithm"], "lz4")

    def test_native_ai_center_is_packaged_not_read_from_source_checkout(self):
        from mjon_os.image_builder import _REQUIRED_WHEEL_FILES
        for name in ("mjon_os/ai_center.py", "mjon_os/ai_fabric.py",
                     "mjon_os/local_inference.py"):
            self.assertIn(name, _REQUIRED_WHEEL_FILES)


if __name__ == "__main__":
    unittest.main()
