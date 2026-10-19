from __future__ import annotations

from evdev import ecodes

KEY_ACTIONS = {
    ecodes.KEY_W: "W",
    ecodes.KEY_A: "A",
    ecodes.KEY_S: "S",
    ecodes.KEY_D: "D",
    ecodes.KEY_E: "E",
    ecodes.KEY_F: "F",
    ecodes.KEY_SPACE: "SPACE",
    ecodes.KEY_LEFTSHIFT: "SHIFT_L",
    ecodes.KEY_RIGHTSHIFT: "SHIFT_R",
    ecodes.KEY_1: "1",
    ecodes.KEY_2: "2",
    ecodes.KEY_3: "3",
    ecodes.KEY_4: "4",
    ecodes.KEY_5: "5",
}

BUTTON_ACTIONS = {
    ecodes.BTN_LEFT: "M1",
    ecodes.BTN_RIGHT: "M2",
    ecodes.BTN_MIDDLE: "M3",
    ecodes.BTN_SIDE: "M4",
    ecodes.BTN_BACK: "M4",
    ecodes.BTN_EXTRA: "M5",
    ecodes.BTN_FORWARD: "M5",
    ecodes.BTN_TASK: "M6",
}


def decode_event(event) -> tuple | None:
    """Translate one evdev event into a small renderer-independent action."""
    if event.type == ecodes.EV_KEY:
        name = KEY_ACTIONS.get(event.code)
        if name is not None:
            return ("key", name, event.value != 0)
        name = BUTTON_ACTIONS.get(event.code)
        if name is not None:
            return ("button", name, event.value != 0)
        return None

    if event.type == ecodes.EV_REL:
        if event.code == ecodes.REL_X:
            return ("motion", event.value, 0)
        if event.code == ecodes.REL_Y:
            return ("motion", 0, event.value)
        if event.code in (ecodes.REL_WHEEL, ecodes.REL_HWHEEL):
            if event.value > 0:
                return ("scroll", 1)
            if event.value < 0:
                return ("scroll", -1)
        return None

    return None
