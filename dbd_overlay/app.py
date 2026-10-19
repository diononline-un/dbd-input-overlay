from __future__ import annotations

import argparse
import ctypes
import os
import queue
import signal
import sys
import time
from pathlib import Path

_LAYER_SHELL_ERROR: str | None = None
try:
    ctypes.CDLL("libgtk4-layer-shell.so")
except OSError as exc:
    _LAYER_SHELL_ERROR = str(exc)

import cairo  # noqa: E402
import gi  # noqa: E402

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")

from gi.repository import Gdk, GLib, Gtk  # noqa: E402

Gtk4LayerShell = None
try:
    gi.require_version("Gtk4LayerShell", "1.0")
    from gi.repository import Gtk4LayerShell  # type: ignore[no-redef]  # noqa: E402
except (ValueError, ImportError) as exc:
    _LAYER_SHELL_ERROR = _LAYER_SHELL_ERROR or str(exc)

from . import __version__  # noqa: E402
from .config import Config, load_config  # noqa: E402
from .demo import DemoSource  # noqa: E402
from .devices import InputReader, discover_devices  # noqa: E402
from .layout import build_layout  # noqa: E402
from .render import OverlayRenderer  # noqa: E402
from .state import OverlayState  # noqa: E402

DEFAULT_CONFIG = Path.home() / ".config" / "dbd-input-overlay" / "config.toml"


def _debug(message: str) -> None:
    if os.environ.get("DBD_OVERLAY_DEBUG"):
        print(f"dbd-input-overlay: {message}", file=sys.stderr, flush=True)


