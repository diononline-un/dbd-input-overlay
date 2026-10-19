import unittest

from dbd_overlay.state import OverlayState


class KeyStateTests(unittest.TestCase):
    def test_press_and_release_key(self):
        state = OverlayState()

        state.press_key("W", "keyboard")
        self.assertTrue(state.is_active("W"))

        state.release_key("W", "keyboard")
        self.assertFalse(state.is_active("W"))

    def test_key_from_two_devices_stays_active_until_both_release(self):
        state = OverlayState()

        state.press_key("W", "keyboard-a")
        state.press_key("W", "keyboard-b")
        state.release_key("W", "keyboard-a")
        self.assertTrue(state.is_active("W"))

        state.release_key("W", "keyboard-b")
        self.assertFalse(state.is_active("W"))

    def test_repeated_press_is_idempotent(self):
        state = OverlayState()

        state.press_key("W", "keyboard")
        state.press_key("W", "keyboard")
        state.release_key("W", "keyboard")

        self.assertFalse(state.is_active("W"))

    def test_shift_either_side_counts_as_shift(self):
        state = OverlayState()

        state.press_key("SHIFT_L", "keyboard")
        self.assertTrue(state.is_active("SHIFT"))

        state.release_key("SHIFT_L", "keyboard")
        state.press_key("SHIFT_R", "keyboard")
        self.assertTrue(state.is_active("SHIFT"))

    def test_unknown_key_is_ignored(self):
        state = OverlayState()

        state.press_key("NOPE", "keyboard")

        self.assertEqual(state.snapshot().keys, frozenset())


class MouseStateTests(unittest.TestCase):
    def test_side_buttons_are_tracked(self):
        state = OverlayState()

        state.press_button("M4", "mouse")
        state.press_button("M5", "mouse")

        self.assertTrue(state.is_active("M4"))
        self.assertTrue(state.is_active("M5"))

    def test_motion_is_smoothed_and_decays(self):
        state = OverlayState()

        state.add_motion(120, 0)
        state.update(1 / 60)
        self.assertGreater(state.motion[0], 0)

        for _ in range(30):
            state.update(0.1)

        self.assertLess(abs(state.motion[0]), 0.5)
        self.assertEqual(state.motion[1], 0)

    def test_diagonal_motion_keeps_direction(self):
        state = OverlayState()

        state.add_motion(10, 10)
        state.update(1 / 60)

        self.assertAlmostEqual(state.motion[0], state.motion[1])

    def test_scroll_expires(self):
        state = OverlayState()

        state.add_scroll(1)
        state.update(0.05)
        self.assertEqual(state.snapshot().scroll, 1)

        state.update(0.4)
        self.assertEqual(state.snapshot().scroll, 0)

    def test_snapshot_is_a_copy(self):
        state = OverlayState()
        state.press_key("W", "keyboard")

        snap = state.snapshot()
        state.release_key("W", "keyboard")

        self.assertIn("W", snap.keys)
        self.assertNotIn("W", state.snapshot().keys)


class VisibilityTests(unittest.TestCase):
    def test_toggle_visibility(self):
        state = OverlayState()

        self.assertTrue(state.snapshot().visible)
        state.toggle_visible()
        self.assertFalse(state.snapshot().visible)
        state.toggle_visible()
        self.assertTrue(state.snapshot().visible)


if __name__ == "__main__":
    unittest.main()
