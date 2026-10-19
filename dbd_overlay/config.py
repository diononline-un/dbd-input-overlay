from __future__ import annotations

import json
import tomllib
from dataclasses import dataclass
from pathlib import Path

from .position import ANCHORS


@dataclass
class Config:
    output: str = ""
    anchor: str = "top-right"
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
    if "anchor" in data:
        anchor = str(data["anchor"])
        cfg.anchor = anchor if anchor in ANCHORS else "top-right"
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


def save_config(path: Path, cfg: Config) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"output = {json.dumps(cfg.output)}",
        f"anchor = {json.dumps(cfg.anchor)}",
        f"scale = {cfg.scale:g}",
        f"margin = {cfg.margin}",
        f"panel_alpha = {cfg.panel_alpha:g}",
        f"accent = {json.dumps(cfg.accent)}",
        f"font = {json.dumps(cfg.font)}",
        f"show_numbers = {str(cfg.show_numbers).lower()}",
        f"show_mouse = {str(cfg.show_mouse).lower()}",
        f"mouse_device = {json.dumps(cfg.mouse_device)}",
        f"keyboard_device = {json.dumps(cfg.keyboard_device)}",
    ]
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text("\n".join(lines) + "\n", encoding="utf-8")
    temporary.replace(path)
