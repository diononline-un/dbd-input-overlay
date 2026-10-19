from __future__ import annotations

ANCHORS = (
    "top-left",
    "top-center",
    "top-right",
    "center-left",
    "center",
    "center-right",
    "bottom-left",
    "bottom-center",
    "bottom-right",
)


def anchor_origin(
    anchor: str,
    monitor_width: float,
    monitor_height: float,
    window_width: float,
    window_height: float,
    margin: int,
) -> tuple[int, int]:
    """Return the top-left window offset for one of the nine anchors."""
    if anchor not in ANCHORS:
        anchor = "top-right"
    margin = max(0, int(margin))

    if anchor.endswith("left"):
        x = margin
    elif anchor.endswith("right"):
        x = monitor_width - window_width - margin
    else:
        x = (monitor_width - window_width) / 2

    if anchor.startswith("top"):
        y = margin
    elif anchor.startswith("bottom"):
        y = monitor_height - window_height - margin
    else:
        y = (monitor_height - window_height) / 2

    return max(0, round(x)), max(0, round(y))
