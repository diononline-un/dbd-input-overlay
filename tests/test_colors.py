import unittest

from dbd_overlay.colors import mix_rgba, parse_hex_color


class ColorTests(unittest.TestCase):
    def test_parse_hex(self):
        r, g, b = parse_hex_color("#c2414b")

        self.assertAlmostEqual(r, 194 / 255)
        self.assertAlmostEqual(g, 65 / 255)
        self.assertAlmostEqual(b, 75 / 255)

    def test_parse_hex_without_hash(self):
        self.assertEqual(parse_hex_color("ffffff"), (1.0, 1.0, 1.0))

    def test_invalid_hex_uses_fallback(self):
        self.assertEqual(parse_hex_color("nope", (0.1, 0.2, 0.3)), (0.1, 0.2, 0.3))

    def test_mix_rgba(self):
        mixed = mix_rgba((1.0, 1.0, 1.0, 0.0), (0.0, 0.0, 0.0, 1.0), 0.5)

        self.assertEqual(mixed, (0.5, 0.5, 0.5, 0.5))


if __name__ == "__main__":
    unittest.main()
