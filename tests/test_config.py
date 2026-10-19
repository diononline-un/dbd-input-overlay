import tempfile
import unittest
from pathlib import Path

from dbd_overlay.config import Config, load_config


class ConfigTests(unittest.TestCase):
    def test_defaults_are_small_and_transparent(self):
        cfg = Config()

        self.assertTrue(cfg.show_numbers)
        self.assertTrue(cfg.show_mouse)
        self.assertGreaterEqual(cfg.scale, 0.8)
        self.assertLessEqual(cfg.panel_alpha, 0.4)

    def test_load_toml(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.toml"
            path.write_text(
                'output = "DP-2"\nscale = 1.2\npanel_alpha = 0.25\n'
                'accent = "#ff0000"\nshow_numbers = false\n',
                encoding="utf-8",
            )

            cfg = load_config(path)

            self.assertEqual(cfg.output, "DP-2")
            self.assertEqual(cfg.scale, 1.2)
            self.assertEqual(cfg.panel_alpha, 0.25)
            self.assertEqual(cfg.accent, "#ff0000")
            self.assertFalse(cfg.show_numbers)

    def test_missing_file_uses_defaults(self):
        cfg = load_config(Path("/nonexistent/dbd-overlay/config.toml"))

        self.assertEqual(cfg, Config())

    def test_values_are_clamped(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.toml"
            path.write_text("scale = 99\npanel_alpha = -1\nmargin = -5\n", encoding="utf-8")

            cfg = load_config(path)

            self.assertEqual(cfg.scale, 2.0)
            self.assertEqual(cfg.panel_alpha, 0.0)
            self.assertEqual(cfg.margin, 0)


if __name__ == "__main__":
    unittest.main()
