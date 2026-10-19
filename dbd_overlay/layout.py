from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Rect:
    x: float
    y: float
    w: float
    h: float


@dataclass(frozen=True)
class Layout:
    scale: float
    card_width: float
    card_height: float
    window_width: float
    window_height: float
    keycaps: dict[str, Rect]
    mouse_body: Rect | None
    mouse_sides: dict[str, Rect]
    compass_center: tuple[float, float]
    compass_radius: float


PAD = 10.0
KEY = 20.0
GAP = 4.0
NUM_W = 18.0
NUM_H = 14.0
NUM_GAP = 3.0
NUM_ROW_GAP = 5.0
SHIFT_W = 38.0
SPACE_W = 54.0
MOUSE_W = 48.0
MOUSE_GAP = 10.0
SHADOW = 6.0


def build_layout(scale: float = 1.0, show_numbers: bool = True, show_mouse: bool = True) -> Layout:
    left_width = KEY + GAP + KEY + GAP + SHIFT_W + GAP + SPACE_W
    card_width = PAD * 2 + left_width
    if show_mouse:
        card_width += MOUSE_GAP + MOUSE_W

    y = PAD
    keycaps: dict[str, Rect] = {}

    if show_numbers:
        for index, label in enumerate(("1", "2", "3", "4", "5")):
            x = PAD + index * (NUM_W + NUM_GAP)
            keycaps[label] = Rect(x, y, NUM_W, NUM_H)
        y += NUM_H + NUM_ROW_GAP

    w_y = y
    keycaps["W"] = Rect(PAD + (KEY * 3 + GAP * 2 - KEY) / 2, w_y, KEY, KEY)
    y += KEY + GAP

    for index, label in enumerate(("A", "S", "D")):
        keycaps[label] = Rect(PAD + index * (KEY + GAP), y, KEY, KEY)
    y += KEY + GAP

    keycaps["E"] = Rect(PAD, y, KEY, KEY)
    keycaps["F"] = Rect(PAD + KEY + GAP, y, KEY, KEY)
    keycaps["SHIFT"] = Rect(PAD + (KEY + GAP) * 2, y, SHIFT_W, KEY)
    keycaps["SPACE"] = Rect(PAD + (KEY + GAP) * 2 + SHIFT_W + GAP, y, SPACE_W, KEY)
    y += KEY

    card_height = y + PAD

    mouse_body = None
    mouse_sides: dict[str, Rect] = {}
    compass_center = (0.0, 0.0)
    compass_radius = 0.0
    if show_mouse:
        mouse_x = PAD + left_width + MOUSE_GAP
        compass_radius = 13.0
        compass_center = (mouse_x + MOUSE_W / 2, PAD + compass_radius + 2)
        body_x = mouse_x + (MOUSE_W - 24) / 2
        mouse_body = Rect(body_x, PAD + 34, 24, 32)
        mouse_sides = {
            "M4": Rect(mouse_x + 1, PAD + 70, 18, 10),
            "M5": Rect(mouse_x + MOUSE_W - 19, PAD + 70, 18, 10),
        }

    if scale != 1.0:
        def scaled(rect: Rect) -> Rect:
            return Rect(rect.x * scale, rect.y * scale, rect.w * scale, rect.h * scale)

        keycaps = {name: scaled(rect) for name, rect in keycaps.items()}
        if mouse_body is not None:
            mouse_body = scaled(mouse_body)
        mouse_sides = {name: scaled(rect) for name, rect in mouse_sides.items()}
        compass_center = (compass_center[0] * scale, compass_center[1] * scale)
        compass_radius *= scale
        card_width *= scale
        card_height *= scale

    return Layout(
        scale=scale,
        card_width=card_width,
        card_height=card_height,
        window_width=card_width + SHADOW * 2 * scale,
        window_height=card_height + SHADOW * 2 * scale,
        keycaps=keycaps,
        mouse_body=mouse_body,
        mouse_sides=mouse_sides,
        compass_center=compass_center,
        compass_radius=compass_radius,
    )
