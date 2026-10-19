import unittest

from evdev import InputEvent, ecodes

from dbd_overlay.events import decode_event


def key_event(code, value):
    return InputEvent(0, 0, ecodes.EV_KEY, code, value)


def rel_event(code, value):
    return InputEvent(0, 0, ecodes.EV_REL, code, value)


class KeyDecodeTests(unittest.TestCase):
    def test_wasd(self):
        self.assertEqual(decode_event(key_event(ecodes.KEY_W, 1)), ("key", "W", True))
        self.assertEqual(decode_event(key_event(ecodes.KEY_A, 0)), ("key", "A", False))

    def test_extra_keys(self):
        for code, name in (
            (ecodes.KEY_E, "E"),
            (ecodes.KEY_F, "F"),
            (ecodes.KEY_SPACE, "SPACE"),
            (ecodes.KEY_LEFTSHIFT, "SHIFT_L"),
            (ecodes.KEY_RIGHTSHIFT, "SHIFT_R"),
            (ecodes.KEY_1, "1"),
            (ecodes.KEY_5, "5"),
        ):
            with self.subTest(name=name):
                self.assertEqual(decode_event(key_event(code, 1)), ("key", name, True))

    def test_repeat_counts_as_pressed(self):
        self.assertEqual(decode_event(key_event(ecodes.KEY_W, 2)), ("key", "W", True))

    def test_unmapped_key_ignored(self):
        self.assertIsNone(decode_event(key_event(ecodes.KEY_Q, 1)))


class MouseDecodeTests(unittest.TestCase):
    def test_buttons(self):
        for code, name in (
            (ecodes.BTN_LEFT, "M1"),
            (ecodes.BTN_RIGHT, "M2"),
            (ecodes.BTN_MIDDLE, "M3"),
            (ecodes.BTN_SIDE, "M4"),
            (ecodes.BTN_EXTRA, "M5"),
            (ecodes.BTN_BACK, "M4"),
            (ecodes.BTN_FORWARD, "M5"),
            (ecodes.BTN_TASK, "M6"),
        ):
            with self.subTest(name=name):
                self.assertEqual(decode_event(key_event(code, 1)), ("button", name, True))

    def test_motion(self):
        self.assertEqual(decode_event(rel_event(ecodes.REL_X, 7)), ("motion", 7, 0))
        self.assertEqual(decode_event(rel_event(ecodes.REL_Y, -3)), ("motion", 0, -3))

    def test_wheel(self):
        self.assertEqual(decode_event(rel_event(ecodes.REL_WHEEL, 1)), ("scroll", 1))
        self.assertEqual(decode_event(rel_event(ecodes.REL_WHEEL, -1)), ("scroll", -1))


if __name__ == "__main__":
    unittest.main()
