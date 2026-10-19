from __future__ import annotations

import re
from collections.abc import Callable

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
gi.require_version("Gtk4LayerShell", "1.0")

from gi.repository import Gdk, GLib, Gtk  # noqa: E402
from gi.repository import Gtk4LayerShell  # noqa: E402

from .config import Config  # noqa: E402
from .position import ANCHORS, anchor_origin  # noqa: E402

WINDOW_WIDTH = 550
WINDOW_HEIGHT = 800

SWATCHES = (
    "#c2414b",
    "#e05a4f",
    "#e0a34b",
    "#d8d24a",
    "#58b368",
    "#4aa3c2",
    "#5b6ee0",
    "#a45ad8",
    "#d85aa3",
    "#f0f0f0",
)

ARROWS = {
    "top-left": "↖",
    "top-center": "↑",
    "top-right": "↗",
    "center-left": "←",
    "center": "·",
    "center-right": "→",
    "bottom-left": "↙",
    "bottom-center": "↓",
    "bottom-right": "↘",
}

HEX_RE = re.compile(r"^#[0-9a-fA-F]{6}$")


class SettingsWindow:
    def __init__(
        self,
        app: Gtk.Application,
        config: Config,
        monitor: Gdk.Monitor | None,
        on_change: Callable[[str], None],
        on_quit: Callable[[], None],
        monitor_names: list[str],
    ) -> None:
        self.app = app
        self.config = config
        self.monitor = monitor
        self.on_change = on_change
        self.on_quit = on_quit
        self.monitor_names = monitor_names
        self._updating = False
        self._anchor_buttons: dict[str, Gtk.ToggleButton] = {}
        self._swatch_buttons: list[tuple[str, Gtk.Button]] = []

        self.window = Gtk.Window(application=app)
        self.window.add_css_class("dbd-settings")
        self.window.set_title("DBD Input Overlay")
        self.window.set_default_size(WINDOW_WIDTH, WINDOW_HEIGHT)
        self.window.set_resizable(False)
        self.window.set_decorated(False)
        self.window.set_can_focus(True)
        self.window.set_hide_on_close(True)
        self.window.connect("close-request", self._on_close_request)
        keys = Gtk.EventControllerKey()
        keys.connect("key-pressed", self._on_key_pressed)
        self.window.add_controller(keys)

        self._install_css()
        self.window.set_child(self._build_content())
        self._init_layer_shell()
        self._load_controls()

    def present(self) -> None:
        Gtk4LayerShell.set_keyboard_mode(self.window, Gtk4LayerShell.KeyboardMode.EXCLUSIVE)
        self.window.present()
        GLib.idle_add(self._focus_first)

    def _focus_first(self) -> bool:
        self.monitor_dropdown.grab_focus()
        return GLib.SOURCE_REMOVE

    def hide(self) -> None:
        Gtk4LayerShell.set_keyboard_mode(self.window, Gtk4LayerShell.KeyboardMode.NONE)
        self.window.hide()

    def _on_close_request(self, window: Gtk.Window) -> bool:
        self.hide()
        return True

    def _on_key_pressed(
        self,
        controller: Gtk.EventControllerKey,
        keyval: int,
        keycode: int,
        state: Gdk.ModifierType,
    ) -> bool:
        if keyval == Gdk.KEY_Escape:
            self.hide()
            return True
        return False

    def _install_css(self) -> None:
        display = Gdk.Display.get_default()
        if display is None:
            return
        swatch_rules = "\n".join(
            f"button.swatch-{index} {{ background-color: {color}; }}"
            for index, color in enumerate(SWATCHES)
        )
        css = (
            "window.dbd-settings {"
            " background-color: rgba(18, 20, 26, 0.98);"
            " border-radius: 14px;"
            " border: 1px solid rgba(255, 255, 255, 0.14);"
            "}"
            ".dbd-title { font-size: 17px; font-weight: 700; }"
            ".dbd-section { font-size: 11px; font-weight: 700; opacity: 0.62; margin-top: 4px; }"
            ".dbd-hint { font-size: 11px; opacity: 0.52; }"
            "button.swatch { min-width: 26px; min-height: 26px; border-radius: 13px;"
            " padding: 0; border: 2px solid rgba(255, 255, 255, 0.18); }"
            "button.swatch.selected { border-color: #ffffff; }"
            "button.anchor { min-width: 44px; min-height: 34px; }"
            "button.anchor:checked {"
            " background-color: rgba(194, 65, 75, 0.45);"
            " border-color: rgba(194, 65, 75, 0.95);"
            "}"
            "scale slider { min-width: 18px; min-height: 18px; }"
            f"\n{swatch_rules}"
        )
        provider = Gtk.CssProvider()
        provider.load_from_data(css.encode("utf-8"))
        Gtk.StyleContext.add_provider_for_display(
            display, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    def _build_content(self) -> Gtk.Widget:
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        outer.set_margin_top(18)
        outer.set_margin_bottom(18)
        outer.set_margin_start(20)
        outer.set_margin_end(20)

        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        title = Gtk.Label(label="DBD Input Overlay", xalign=0)
        title.add_css_class("dbd-title")
        title.set_hexpand(True)
        header.append(title)
        close = Gtk.Button(label="×")
        close.add_css_class("flat")
        close.set_can_focus(False)
        close.set_tooltip_text("Einstellungen schließen")
        close.connect("clicked", lambda _button: self.hide())
        header.append(close)
        outer.append(header)

        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_vexpand(True)
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        scroll.set_child(content)
        outer.append(scroll)

        content.append(self._section("Monitor"))
        monitor_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.monitor_dropdown = Gtk.DropDown.new_from_strings(self._monitor_labels())
        self.monitor_dropdown.connect("notify::selected", self._on_monitor_changed)
        monitor_box.append(self.monitor_dropdown)
        hint = Gtk.Label(
            label="„Aktiver Monitor“ folgt dem Monitor mit dem aktiven Fenster.",
            xalign=0,
        )
        hint.add_css_class("dbd-hint")
        hint.set_wrap(True)
        monitor_box.append(hint)
        content.append(monitor_box)

        content.append(self._section("Position"))
        grid = Gtk.Grid(row_spacing=6, column_spacing=6, halign=Gtk.Align.CENTER)
        active_button = None
        for index, anchor in enumerate(ANCHORS):
            button = Gtk.ToggleButton(label=ARROWS[anchor])
            button.add_css_class("anchor")
            button.set_tooltip_text(anchor.replace("-", " "))
            if active_button is None:
                active_button = button
            else:
                button.set_group(active_button)
            button.connect("toggled", self._on_anchor_toggled, anchor)
            grid.attach(button, index % 3, index // 3, 1, 1)
            self._anchor_buttons[anchor] = button
        content.append(grid)

        margin_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        margin_label = Gtk.Label(label="Randabstand", xalign=0)
        margin_label.set_hexpand(True)
        self.margin_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 80, 1)
        self.margin_scale.set_draw_value(True)
        self.margin_scale.set_value_pos(Gtk.PositionType.RIGHT)
        self.margin_scale.set_digits(0)
        self.margin_scale.set_hexpand(True)
        self.margin_scale.connect("value-changed", self._on_margin_changed)
        margin_box.append(margin_label)
        margin_box.append(self.margin_scale)
        content.append(margin_box)

        content.append(self._section("Größe"))
        self.scale_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0.6, 2.0, 0.05)
        self.scale_scale.set_draw_value(True)
        self.scale_scale.set_value_pos(Gtk.PositionType.RIGHT)
        self.scale_scale.set_digits(2)
        self.scale_scale.set_hexpand(True)
        self.scale_scale.connect("value-changed", self._on_scale_changed)
        content.append(self.scale_scale)

        content.append(self._section("Farbe"))
        swatch_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        for index, color in enumerate(SWATCHES):
            button = Gtk.Button()
            button.add_css_class("swatch")
            button.add_css_class(f"swatch-{index}")
            button.set_tooltip_text(color)
            button.connect("clicked", self._on_swatch_clicked, color)
            swatch_box.append(button)
            self._swatch_buttons.append((color, button))
        content.append(swatch_box)

        hex_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        hex_label = Gtk.Label(label="Hex", xalign=0)
        hex_label.set_hexpand(True)
        self.hex_entry = Gtk.Entry()
        self.hex_entry.set_max_length(7)
        self.hex_entry.set_width_chars(9)
        self.hex_entry.set_placeholder_text("#c2414b")
        self.hex_entry.connect("changed", self._on_hex_changed)
        hex_box.append(hex_label)
        hex_box.append(self.hex_entry)
        content.append(hex_box)

        alpha_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        alpha_label = Gtk.Label(label="Panel-Deckkraft", xalign=0)
        alpha_label.set_hexpand(True)
        self.alpha_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
        self.alpha_scale.set_draw_value(True)
        self.alpha_scale.set_value_pos(Gtk.PositionType.RIGHT)
        self.alpha_scale.set_digits(0)
        self.alpha_scale.set_hexpand(True)
        self.alpha_scale.connect("value-changed", self._on_alpha_changed)
        alpha_box.append(alpha_label)
        alpha_box.append(self.alpha_scale)
        content.append(alpha_box)

        content.append(self._section("Anzeige"))
        content.append(self._switch_row("Zahlenreihe 1-5", "numbers"))
        content.append(self._switch_row("Mauscluster", "mouse"))

        footer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.status = Gtk.Label(label="Änderungen werden automatisch gespeichert.", xalign=0)
        self.status.add_css_class("dbd-hint")
        self.status.set_hexpand(True)
        footer.append(self.status)
        reset = Gtk.Button(label="Zurücksetzen")
        reset.connect("clicked", lambda _button: self._reset())
        footer.append(reset)
        quit_button = Gtk.Button(label="Beenden")
        quit_button.connect("clicked", lambda _button: self.on_quit())
        footer.append(quit_button)
        close_button = Gtk.Button(label="Schließen")
        close_button.connect("clicked", lambda _button: self.hide())
        footer.append(close_button)
        outer.append(footer)

        return outer

    def _section(self, title: str) -> Gtk.Label:
        label = Gtk.Label(label=title, xalign=0)
        label.add_css_class("dbd-section")
        return label

    def _switch_row(self, title: str, field: str) -> Gtk.Box:
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        label = Gtk.Label(label=title, xalign=0)
        label.set_hexpand(True)
        switch = Gtk.Switch()
        switch.connect("notify::active", self._on_switch_changed, field, switch)
        row.append(label)
        row.append(switch)
        if field == "numbers":
            self.numbers_switch = switch
        else:
            self.mouse_switch = switch
        return row

    def _monitor_labels(self) -> list[str]:
        labels = ["Aktiver Monitor"]
        for name in self.monitor_names:
            if name not in labels:
                labels.append(name)
        if self.config.output and self.config.output not in labels:
            labels.append(self.config.output)
        return labels

    def _init_layer_shell(self) -> None:
        Gtk4LayerShell.init_for_window(self.window)
        Gtk4LayerShell.set_namespace(self.window, "dbd-input-overlay-settings")
        Gtk4LayerShell.set_layer(self.window, Gtk4LayerShell.Layer.OVERLAY)
        Gtk4LayerShell.set_anchor(self.window, Gtk4LayerShell.Edge.TOP, True)
        Gtk4LayerShell.set_anchor(self.window, Gtk4LayerShell.Edge.LEFT, True)
        Gtk4LayerShell.set_exclusive_zone(self.window, -1)
        Gtk4LayerShell.set_keyboard_mode(self.window, Gtk4LayerShell.KeyboardMode.ON_DEMAND)
        if self.monitor is not None:
            Gtk4LayerShell.set_monitor(self.window, self.monitor)
            geometry = self.monitor.get_geometry()
            x, y = anchor_origin(
                "center",
                geometry.width,
                geometry.height,
                WINDOW_WIDTH,
                WINDOW_HEIGHT,
                0,
            )
            Gtk4LayerShell.set_margin(self.window, Gtk4LayerShell.Edge.LEFT, x)
            Gtk4LayerShell.set_margin(self.window, Gtk4LayerShell.Edge.TOP, y)

    def _load_controls(self) -> None:
        self._updating = True
        try:
            labels = self._monitor_labels()
            selected = 0 if not self.config.output else labels.index(self.config.output)
            self.monitor_dropdown.set_selected(selected)

            for anchor, button in self._anchor_buttons.items():
                button.set_active(anchor == self.config.anchor)

            self.margin_scale.set_value(self.config.margin)
            self.scale_scale.set_value(self.config.scale)
            self.alpha_scale.set_value(round(self.config.panel_alpha * 100))
            self.numbers_switch.set_active(self.config.show_numbers)
            self.mouse_switch.set_active(self.config.show_mouse)
            self.hex_entry.set_text(self.config.accent)
            self._select_swatch(self.config.accent)
        finally:
            self._updating = False

    def _on_monitor_changed(self, dropdown: Gtk.DropDown, _param) -> None:
        if self._updating:
            return
        selected = dropdown.get_selected()
        labels = self._monitor_labels()
        if selected < 0 or selected >= len(labels):
            return
        self.config.output = "" if selected == 0 else labels[selected]
        self.on_change("output")

    def _on_anchor_toggled(self, button: Gtk.ToggleButton, anchor: str) -> None:
        if self._updating or not button.get_active():
            return
        self.config.anchor = anchor
        self.on_change("anchor")

    def _on_margin_changed(self, scale: Gtk.Scale) -> None:
        if self._updating:
            return
        self.config.margin = int(round(scale.get_value()))
        self.on_change("margin")

    def _on_scale_changed(self, scale: Gtk.Scale) -> None:
        if self._updating:
            return
        self.config.scale = round(scale.get_value(), 2)
        self.on_change("scale")

    def _on_alpha_changed(self, scale: Gtk.Scale) -> None:
        if self._updating:
            return
        self.config.panel_alpha = round(scale.get_value() / 100.0, 2)
        self.on_change("panel_alpha")

    def _on_switch_changed(self, switch: Gtk.Switch, _param, field: str, widget: Gtk.Switch) -> None:
        if self._updating:
            return
        setattr(self.config, field, widget.get_active())
        self.on_change(field)

    def _on_swatch_clicked(self, _button: Gtk.Button, color: str) -> None:
        if self._updating:
            return
        self.config.accent = color
        self._updating = True
        try:
            self.hex_entry.set_text(color)
            self._select_swatch(color)
        finally:
            self._updating = False
        self.on_change("accent")

    def _on_hex_changed(self, entry: Gtk.Entry) -> None:
        if self._updating:
            return
        value = entry.get_text().strip()
        if not HEX_RE.fullmatch(value):
            return
        if value.lower() == self.config.accent.lower():
            return
        self.config.accent = value
        self._select_swatch(value)
        self.on_change("accent")

    def _select_swatch(self, color: str) -> None:
        for swatch, button in self._swatch_buttons:
            if swatch.lower() == color.lower():
                button.add_css_class("selected")
            else:
                button.remove_css_class("selected")

    def _reset(self) -> None:
        defaults = Config()
        for field in (
            "output",
            "anchor",
            "scale",
            "margin",
            "panel_alpha",
            "accent",
            "font",
            "show_numbers",
            "show_mouse",
            "mouse_device",
            "keyboard_device",
        ):
            setattr(self.config, field, getattr(defaults, field))
        self._load_controls()
        self.on_change("reset")
