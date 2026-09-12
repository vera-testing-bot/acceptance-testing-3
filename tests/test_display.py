"""Tests for the display component (phases 1, 2 and 3)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from shard_app.display import render_display
from shard_app.formatting import format_value


def test_render_display_is_standalone_component() -> None:
    html = render_display(7)
    assert "calculator-display" in html
    assert "7" in html


def test_render_display_uses_formatting_helper() -> None:
    html = render_display(2.50)
    assert format_value(2.50) in html
    assert "2.5" in html
    assert "2.50" not in html


def test_render_display_has_aria_live_region() -> None:
    html = render_display(0)
    assert "aria-live" in html
    assert "aria-atomic" in html


def test_render_display_announces_all_values() -> None:
    for value in (0, -3, 1.5, "Error"):
        html = render_display(value)
        assert "aria-live" in html
