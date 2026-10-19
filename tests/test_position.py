import unittest

from dbd_overlay.position import ANCHORS, anchor_origin


class AnchorOriginTests(unittest.TestCase):
    def setUp(self):
        self.monitor = (2560, 1440)
        self.window = (234, 119)
        self.margin = 16

    def test_all_nine_anchors(self):
        width, height = self.monitor
        win_w, win_h = self.window
        margin = self.margin
        center_x = round((width - win_w) / 2)
        center_y = round((height - win_h) / 2)
        expected = {
            "top-left": (margin, margin),
            "top-center": (center_x, margin),
            "top-right": (width - win_w - margin, margin),
            "center-left": (margin, center_y),
            "center": (center_x, center_y),
            "center-right": (width - win_w - margin, center_y),
            "bottom-left": (margin, height - win_h - margin),
            "bottom-center": (center_x, height - win_h - margin),
            "bottom-right": (width - win_w - margin, height - win_h - margin),
        }

        for anchor, position in expected.items():
            with self.subTest(anchor=anchor):
                self.assertEqual(
                    anchor_origin(anchor, width, height, win_w, win_h, margin),
                    position,
                )

    def test_unknown_anchor_falls_back_to_top_right(self):
        self.assertEqual(
            anchor_origin("diagonal", 2560, 1440, 234, 119, 16),
            (2310, 16),
        )

    def test_large_window_is_clamped_to_origin(self):
        self.assertEqual(anchor_origin("center", 100, 100, 400, 300, 0), (0, 0))

    def test_anchor_order_has_nine_entries(self):
        self.assertEqual(len(ANCHORS), 9)
        self.assertEqual(ANCHORS[0], "top-left")
        self.assertEqual(ANCHORS[-1], "bottom-right")


if __name__ == "__main__":
    unittest.main()
