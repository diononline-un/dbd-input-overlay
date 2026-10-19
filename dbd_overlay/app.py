from __future__ import annotations

import argparse
import ctypes
import math
import os
import queue
import signal
import subprocess
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
from .colors import parse_hex_color  # noqa: E402
from .config import Config, load_config, save_config  # noqa: E402
from .demo import DemoSource  # noqa: E402
from .devices import InputReader, discover_devices  # noqa: E402
from .layout import SHADOW, build_layout  # noqa: E402
from .position import ANCHORS, anchor_origin  # noqa: E402
from .render import OverlayRenderer  # noqa: E402
from .settings import SettingsWindow  # noqa: E402
from .state import OverlayState  # noqa: E402

DEFAULT_CONFIG = Path.home() / ".config" / "dbd-input-overlay" / "config.toml"
CLOSE_PADDING = 4.0


def _debug(message: str) -> None:
    if os.environ.get("DBD_OVERLAY_DEBUG"):
        print(f"dbd-input-overlay: {message}", file=sys.stderr, flush=True)


def _active_output_name() -> str:
    for command in ("qdbus6", "qdbus"):
        try:
            result = subprocess.run(
                [command, "org.kde.KWin", "/KWin", "org.kde.KWin.activeOutputName"],
                capture_output=True,
                text=True,
                timeout=0.7,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
            continue
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    return ""


class DbdOverlayApp:
    def __init__(
        self,
        config: Config,
        config_path: Path,
        demo: bool = False,
        quit_after: float | None = None,
        no_settings: bool = False,
    ) -> None:
        self.config = config
        self.config_path = config_path
        self.demo = demo
        self.quit_after = quit_after
        self.no_settings = no_settings
        self.state = OverlayState()
        self.reader: InputReader | None = None
        self.demo_source = DemoSource() if demo else None
        self.events: queue.Queue = queue.Queue()
        self.window: Gtk.Window | None = None
        self.area: Gtk.DrawingArea | None = None
        self.renderer: OverlayRenderer | None = None
        self.settings: SettingsWindow | None = None
        self._layout = None
        self._last_tick = time.monotonic()
        self._runtime_started = False
        self._rebuild_source = 0
        self._save_source = 0
        self._hover_close = False
        self._css_installed = False
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
        display = Gdk.Display.get_default()
        if display is None:
            print("dbd-input-overlay: no Wayland display", file=sys.stderr)
            app.quit()
            return

        if self.window is None:
            self._ensure_runtime()
            if not self._create_overlay(app):
                app.quit()
                return
            if not self.no_settings:
                self._show_settings(app)
        else:
            self._show_settings(app)

    def _ensure_runtime(self) -> None:
        if self._runtime_started:
            return
        self._runtime_started = True
        if not self.demo:
            self.reader = InputReader(
                self.events,
                keyboard_hint=self.config.keyboard_device,
                mouse_hint=self.config.mouse_device,
            )
            self.reader.start()
        self._last_tick = time.monotonic()
        GLib.timeout_add(16, self._tick)

    def _create_overlay(self, app: Gtk.Application) -> bool:
        display = Gdk.Display.get_default()
        if display is None:
            return False

        self._install_overlay_css(display)
        base_layout = build_layout(1.0, self.config.show_numbers, self.config.show_mouse)
        scaled_layout = build_layout(self.config.scale, self.config.show_numbers, self.config.show_mouse)
        window_width = int(round(scaled_layout.window_width))
        window_height = int(round(scaled_layout.window_height))

        window = Gtk.Window(application=app)
        window.add_css_class("dbd-overlay")
        window.set_title("dbd-input-overlay")
        window.set_decorated(False)
        window.set_resizable(False)
        window.set_can_focus(False)
        window.set_default_size(window_width, window_height)

        area = Gtk.DrawingArea()
        area.set_content_width(window_width)
        area.set_content_height(window_height)
        area.set_draw_func(self._draw)
        window.set_child(area)

        Gtk4LayerShell.init_for_window(window)
        Gtk4LayerShell.set_namespace(window, "dbd-input-overlay")
        Gtk4LayerShell.set_layer(window, Gtk4LayerShell.Layer.OVERLAY)
        Gtk4LayerShell.set_anchor(window, Gtk4LayerShell.Edge.TOP, True)
        Gtk4LayerShell.set_anchor(window, Gtk4LayerShell.Edge.LEFT, True)
        Gtk4LayerShell.set_exclusive_zone(window, -1)
        Gtk4LayerShell.set_keyboard_mode(window, Gtk4LayerShell.KeyboardMode.NONE)

        monitor = self._resolve_monitor(display, self.config.output)
        if monitor is not None:
            Gtk4LayerShell.set_monitor(window, monitor)
            geometry = monitor.get_geometry()
            x, y = anchor_origin(
                self.config.anchor,
                geometry.width,
                geometry.height,
                window_width,
                window_height,
                self.config.margin,
            )
        else:
            if self.config.output:
                print(
                    f"dbd-input-overlay: monitor {self.config.output!r} not found, using default",
                    file=sys.stderr,
                )
            x = y = self.config.margin

        Gtk4LayerShell.set_margin(window, Gtk4LayerShell.Edge.LEFT, x)
        Gtk4LayerShell.set_margin(window, Gtk4LayerShell.Edge.TOP, y)

        self.window = window
        self.area = area
        self.renderer = OverlayRenderer(self.state, self.config, base_layout, self.config.scale)
        self._layout = base_layout

        motion = Gtk.EventControllerMotion()
        motion.connect("motion", self._on_pointer_motion)
        motion.connect("leave", self._on_pointer_leave)
        area.add_controller(motion)
        click = Gtk.GestureClick()
        click.connect("pressed", self._on_pointer_click)
        area.add_controller(click)

        _debug(
            f"present window {window_width}x{window_height} "
            f"on {monitor.get_connector() if monitor else 'default'} at {x},{y}"
        )
        window.present()
        GLib.idle_add(self._apply_input_region)
        return True

    def _install_overlay_css(self, display: Gdk.Display) -> None:
        if self._css_installed:
            return
        self._css_installed = True
        provider = Gtk.CssProvider()
        provider.load_from_data(
            b"window.dbd-overlay { background: transparent; }"
            b"drawingarea { background: transparent; }"
        )
        Gtk.StyleContext.add_provider_for_display(
            display, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    def _destroy_overlay(self) -> None:
        if self.window is not None:
            self.window.destroy()
        self.window = None
        self.area = None
        self.renderer = None
        self._layout = None
        self._hover_close = False

    def _rebuild_overlay(self) -> bool:
        self._rebuild_source = 0
        self._app.hold()
        try:
            self._destroy_overlay()
            self._create_overlay(self._app)
        finally:
            self._app.release()
        return GLib.SOURCE_REMOVE

    def _schedule_rebuild(self) -> None:
        if self._rebuild_source:
            GLib.source_remove(self._rebuild_source)
        self._rebuild_source = GLib.timeout_add(150, self._rebuild_overlay)

    def _close_hit_rect(self) -> tuple[float, float, float, float] | None:
        if self._layout is None:
            return None
        rect = self._layout.close_button
        scale = self.config.scale
        return (
            (SHADOW + rect.x - CLOSE_PADDING) * scale,
            (SHADOW + rect.y - CLOSE_PADDING) * scale,
            (rect.w + CLOSE_PADDING * 2) * scale,
            (rect.h + CLOSE_PADDING * 2) * scale,
        )

    def _apply_input_region(self) -> bool:
        if self.window is None:
            return GLib.SOURCE_REMOVE
        surface = self.window.get_surface()
        if surface is None:
            return GLib.SOURCE_CONTINUE
        hit = self._close_hit_rect()
        if hit is None:
            surface.set_input_region(cairo.Region())
        else:
            x, y, width, height = hit
            region = cairo.Region(
                cairo.RectangleInt(
                    math.floor(x),
                    math.floor(y),
                    math.ceil(width),
                    math.ceil(height),
                )
            )
            surface.set_input_region(region)
        surface.set_opaque_region(cairo.Region())
        _debug("input region restricted to close button")
        return GLib.SOURCE_REMOVE

    def _on_pointer_motion(self, controller: Gtk.EventControllerMotion, x: float, y: float) -> None:
        hit = self._close_hit_rect()
        hover = False
        if hit is not None:
            hx, hy, hw, hh = hit
            hover = hx <= x <= hx + hw and hy <= y <= hy + hh
        if hover != self._hover_close:
            self._hover_close = hover
            if self.renderer is not None:
                self.renderer.hover_close = hover
            if self.area is not None:
                self.area.queue_draw()

    def _on_pointer_leave(self, controller: Gtk.EventControllerMotion) -> None:
        if self._hover_close:
            self._hover_close = False
            if self.renderer is not None:
                self.renderer.hover_close = False
            if self.area is not None:
                self.area.queue_draw()

    def _on_pointer_click(
        self,
        gesture: Gtk.GestureClick,
        n_press: int,
        x: float,
        y: float,
    ) -> None:
        if gesture.get_current_button() != 1:
            return
        hit = self._close_hit_rect()
        if hit is None:
            return
        hx, hy, hw, hh = hit
        if hx <= x <= hx + hw and hy <= y <= hy + hh:
            self._quit()

    def _show_settings(self, app: Gtk.Application) -> None:
        display = Gdk.Display.get_default()
        if display is None:
            return
        if self.settings is None:
            monitor = self._resolve_monitor(display, self.config.output)
            self.settings = SettingsWindow(
                app,
                self.config,
                monitor,
                self._on_settings_change,
                lambda: self._quit(),
                self._monitor_names(display),
            )
        self.settings.present()

    def _on_settings_change(self, field: str) -> None:
        _debug(f"settings changed: {field}")
        if field in ("accent", "panel_alpha"):
            if self.renderer is not None:
                self.renderer.config = self.config
                self.renderer.accent = parse_hex_color(self.config.accent)
            if self.area is not None:
                self.area.queue_draw()
        else:
            self._schedule_rebuild()
        self._schedule_save()

    def _schedule_save(self) -> None:
        if self._save_source:
            GLib.source_remove(self._save_source)
        self._save_source = GLib.timeout_add(250, self._save_config)

    def _save_config(self) -> bool:
        self._save_source = 0
        try:
            save_config(self.config_path, self.config)
            _debug(f"saved config to {self.config_path}")
        except OSError as exc:
            print(f"dbd-input-overlay: config could not be saved: {exc}", file=sys.stderr)
        return GLib.SOURCE_REMOVE

    def _resolve_monitor(self, display: Gdk.Display, name: str) -> Gdk.Monitor | None:
        if name:
            monitor = self._find_monitor(display, name)
            if monitor is not None:
                return monitor
        else:
            active = _active_output_name()
            if active:
                monitor = self._find_monitor(display, active)
                if monitor is not None:
                    return monitor
        monitors = display.get_monitors()
        if monitors.get_n_items() > 0:
            return monitors.get_item(0)
        return None

    def _find_monitor(self, display: Gdk.Display, name: str) -> Gdk.Monitor | None:
        if not name:
            return None
        monitors = display.get_monitors()
        for index in range(monitors.get_n_items()):
            monitor = monitors.get_item(index)
            if name in (monitor.get_connector(), monitor.get_model()):
                return monitor
        return None

    def _monitor_names(self, display: Gdk.Display) -> list[str]:
        names: list[str] = []
        monitors = display.get_monitors()
        for index in range(monitors.get_n_items()):
            monitor = monitors.get_item(index)
            name = monitor.get_connector() or monitor.get_model() or f"Monitor {index + 1}"
            if name not in names:
                names.append(name)
        return names

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
        if self._save_source:
            GLib.source_remove(self._save_source)
            self._save_source = 0
            self._save_config()
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
    parser.add_argument("--anchor", choices=ANCHORS, help="Screen anchor, default top-right")
    parser.add_argument("--scale", type=float, help="Overlay scale, default 1.0")
    parser.add_argument("--margin", type=int, help="Distance from the screen edge in pixels")
    parser.add_argument("--panel-alpha", type=float, help="Panel opacity from 0.0 to 1.0")
    parser.add_argument("--accent", help="Pressed-key accent color, for example #c2414b")
    parser.add_argument("--no-numbers", action="store_true", help="Hide the 1-5 row")
    parser.add_argument("--no-mouse", action="store_true", help="Hide the mouse cluster")
    parser.add_argument("--no-settings", action="store_true", help="Start the overlay without the settings window")
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
    if args.anchor is not None:
        config.anchor = args.anchor
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
    app = DbdOverlayApp(
        config,
        args.config,
        demo=args.demo,
        quit_after=args.quit_after,
        no_settings=args.no_settings,
    )
    return app.run()
