from __future__ import annotations

from collections.abc import Iterable

Color = tuple[float, float, float]
RGBA = tuple[float, float, float, float]


def parse_hex_color(value: str, fallback: Color = (0.76, 0.25, 0.29)) -> Color:
    raw = value.strip().lstrip("#")
    if len(raw) != 6:
        return fallback
    try:
        return tuple(int(raw[index : index + 2], 16) / 255 for index in (0, 2, 4))  # type: ignore[return-value]
    except ValueError:
        return fallback


def mix_rgba(base: RGBA, accent: RGBA, amount: float) -> RGBA:
    amount = max(0.0, min(1.0, amount))
    return tuple(base[index] + (accent[index] - base[index]) * amount for index in range(4))  # type: ignore[return-value]


def with_alpha(color: Iterable[float], alpha: float) -> RGBA:
    r, g, b = color
    return (r, g, b, max(0.0, min(1.0, alpha)))
