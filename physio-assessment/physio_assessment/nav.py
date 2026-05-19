"""TUI-wide arrow-key navigation helpers.

Used by BaseSection.on_key and per-section grid-nav handlers.

Positioning
-----------
Textual 8.2.5 does not expose a reliable cross-scroll-container screen-coordinate
API, so position is computed in *section coordinates*: each widget's center is
found by walking the DOM from the widget up to its containing BaseSection,
accumulating region.x / region.y offsets at each level.  This gives stable,
scroll-independent coordinates that are correct for both vertical stacks and
horizontal button rows.

Scoring
-------
Up/Down: prefer widgets closest vertically above/below; penalise x-offset by 0.5
    so the directly-above/below widget wins over a diagonal one.
Left/Right: prefer widgets closest horizontally in the same direction; penalise
    y-offset by 3.0 so left/right stays within the same row.
"""

from __future__ import annotations

from textual.widget import Widget
from textual.widgets import TextArea


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _section_coords(widget: Widget, section: Widget) -> tuple[float, float]:
    """Return widget's center position in section's coordinate space.

    Walks up the DOM from widget to section, accumulating region offsets.
    Stable regardless of scroll position.
    """
    try:
        r = widget.region
        cx = float(r.x + r.width / 2)
        cy = float(r.y + r.height / 2)
    except Exception:
        return 0.0, 0.0

    node = widget.parent
    while node is not None and node is not section:
        try:
            r = node.region
            cx += r.x
            cy += r.y
        except Exception:
            pass
        node = getattr(node, "parent", None)

    return cx, cy


def _score(
    fx: float, fy: float,
    cx: float, cy: float,
    direction: str,
) -> float | None:
    """Proximity score for *direction* (lower = better), or None if wrong direction."""
    if direction == "up":
        if cy >= fy:
            return None
        return (fy - cy) + abs(cx - fx) * 0.5
    if direction == "down":
        if cy <= fy:
            return None
        return (cy - fy) + abs(cx - fx) * 0.5
    if direction == "left":
        if cx >= fx:
            return None
        return (fx - cx) + abs(cy - fy) * 3.0
    if direction == "right":
        if cx <= fx:
            return None
        return (cx - fx) + abs(cy - fy) * 3.0
    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def find_parent_section(widget: Widget) -> Widget | None:
    """Walk up the DOM until we hit a BaseSection (or None if not inside one)."""
    from .sections.base import BaseSection
    node = widget.parent
    while node is not None:
        if isinstance(node, BaseSection):
            return node
        node = getattr(node, "parent", None)
    return None


def focusable_in_section(section: Widget) -> list[Widget]:
    """All focusable, non-TextArea widgets inside *section*, in DOM order."""
    return [
        w for w in section.query("*")
        if w.can_focus and not isinstance(w, TextArea)
    ]


def find_neighbor(
    focused: Widget,
    candidates: list[Widget],
    direction: str,
    section: Widget | None = None,
) -> Widget | None:
    """Return the nearest candidate in *direction* using section coordinates.

    *section* is optional — if omitted, find_parent_section() is called.
    Returns None when no candidate exists in that direction (boundary), which
    allows the event to continue bubbling so the scroll container scrolls.
    """
    if section is None:
        section = find_parent_section(focused)
    if section is None:
        return None

    fx, fy = _section_coords(focused, section)

    best: Widget | None = None
    best_score = float("inf")

    for cand in candidates:
        if cand is focused:
            continue
        cx, cy = _section_coords(cand, section)
        s = _score(fx, fy, cx, cy, direction)
        if s is not None and s < best_score:
            best_score = s
            best = cand

    return best


def escape_to_neighbor(section: Widget, focused: Widget, direction: str) -> bool:
    """Focus the nearest widget in *section* in *direction* from *focused*.

    Called by grid-nav handlers when internal grid movement hits a boundary.
    Returns True if a neighbor was found and focused.
    """
    candidates = focusable_in_section(section)
    target = find_neighbor(focused, candidates, direction, section=section)
    if target is not None:
        target.focus()
        return True
    return False
