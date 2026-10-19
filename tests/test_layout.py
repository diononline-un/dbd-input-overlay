import unittest

from dbd_overlay.layout import build_layout


class LayoutTests(unittest.TestCase):
    def test_all_keys_fit_inside_card(self):
        layout = build_layout(scale=1.0, show_numbers=True, show_mouse=True)

        for name, rect in layout.keycaps.items():
            with self.subTest(key=name):
                self.assertGreaterEqual(rect.x, 0)
                self.assertGreaterEqual(rect.y, 0)
                self.assertLessEqual(rect.x + rect.w, layout.card_width)
                self.assertLessEqual(rect.y + rect.h, layout.card_height)

    def test_numbers_can_be_hidden(self):
        with_numbers = build_layout(scale=1.0, show_numbers=True, show_mouse=True)
        without = build_layout(scale=1.0, show_numbers=False, show_mouse=True)

        self.assertIn("1", with_numbers.keycaps)
        self.assertNotIn("1", without.keycaps)
        self.assertLess(without.window_height, with_numbers.window_height)

    def test_scale_applies_to_window(self):
        normal = build_layout(scale=1.0, show_numbers=True, show_mouse=True)
        small = build_layout(scale=0.8, show_numbers=True, show_mouse=True)

        self.assertAlmostEqual(small.window_width, normal.window_width * 0.8, places=3)
        self.assertAlmostEqual(small.window_height, normal.window_height * 0.8, places=3)

    def test_mouse_parts_fit_when_numbers_hidden(self):
        layout = build_layout(scale=1.0, show_numbers=False, show_mouse=True)

        parts = [layout.mouse_body, *layout.mouse_sides.values()]
        for rect in parts:
            with self.subTest(rect=rect):
                self.assertLessEqual(rect.y + rect.h, layout.card_height)

    def test_close_button_fits_inside_card(self):
        for numbers in (True, False):
            for mouse in (True, False):
                layout = build_layout(scale=1.0, show_numbers=numbers, show_mouse=mouse)
                rect = layout.close_button
                with self.subTest(numbers=numbers, mouse=mouse):
                    self.assertGreaterEqual(rect.x, 0)
                    self.assertLessEqual(rect.x + rect.w, layout.card_width)
                    self.assertGreaterEqual(rect.y, 0)
                    self.assertLessEqual(rect.y + rect.h, layout.card_height)

    def test_mouse_can_be_hidden(self):
        with_mouse = build_layout(scale=1.0, show_numbers=True, show_mouse=True)
        without = build_layout(scale=1.0, show_numbers=True, show_mouse=False)

        self.assertLess(without.window_width, with_mouse.window_width)


if __name__ == "__main__":
    unittest.main()
