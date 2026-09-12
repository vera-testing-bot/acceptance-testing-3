"""The calculator component, now a view over the unified :class:`Store`.

Before this refactor the calculator held display state in a module-level
global, serialized it to localStorage by hand, and the history panel kept a
separate copy that drifted. All of that is gone: the calculator reads and
writes through the store, and history is a view over the store's ``history``
field rather than its own storage.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .store import Store


class Calculator:
    """A small calculator that owns no state of its own."""

    WRITER = "calculator"

    def __init__(self, store: Store) -> None:
        self._store = store

    @property
    def display(self) -> str:
        return self._store.get("display")

    def input_digit(self, digit: str) -> None:
        if not digit.isdigit():
            raise ValueError(f"not a digit: {digit!r}")
        current = self.display
        next_display = digit if current == "0" else current + digit
        self._store.set("display", next_display, self.WRITER)

    def input_decimal(self) -> None:
        if "." in self.display:
            return
        self._store.set("display", self.display + ".", self.WRITER)

    def clear(self) -> None:
        self._store.set("display", "0", self.WRITER)

    def _round(self, value: float) -> float:
        precision = int(self._store.get("precision"))
        return round(value, precision)

    def evaluate(self) -> float:
        expr = self.display
        try:
            result = self._safe_eval(expr)
        except ZeroDivisionError:
            result = float("inf")
        rounded = self._round(result)
        self._store.append_history(f"{expr} = {rounded}", self.WRITER)
        self._store.set("display", str(rounded), self.WRITER)
        return rounded

    def _safe_eval(self, expr: str) -> float:
        allowed = {
            name: getattr(math, name)
            for name in (
                "sin",
                "cos",
                "tan",
                "sqrt",
                "log",
                "log10",
                "pi",
                "e",
                "fabs",
            )
        }
        mode = self._store.get("angle_mode")
        if mode == "deg":
            allowed["sin"] = lambda x: math.sin(math.radians(x))
            allowed["cos"] = lambda x: math.cos(math.radians(x))
            allowed["tan"] = lambda x: math.tan(math.radians(x))
        return float(eval(expr, {"__builtins__": {}}, allowed))


class HistoryPanel:
    """A read-only view over the store's ``history`` field.

    This used to be a third copy of the history that drifted out of sync. It is
    now a thin view: it reads from the store and clears through the store, so
    there is exactly one history.
    """

    WRITER = "history"

    def __init__(self, store: Store) -> None:
        self._store = store

    def entries(self) -> list[str]:
        return list(self._store.get("history"))

    def clear(self) -> None:
        self._store.clear_history(self.WRITER)


class Settings:
    """The settings subsystem, backed by the store's typed fields."""

    WRITER = "settings"

    def __init__(self, store: Store) -> None:
        self._store = store

    @property
    def angle_mode(self) -> str:
        return self._store.get("angle_mode")

    @angle_mode.setter
    def angle_mode(self, value: str) -> None:
        if value not in ("deg", "rad"):
            raise ValueError(f"unknown angle mode: {value!r}")
        self._store.set("angle_mode", value, self.WRITER)

    @property
    def precision(self) -> int:
        return int(self._store.get("precision"))

    @precision.setter
    def precision(self, value: int) -> None:
        if value < 0:
            raise ValueError("precision must be non-negative")
        self._store.set("precision", int(value), self.WRITER)
