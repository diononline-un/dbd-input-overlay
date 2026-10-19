from __future__ import annotations

import math

from .state import OverlayState


class DemoSource:
    """Small scripted input source so the overlay can be judged without DBD."""

    def __init__(self) -> None:
        self.time = 0.0
        self._last_second = 0

    def tick(self, dt: float, state: OverlayState) -> None:
        self.time += dt
        cycle = ("W", "A", "S", "D", "E", "F", "SPACE", "SHIFT_L", "1", "2", "3", "4", "5")
        active = {cycle[int(self.time / 0.55) % len(cycle)]}
        if int(self.time / 2.1) % 2 == 0:
            active.add("W")
        if int(self.time / 1.7) % 3 == 0:
            active.add("D")

        for key in cycle:
            if key in active:
                state.press_key(key, "demo")
            else:
                state.release_key(key, "demo")

        state.add_motion(
            1100.0 * math.cos(self.time * 2.4),
            800.0 * math.sin(self.time * 3.2),
        )

        buttons = ("M1", "M2", "M3", "M4", "M5")
        for index, button in enumerate(buttons):
            phase = int(self.time * 2.0 + index * 0.7) % 9
            if phase == 0:
                state.press_button(button, "demo")
            else:
                state.release_button(button, "demo")

        second = int(self.time)
        if second != self._last_second:
            self._last_second = second
            if second % 4 == 0:
                state.add_scroll(1)
            elif second % 4 == 2:
                state.add_scroll(-1)
