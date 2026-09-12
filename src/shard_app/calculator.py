"""Calculator logic and template rendering (phase 1).

The calculator template renders the full calculator; the display markup lives
in its own component (:mod:`shard_app.display`) and is injected here, keeping
behavior unchanged.
"""

from pathlib import Path

from shard_app.display import render_display

_CALCULATOR_TEMPLATE = (
    Path(__file__).parent / "templates" / "calculator.html"
).read_text()


class Calculator:
    """A tiny calculator that tracks a running value."""

    def __init__(self) -> None:
        self._value: float = 0

    def input(self, value: float) -> None:
        """Set the current value."""
        self._value = value

    def add(self, right: float) -> float:
        """Add *right* to the current value and return the result."""
        self._value += right
        return self._value

    @property
    def value(self) -> float:
        """The current value."""
        return self._value


def render_calculator(value: object) -> str:
    """Render the calculator template, wiring in the display component."""
    return _CALCULATOR_TEMPLATE.replace("{display}", render_display(value))
