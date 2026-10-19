from __future__ import annotations

import queue
import selectors
import threading
import time

import evdev
from evdev import InputDevice, ecodes

from .events import decode_event


def is_keyboard_caps(caps: dict) -> bool:
    keys = set(caps.get(ecodes.EV_KEY, ()))
    return {ecodes.KEY_W, ecodes.KEY_A, ecodes.KEY_S, ecodes.KEY_D}.issubset(keys)


def is_pointer_caps(caps: dict) -> bool:
    keys = set(caps.get(ecodes.EV_KEY, ()))
    rels = set(caps.get(ecodes.EV_REL, ()))
    return ecodes.BTN_LEFT in keys and {ecodes.REL_X, ecodes.REL_Y}.issubset(rels)


def is_virtual_name(name: str) -> bool:
    lowered = name.lower()
    return "virtual" in lowered or "ydotoold" in lowered or "uinput" in lowered


def pointer_score(name: str, caps: dict) -> int:
    buttons = [code for code in caps.get(ecodes.EV_KEY, ()) if 0x110 <= code <= 0x11F]
    score = len(buttons) * 100
    lowered = name.lower()
    if "receiver" in lowered:
        score += 10
    if "mouse" in lowered:
        score += 5
    return score


class DeviceSelection:
    def __init__(self, keyboards: list[InputDevice], pointer: InputDevice | None) -> None:
        self.keyboards = keyboards
        self.pointer = pointer

    @property
    def paths(self) -> tuple[str, ...]:
        paths = [device.path for device in self.keyboards]
        if self.pointer is not None:
            paths.append(self.pointer.path)
        return tuple(sorted(set(paths)))

    def close(self) -> None:
        for device in self.keyboards:
            device.close()
        if self.pointer is not None:
            self.pointer.close()


def discover_devices(
    keyboard_hint: str = "", mouse_hint: str = ""
) -> tuple[DeviceSelection, list[tuple[str, str, str]]]:
    keyboards: list[InputDevice] = []
    pointers: list[InputDevice] = []
    inventory: list[tuple[str, str, str]] = []
    opened: list[InputDevice] = []

    for path in evdev.list_devices():
        try:
            device = InputDevice(path)
        except (OSError, PermissionError):
            continue
        opened.append(device)
        caps = device.capabilities(absinfo=False)
        if is_virtual_name(device.name):
            continue
        if is_keyboard_caps(caps):
            keyboards.append(device)
            inventory.append((path, device.name, "keyboard"))
        if is_pointer_caps(caps):
            pointers.append(device)
            inventory.append((path, device.name, "pointer"))

    if keyboard_hint:
        matched = [d for d in keyboards if keyboard_hint.lower() in d.name.lower()]
        keyboards = matched or keyboards
    if mouse_hint:
        matched = [d for d in pointers if mouse_hint.lower() in d.name.lower()]
        pointers = matched or pointers

    pointer = max(pointers, key=lambda d: pointer_score(d.name, d.capabilities(absinfo=False)), default=None)
    keyboard_paths = {device.path for device in keyboards}
    if pointer is not None and pointer.path in keyboard_paths:
        # A combo device is already read through its keyboard fd. Registering the
        # same fd twice would fail and closing it twice would be unsafe.
        pointer = None

    selected = {d.path for d in keyboards}
    if pointer is not None:
        selected.add(pointer.path)
    for device in opened:
        if device.path not in selected:
            device.close()

    return DeviceSelection(keyboards, pointer), inventory


class InputReader(threading.Thread):
    """Reads all physical keyboards and one physical pointer via evdev."""

    def __init__(
        self,
        events: queue.Queue,
        keyboard_hint: str = "",
        mouse_hint: str = "",
    ) -> None:
        super().__init__(name="evdev-reader", daemon=True)
        self.events = events
        self.keyboard_hint = keyboard_hint
        self.mouse_hint = mouse_hint
        self._stop = threading.Event()
        self._selector: selectors.BaseSelector | None = None
        self._selection: DeviceSelection | None = None
        self._known_paths: set[str] = set()
        self._last_scan = 0.0
        self._warned_no_devices = False

    def run(self) -> None:
        while not self._stop.is_set():
            self._maybe_rebuild()
            if self._selector is None:
                self._stop.wait(1.0)
                continue

            try:
                ready = self._selector.select(0.5)
            except OSError:
                self._rebuild()
                continue

            for key, _ in ready:
                device = key.data
                try:
                    for event in device.read():
                        action = decode_event(event)
                        if action is not None:
                            self.events.put((device.path, action))
                except (BlockingIOError, OSError):
                    self._rebuild()
                    break

            now = time.monotonic()
            if now - self._last_scan > 3:
                self._last_scan = now
                try:
                    current = set(evdev.list_devices())
                except OSError:
                    current = set()
                if current != self._known_paths:
                    self._rebuild()

    def stop(self) -> None:
        self._stop.set()

    def _maybe_rebuild(self) -> None:
        if self._selector is None:
            self._rebuild()

    def _rebuild(self) -> None:
        if self._selector is not None:
            self._selector.close()
            self._selector = None
        if self._selection is not None:
            self._selection.close()
            self._selection = None

        try:
            selection, _ = discover_devices(self.keyboard_hint, self.mouse_hint)
        except OSError as exc:
            print(f"dbd-input-overlay: cannot read input devices: {exc}", flush=True)
            self._known_paths = set()
            return

        selector = selectors.DefaultSelector()
        for device in selection.keyboards:
            selector.register(device.fd, selectors.EVENT_READ, device)
        if selection.pointer is not None:
            selector.register(selection.pointer.fd, selectors.EVENT_READ, selection.pointer)

        self._selection = selection
        self._selector = selector
        self._known_paths = set(selection.paths)
        self._last_scan = time.monotonic()

        if not selection.keyboards and selection.pointer is None and not self._warned_no_devices:
            print(
                "dbd-input-overlay: no readable keyboard or mouse found. "
                "Check that you are in the input group or that the device ACL is set.",
                flush=True,
            )
            self._warned_no_devices = True
