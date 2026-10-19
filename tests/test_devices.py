import unittest

from evdev import ecodes

from dbd_overlay.devices import is_keyboard_caps, is_pointer_caps, is_virtual_name, pointer_score


def caps(keys=(), rels=()):
    return {ecodes.EV_KEY: list(keys), ecodes.EV_REL: list(rels)}


class CapsTests(unittest.TestCase):
    def test_wasd_keyboard(self):
        self.assertTrue(
            is_keyboard_caps(
                caps([ecodes.KEY_W, ecodes.KEY_A, ecodes.KEY_S, ecodes.KEY_D])
            )
        )

    def test_partial_keyboard_is_rejected(self):
        self.assertFalse(
            is_keyboard_caps(caps([ecodes.KEY_W, ecodes.KEY_A, ecodes.KEY_S]))
        )

    def test_pointer_needs_button_and_axes(self):
        self.assertTrue(
            is_pointer_caps(caps([ecodes.BTN_LEFT], [ecodes.REL_X, ecodes.REL_Y]))
        )
        self.assertFalse(is_pointer_caps(caps([ecodes.BTN_LEFT], [ecodes.REL_X])))

    def test_virtual_names(self):
        self.assertTrue(is_virtual_name("ydotoold virtual device"))
        self.assertTrue(is_virtual_name("some virtual keyboard"))
        self.assertFalse(is_virtual_name("Keychron Keychron V5"))

    def test_real_mouse_scores_higher_than_keyboard_mouse_node(self):
        keychron = caps(
            [ecodes.BTN_LEFT, ecodes.BTN_RIGHT, ecodes.BTN_MIDDLE],
            [ecodes.REL_X, ecodes.REL_Y],
        )
        receiver = caps(
            [
                ecodes.BTN_LEFT,
                ecodes.BTN_RIGHT,
                ecodes.BTN_MIDDLE,
                ecodes.BTN_SIDE,
                ecodes.BTN_EXTRA,
                ecodes.BTN_BACK,
                ecodes.BTN_FORWARD,
            ],
            [ecodes.REL_X, ecodes.REL_Y],
        )

        self.assertGreater(pointer_score("YJX-CHIP USB Receiver Mouse", receiver), pointer_score("Keychron Keychron V5 Mouse", keychron))


if __name__ == "__main__":
    unittest.main()
