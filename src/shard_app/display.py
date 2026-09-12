"""Standalone display component (phase 1) with accessibility (phase 3).

Renders the display markup from ``templates/display.html``. Every value is
run through :func:`shard_app.formatting.format_value` so formatting stays
centralized, and the region carries an ``aria-live`` region so screen readers
announce updates with no visual change.
"""

from pathlib import Path

from shard_app.formatting import format_value

_DISPLAY_TEMPLATE = (Path(__file__).parent / "templates" / "display.html").read_text()


def render_display(value: object) -> str:
    """Return the display component HTML for *value*."""
    return _DISPLAY_TEMPLATE.replace("{value}", format_value(value))