class DbdOverlayApp:
    def __init__(self, config: Config, demo: bool = False, quit_after: float | None = None) -> None:
        self.config = config
        self.demo = demo
        self.quit_after = quit_after
        self.state = OverlayState()
        self.reader: InputReader | None = None
        self.demo_source: DemoSource | None = None
        self.events: queue.Queue = queue.Queue()
        self.window: Gtk.Window | None = None
        self.area: Gtk.DrawingArea | None = None
        self.renderer: OverlayRenderer | None = None
        self._last_tick = time.monotonic()
        self._app = Gtk.Application(application_id="io.github.diononline.DbdInputOverlay")
        self._app.connect("activate", self._on_activate)
        self._app.connect("shutdown", self._on_shutdown)

    def run(self) -> int:
        if self.quit_after:
            GLib.timeout_add(int(self.quit_after * 1000), self._quit)
        GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGINT, self._quit)
        GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGTERM, self._quit)
        return self._app.run([])

    def _on_activate(self, app: Gtk.Application) -> None:
        _debug("activate")
        if self.window is not None:
            self.window.present()
            return

        display = Gdk.Display.get_default()
        if display is None:
            print("dbd-input-overlay: no Wayland display", file=sys.stderr)
            app.quit()
            return

        base_layout = build_layout(1.0, self.config.show_numbers, self.config.show_mouse)
        scaled_layout = build_layout(self.config.scale, self.config.show_numbers, self.config.show_mouse)

        window = Gtk.Window(application=app)
        window.add_css_class("dbd-overlay")
        window.set_title("dbd-input-overlay")
        window.set_decorated(False)
        window.set_resizable(False)
        window.set_can_focus(False)
        window.set_default_size(
            int(round(scaled_layout.window_width)),
            int(round(scaled_layout.window_height)),
        )

        area = Gtk.DrawingArea()
        area.set_content_width(int(round(scaled_layout.window_width)))
        area.set_content_height(int(round(scaled_layout.window_height)))
        area.set_draw_func(self._draw)
        window.set_child(area)

        provider = Gtk.CssProvider()
        provider.load_from_data(
            b"window.dbd-overlay { background: transparent; }"
            b"drawingarea { background: transparent; }"
        )
        Gtk.StyleContext.add_provider_for_display(
            display, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        Gtk4LayerShell.init_for_window(window)
        Gtk4LayerShell.set_namespace(window, "dbd-input-overlay")
        Gtk4LayerShell.set_layer(window, Gtk4LayerShell.Layer.OVERLAY)
        Gtk4LayerShell.set_anchor(window, Gtk4LayerShell.Edge.TOP, True)
        Gtk4LayerShell.set_anchor(window, Gtk4LayerShell.Edge.RIGHT, True)
        Gtk4LayerShell.set_margin(window, Gtk4LayerShell.Edge.TOP, self.config.margin)
        Gtk4LayerShell.set_margin(window, Gtk4LayerShell.Edge.RIGHT, self.config.margin)
        Gtk4LayerShell.set_exclusive_zone(window, -1)
        Gtk4LayerShell.set_keyboard_mode(window, Gtk4LayerShell.KeyboardMode.NONE)

        monitor = self._find_monitor(display, self.config.output)
        if monitor is not None:
            Gtk4LayerShell.set_monitor(window, monitor)
        elif self.config.output:
            print(
                f"dbd-input-overlay: monitor {self.config.output!r} not found, using default",
                file=sys.stderr,
            )

        self.window = window
        self.area = area
        self.renderer = OverlayRenderer(self.state, self.config, base_layout, self.config.scale)

        _debug(
            f"present window {int(scaled_layout.window_width)}x"
            f"{int(scaled_layout.window_height)} on {self.config.output or 'default'}"
        )
        window.present()
        GLib.idle_add(self._apply_click_through)
        _debug("window presented")

        if self.demo:
            self.demo_source = DemoSource()
        else:
            self.reader = InputReader(
                self.events,
                keyboard_hint=self.config.keyboard_device,
                mouse_hint=self.config.mouse_device,
            )
            self.reader.start()

        self._last_tick = time.monotonic()
        GLib.timeout_add(16, self._tick)

    def _find_monitor(self, display: Gdk.Display, name: str) -> Gdk.Monitor | None:
        if not name:
            return None
        monitors = display.get_monitors()
        for index in range(monitors.get_n_items()):
            monitor = monitors.get_item(index)
            connector = monitor.get_connector()
            model = monitor.get_model()
            if name in (connector, model):
                return monitor
        return None

    def _apply_click_through(self) -> bool:
        if self.window is None:
            return GLib.SOURCE_REMOVE
        surface = self.window.get_surface()
        if surface is None:
            return GLib.SOURCE_CONTINUE
        surface.set_input_region(cairo.Region())
        surface.set_opaque_region(cairo.Region())
        _debug("click-through and transparency applied")
        return GLib.SOURCE_REMOVE

    def _draw(self, area: Gtk.DrawingArea, cr: cairo.Context, width: int, height: int) -> None:
        if self.renderer is not None:
            self.renderer.draw(area, cr, width, height)

    def _tick(self) -> bool:
        now = time.monotonic()
        dt = min(0.1, now - self._last_tick)
        self._last_tick = now

        self._drain_events()
        if self.demo_source is not None:
            self.demo_source.tick(dt, self.state)
        self.state.update(dt)
        if self.renderer is not None:
            self.renderer.tick(dt)
        if self.area is not None:
            self.area.queue_draw()
        return GLib.SOURCE_CONTINUE

    def _drain_events(self) -> None:
        while True:
            try:
                source, action = self.events.get_nowait()
            except queue.Empty:
                return
            kind = action[0]
            if kind == "key":
                if action[2]:
                    self.state.press_key(action[1], source)
                else:
                    self.state.release_key(action[1], source)
            elif kind == "button":
                if action[2]:
                    self.state.press_button(action[1], source)
                else:
                    self.state.release_button(action[1], source)
            elif kind == "motion":
                self.state.add_motion(action[1], action[2])
            elif kind == "scroll":
                self.state.add_scroll(action[1])

    def _quit(self) -> bool:
        if self.reader is not None:
            self.reader.stop()
        self._app.quit()
        return GLib.SOURCE_REMOVE

    def _on_shutdown(self, app: Gtk.Application) -> None:
        if self.reader is not None:
            self.reader.stop()
            self.reader.join(timeout=1.0)


def list_devices() -> int:
    selection, inventory = discover_devices()
    chosen = {device.path for device in selection.keyboards}
    if selection.pointer is not None:
        chosen.add(selection.pointer.path)

    if not inventory:
        print("No readable input devices found.")
        print("Check: id -nG (needs input), or the device ACL in /dev/input/event*.")
        return 1

    for path, name, kind in inventory:
        marker = "*" if path in chosen else " "
        print(f"{marker} {kind:8} {path}  {name}")
    print("\n* = used by the overlay")
    selection.close()
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="dbd-input-overlay",
        description="Small transparent input overlay for Dead by Daylight on KDE Wayland.",
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output", help="Monitor connector, for example DP-1 or DP-2")
    parser.add_argument("--scale", type=float, help="Overlay scale, default 1.0")
    parser.add_argument("--margin", type=int, help="Distance from the screen corner in pixels")
    parser.add_argument("--panel-alpha", type=float, help="Panel opacity from 0.0 to 1.0")
    parser.add_argument("--accent", help="Pressed-key accent color, for example #c2414b")
    parser.add_argument("--no-numbers", action="store_true", help="Hide the 1-5 row")
    parser.add_argument("--no-mouse", action="store_true", help="Hide the mouse cluster")
    parser.add_argument("--keyboard", default="", help="Only use keyboards whose name contains this")
    parser.add_argument("--mouse", default="", help="Only use pointers whose name contains this")
    parser.add_argument("--demo", action="store_true", help="Show scripted input instead of evdev input")
    parser.add_argument("--quit-after", type=float, help="Quit after N seconds, useful for screenshots")
    parser.add_argument("--list-devices", action="store_true", help="List input devices and exit")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.list_devices:
        return list_devices()

    if Gtk4LayerShell is None:
        print("dbd-input-overlay: gtk4-layer-shell is missing.", file=sys.stderr)
        print("Install it with: sudo pacman -S gtk4-layer-shell", file=sys.stderr)
        if _LAYER_SHELL_ERROR:
            print(f"Details: {_LAYER_SHELL_ERROR}", file=sys.stderr)
        return 1

    try:
        config = load_config(args.config)
    except ValueError as exc:
        print(f"dbd-input-overlay: {exc}", file=sys.stderr)
        return 2

    if args.output is not None:
        config.output = args.output
    if args.scale is not None:
        config.scale = max(0.6, min(2.0, args.scale))
    if args.margin is not None:
        config.margin = max(0, args.margin)
    if args.panel_alpha is not None:
        config.panel_alpha = max(0.0, min(1.0, args.panel_alpha))
    if args.accent is not None:
        config.accent = args.accent
    if args.no_numbers:
        config.show_numbers = False
    if args.no_mouse:
        config.show_mouse = False
    if args.keyboard:
        config.keyboard_device = args.keyboard
    if args.mouse:
        config.mouse_device = args.mouse

    _debug("starting GTK application")
    app = DbdOverlayApp(config, demo=args.demo, quit_after=args.quit_after)
    return app.run()
