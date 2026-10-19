from __future__ import annotations

import math
from dataclasses import dataclass

KEY_NAMES = frozenset(
    {"W", "A", "S", "D", "E", "F", "SPACE", "SHIFT_L", "SHIFT_R", "1", "2", "3", "4", "5"}
)
BUTTON_NAMES = frozenset({"M1", "M2", "M3", "M4", "M5", "M6"})


@dataclass(frozen=True)
class Snapshot:
    keys: frozenset[str]
    buttons: frozenset[str]
    motion: tuple[float, float]
    scroll: int
    visible: bool


class OverlayState:
    """Input state shared by the evdev reader and the renderer.

    Keys and buttons are reference-counted per source device. Some keyboards
    expose more than one event node, so the same key can arrive from two
    sources. Releasing one source must not clear the key while the other source
    still holds it.
    """

    def __init__(self, motion_tau: float = 0.16, scroll_hold: float = 0.28) -> None:
        self._key_sources: dict[str, set[str]] = {}
        self._button_sources: dict[str, set[str]] = {}
        self._motion = [0.0, 0.0]
        self._pending_motion = [0.0, 0.0]
        self._scroll = 0
        self._scroll_age = 0.0
        self._visible = True
        self._motion_tau = motion_tau
        self._scroll_hold = scroll_hold

    @property
    def motion(self) -> tuple[float, float]:
        return (self._motion[0], self._motion[1])

    def press_key(self, name: str, source: str = "default") -> None:
        if name not in KEY_NAMES:
            return
        self._key_sources.setdefault(name, set()).add(source)

    def release_key(self, name: str, source: str = "default") -> None:
        sources = self._key_sources.get(name)
        if sources is None:
            return
        sources.discard(source)
        if not sources:
            self._key_sources.pop(name, None)

    def press_button(self, name: str, source: str = "default") -> None:
        if name not in BUTTON_NAMES:
            return
        self._button_sources.setdefault(name, set()).add(source)

    def release_button(self, name: str, source: str = "default") -> None:
        sources = self._button_sources.get(name)
        if sources is None:
            return
        sources.discard(source)
        if not sources:
            self._button_sources.pop(name, None)

    def add_motion(self, dx: float, dy: float) -> None:
        self._pending_motion[0] += dx
        self._pending_motion[1] += dy

    def add_scroll(self, direction: int) -> None:
        if direction == 0:
            return
        self._scroll = 1 if direction > 0 else -1
        self._scroll_age = 0.0

    def update(self, dt: float) -> None:
        if dt <= 0:
            return

        if self._pending_motion[0] or self._pending_motion[1]:
            instant_x = self._pending_motion[0] / dt
            instant_y = self._pending_motion[1] / dt
            smoothing = 1.0 - math.exp(-dt / 0.03)
            self._motion[0] += (instant_x - self._motion[0]) * smoothing
            self._motion[1] += (instant_y - self._motion[1]) * smoothing
            self._pending_motion[0] = 0.0
            self._pending_motion[1] = 0.0
        else:
            decay = math.exp(-dt / self._motion_tau)
            self._motion[0] *= decay
            self._motion[1] *= decay

        self._scroll_age += dt
        if self._scroll_age > self._scroll_hold:
            self._scroll = 0

    def is_active(self, name: str) -> bool:
        if name == "SHIFT":
            return "SHIFT_L" in self._key_sources or "SHIFT_R" in self._key_sources
        return name in self._key_sources or name in self._button_sources

    def toggle_visible(self) -> None:
        self._visible = not self._visible

    def snapshot(self) -> Snapshot:
        return Snapshot(
            keys=frozenset(self._key_sources),
            buttons=frozenset(self._button_sources),
            motion=(self._motion[0], self._motion[1]),
            scroll=self._scroll,
            visible=self._visible,
        )
