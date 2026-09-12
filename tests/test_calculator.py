"""Tests for the calculator template + display wiring (phase 1)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from shard_app.calculator import render_calculator
from shard_app.display import render_display


def test_render_calculator_includes_display_component() -> None:
    html = render_calculator(5)
    assert render_display(5) in html
    assert "calculator" in html


def test_render_calculator_matches_known_good_baseline() -> None:
    expected = (
        '<section class="calculator">\n'
        "  "
        '<div class="calculator-display" aria-live="polite" aria-atomic="true">\n'
        '  <span class="calculator-display__value">5</span>\n'
        "</div>\n"
        "\n"
        '  <div class="calculator__keys" role="group" aria-label="Calculator keys"></div>\n'
        "</section>\n"
    )
    assert render_calculator(5) == expected
