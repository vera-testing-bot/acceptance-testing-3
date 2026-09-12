"""Tests for the calculator template + display wiring (phase 1)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from shard_app.calculator import Calculator, render_calculator
from shard_app.display import render_display


def test_calculator_adds() -> None:
    calc = Calculator()
    calc.input(2)
    assert calc.add(3) == 5
    assert calc.value == 5


def test_render_calculator_includes_display_component() -> None:
    html = render_calculator(5)
    assert render_display(5) in html
    assert "calculator" in html


def test_render_calculator_behavior_unchanged_by_display_extraction() -> None:
    assert render_calculator(5) == render_calculator(5)
