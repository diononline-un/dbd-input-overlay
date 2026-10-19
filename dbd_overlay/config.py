from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Config:
    output: str = ""
    scale: float = 1.0
    margin: int = 16
    panel_alpha: float = 0.28
    accent: str = "#c2414b"
    font: str = "Sans"
    show_numbers: bool = True
    show_mouse: bool = True
    mouse_device: str = ""
    keyboard_device: str = ""


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def load_config(path: Path) -> Config:
    data: dict = {}
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return Config()
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise ValueError(f"Config could not be read: {exc}") from exc

    cfg = Config()
    if "output" in data:
        cfg.output = str(data["output"])
    if "scale" in data:
        cfg.scale = _clamp(float(data["scale"]), 0.6, 2.0)
    if "margin" in data:
        cfg.margin = max(0, int(data["margin"]))
    if "panel_alpha" in data:
        cfg.panel_alpha = _clamp(float(data["panel_alpha"]), 0.0, 1.0)
    if "accent" in data:
        cfg.accent = str(data["accent"])
    if "font" in data:
        cfg.font = str(data["font"])
    if "show_numbers" in data:
        cfg.show_numbers = bool(data["show_numbers"])
    if "show_mouse" in data:
        cfg.show_mouse = bool(data["show_mouse"])
    if "mouse_device" in data:
        cfg.mouse_device = str(data["mouse_device"])
    if "keyboard_device" in data:
        cfg.keyboard_device = str(data["keyboard_device"])
    return cfg
