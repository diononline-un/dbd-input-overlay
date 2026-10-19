from __future__ import annotations

import math

import cairo
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Pango", "1.0")
gi.require_version("PangoCairo", "1.0")

from gi.repository import Pango, PangoCairo  # noqa: E402

from .colors import mix_rgba, parse_hex_color  # noqa: E402
from .config import Config  # noqa: E402
from .layout import Layout, Rect, SHADOW  # noqa: E402
from .state import OverlayState  # noqa: E402

KEY_TEXT_SIZE = 9.6
WORD_TEXT_SIZE = 7.2
NUMBER_TEXT_SIZE = 7.6
BUTTON_TEXT_SIZE = 6.4


def _rounded_rect(cr: cairo.Context, x: float, y: float, w: float, h: float, radius: float) -> None:
    radius = min(radius, w / 2, h / 2)
    cr.new_sub_path()
    cr.arc(x + w - radius, y + radius, radius, -math.pi / 2, 0)
    cr.arc(x + w - radius, y + h - radius, radius, 0, math.pi / 2)
    cr.arc(x + radius, y + h - radius, radius, math.pi / 2, math.pi)
    cr.arc(x + radius, y + radius, radius, math.pi, 3 * math.pi / 2)
    cr.close_path()


class OverlayRenderer:
    def __init__(self, state: OverlayState, config: Config, layout: Layout, scale: float) -> None:
        self.state = state
        self.config = config
        self.layout = layout
        self.scale = scale
        self.accent = parse_hex_color(config.accent)
        self.hover_close = False
        self._anim = {name: 0.0 for name in layout.keycaps}
        self._anim.update({name: 0.0 for name in ("M1", "M2", "M3", "M4", "M5")})

    def tick(self, dt: float) -> None:
        for name in self._anim:
            active = self.state.is_active(name)
            target = 1.0 if active else 0.0
            self._anim[name] += (target - self._anim[name]) * min(1.0, dt * 30.0)

    def draw(self, area, cr: cairo.Context, width: int, height: int) -> None:
        cr.set_operator(cairo.OPERATOR_SOURCE)
        cr.set_source_rgba(0, 0, 0, 0)
        cr.paint()
        cr.set_operator(cairo.OPERATOR_OVER)

        if not self.state.snapshot().visible:
            return

        cr.save()
        cr.scale(self.scale, self.scale)
        cr.translate(SHADOW, SHADOW)
        self._draw_panel(cr)
        for label, rect in self.layout.keycaps.items():
            self._draw_key(cr, label, rect)
        if self.layout.mouse_body is not None:
            self._draw_mouse(cr)
        self._draw_close(cr)
        cr.restore()

    def _draw_close(self, cr: cairo.Context) -> None:
        rect = self.layout.close_button
        if self.hover_close:
            _rounded_rect(cr, rect.x - 3, rect.y - 3, rect.w + 6, rect.h + 6, 4)
            cr.set_source_rgba(1, 1, 1, 0.10)
            cr.fill()

        color = (*self.accent, 0.95) if self.hover_close else (1, 1, 1, 0.42)
        cr.set_source_rgba(*color)
        cr.set_line_width(1.25)
        cr.set_line_cap(cairo.LINE_CAP_ROUND)
        pad = 3.2
        cr.move_to(rect.x + pad, rect.y + pad)
        cr.line_to(rect.x + rect.w - pad, rect.y + rect.h - pad)
        cr.move_to(rect.x + rect.w - pad, rect.y + pad)
        cr.line_to(rect.x + pad, rect.y + rect.h - pad)
        cr.stroke()

    def _draw_panel(self, cr: cairo.Context) -> None:
        if self.config.panel_alpha <= 0.001:
            return

        w = self.layout.card_width
        h = self.layout.card_height

        cr.set_source_rgba(0, 0, 0, 0.16)
        _rounded_rect(cr, 0, 2.0, w, h, 12)
        cr.fill()
        cr.set_source_rgba(0, 0, 0, 0.09)
        _rounded_rect(cr, 0, 4.5, w, h, 12)
        cr.fill()

        _rounded_rect(cr, 0, 0, w, h, 12)
        cr.set_source_rgba(0.025, 0.032, 0.045, self.config.panel_alpha)
        cr.fill_preserve()

        gradient = cairo.LinearGradient(0, 0, 0, h)
        gradient.add_color_stop_rgba(0, 1, 1, 1, 0.045)
        gradient.add_color_stop_rgba(0.45, 1, 1, 1, 0.012)
        gradient.add_color_stop_rgba(1, 0, 0, 0, 0)
        cr.set_source(gradient)
        cr.fill_preserve()

        cr.set_source_rgba(1, 1, 1, 0.11)
        cr.set_line_width(0.8)
        cr.stroke()

    def _draw_key(self, cr: cairo.Context, label: str, rect: Rect) -> None:
        anim = self._anim.get(label, 0.0)
        is_number = label.isdigit()
        base_text_alpha = 0.62 if is_number else 0.88

        fill = mix_rgba((0.02, 0.026, 0.038, 0.62), (*self.accent, 0.92), anim)
        border = mix_rgba((1, 1, 1, 0.22), (1, 1, 1, 0.60), anim)
        text = mix_rgba((1, 1, 1, base_text_alpha), (1, 1, 1, 0.99), anim)

        _rounded_rect(cr, rect.x, rect.y, rect.w, rect.h, 5.2)
        cr.set_source_rgba(*fill)
        cr.fill_preserve()
        cr.set_source_rgba(*border)
        cr.set_line_width(0.8)
        cr.stroke()

        if label in ("SHIFT", "SPACE"):
            size = WORD_TEXT_SIZE
        elif is_number:
            size = NUMBER_TEXT_SIZE
        else:
            size = KEY_TEXT_SIZE + anim * 0.25

        self._draw_text(cr, label, rect.x + rect.w / 2, rect.y + rect.h / 2 + 0.4, size, text)

    def _draw_mouse(self, cr: cairo.Context) -> None:
        body = self.layout.mouse_body
        if body is None:
            return

        cx, cy = self.layout.compass_center
        radius = self.layout.compass_radius
        cr.new_path()
        cr.set_source_rgba(0, 0, 0, 0.16)
        cr.arc(cx, cy, radius, 0, 2 * math.pi)
        cr.fill_preserve()
        cr.set_source_rgba(1, 1, 1, 0.10)
        cr.set_line_width(0.8)
        cr.stroke()

        for angle in (0, 90, 180, 270):
            radians = math.radians(angle)
            inner = radius - 3.2
            outer = radius - 1.8
            cr.move_to(cx + math.cos(radians) * inner, cy + math.sin(radians) * inner)
            cr.line_to(cx + math.cos(radians) * outer, cy + math.sin(radians) * outer)
        cr.set_source_rgba(1, 1, 1, 0.20)
        cr.set_line_width(0.8)
        cr.stroke()

        vx, vy = self.state.snapshot().motion
        magnitude = math.hypot(vx, vy)
        strength = min(1.0, magnitude / 1800.0)
        if strength > 0.02:
            angle = math.atan2(vy, vx)
            length = radius * 0.72 * strength
            end_x = cx + math.cos(angle) * length
            end_y = cy + math.sin(angle) * length
            cr.new_path()
            cr.set_source_rgba(*self.accent, 0.92)
            cr.set_line_width(1.7)
            cr.set_line_cap(cairo.LINE_CAP_ROUND)
            cr.move_to(cx, cy)
            cr.line_to(end_x, end_y)
            cr.stroke()
            cr.new_path()
            cr.arc(end_x, end_y, 1.7, 0, 2 * math.pi)
            cr.fill()
        else:
            cr.new_path()
            cr.set_source_rgba(1, 1, 1, 0.26)
            cr.arc(cx, cy, 1.5, 0, 2 * math.pi)
            cr.fill()

        cr.new_path()
        _rounded_rect(cr, body.x, body.y, body.w, body.h, 7)
        cr.set_source_rgba(0.02, 0.026, 0.038, 0.52)
        cr.fill_preserve()
        cr.set_source_rgba(1, 1, 1, 0.20)
        cr.set_line_width(0.8)
        cr.stroke()

        for name, x, w in (
            ("M1", body.x, body.w / 2),
            ("M2", body.x + body.w / 2, body.w / 2),
        ):
            anim = self._anim.get(name, 0.0)
            if anim <= 0.01:
                continue
            cr.save()
            _rounded_rect(cr, body.x, body.y, body.w, body.h, 7)
            cr.clip()
            cr.rectangle(x, body.y, w, 12)
            cr.set_source_rgba(*self.accent, 0.64 * anim)
            cr.fill()
            cr.restore()

        cr.set_source_rgba(1, 1, 1, 0.13)
        cr.set_line_width(0.7)
        cr.move_to(body.x + body.w / 2, body.y + 1.5)
        cr.line_to(body.x + body.w / 2, body.y + 12)
        cr.stroke()

        wheel_anim = self._anim.get("M3", 0.0)
        wheel_fill = mix_rgba((1, 1, 1, 0.13), (*self.accent, 0.90), wheel_anim)
        _rounded_rect(cr, body.x + body.w / 2 - 2, body.y + 3, 4, 8.5, 2)
        cr.set_source_rgba(*wheel_fill)
        cr.fill()

        for name, rect in self.layout.mouse_sides.items():
            anim = self._anim.get(name, 0.0)
            fill = mix_rgba((0.02, 0.026, 0.038, 0.58), (*self.accent, 0.90), anim)
            border = mix_rgba((1, 1, 1, 0.20), (1, 1, 1, 0.55), anim)
            _rounded_rect(cr, rect.x, rect.y, rect.w, rect.h, 3.5)
            cr.set_source_rgba(*fill)
            cr.fill_preserve()
            cr.set_source_rgba(*border)
            cr.set_line_width(0.7)
            cr.stroke()
            label = name[-1]
            text = mix_rgba((1, 1, 1, 0.78), (1, 1, 1, 0.99), anim)
            self._draw_text(
                cr,
                label,
                rect.x + rect.w / 2,
                rect.y + rect.h / 2 + 0.3,
                BUTTON_TEXT_SIZE,
                text,
            )

        scroll = self.state.snapshot().scroll
        if scroll:
            x = body.x + body.w + 6
            y = body.y + 10
            tip = y - 2 if scroll > 0 else y + 2
            tail = y + 2 if scroll > 0 else y - 2
            cr.set_source_rgba(*self.accent, 0.92)
            cr.set_line_width(1.4)
            cr.set_line_cap(cairo.LINE_CAP_ROUND)
            cr.move_to(x - 2.5, tail)
            cr.line_to(x, tip)
            cr.line_to(x + 2.5, tail)
            cr.stroke()

    def _draw_text(
        self,
        cr: cairo.Context,
        text: str,
        center_x: float,
        center_y: float,
        size: float,
        color: tuple[float, float, float, float],
    ) -> None:
        layout = PangoCairo.create_layout(cr)
        description = Pango.FontDescription()
        description.set_family(self.config.font)
        description.set_weight(Pango.Weight.BOLD)
        description.set_absolute_size(size * Pango.SCALE)
        layout.set_font_description(description)
        layout.set_text(text, -1)
        width, height = layout.get_pixel_size()
        cr.move_to(center_x - width / 2, center_y - height / 2)
        cr.set_source_rgba(*color)
        PangoCairo.show_layout(cr, layout)
