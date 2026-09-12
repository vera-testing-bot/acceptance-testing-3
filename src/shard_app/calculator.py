"""The calculator component, now a view over the unified :class:`Store`.

Before this refactor the calculator held display state in a module-level
global, serialized it to localStorage by hand, and the history panel kept a
separate copy that drifted. All of that is gone: the calculator reads and
writes through the store, and history is a view over the store's ``history``
field rather than its own storage.

The calculator template renders the full calculator; the display markup lives
in its own component (:mod:`shard_app.display`) and is injected here, keeping
behavior unchanged.
"""

from __future__ import annotations

import ast
import math
from pathlib import Path
from typing import TYPE_CHECKING

from shard_app.display import render_display

if TYPE_CHECKING:
    from .store import Store

_CALCULATOR_TEMPLATE = (
    Path(__file__).parent / "templates" / "calculator.html"
).read_text()

_ALLOWED_BINOPS = {
    ast.Add: lambda a, b: a + b,
    ast.Sub: lambda a, b: a - b,
    ast.Mult: lambda a, b: a * b,
    ast.Div: lambda a, b: a / b,
    ast.Mod: lambda a, b: a % b,
    ast.Pow: lambda a, b: a**b,
    ast.FloorDiv: lambda a, b: a // b,
}

_ALLOWED_UNARYOPS = {
    ast.UAdd: lambda a: +a,
    ast.USub: lambda a: -a,
}


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
        return float(self._eval_node(ast.parse(expr, mode="eval").body, allowed))

    def _eval_node(self, node: ast.AST, names: dict[str, object]) -> float:
        if isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float)) and not isinstance(
                node.value, bool
            ):
                return node.value
            raise ValueError(f"unsupported constant: {node.value!r}")
        if isinstance(node, ast.BinOp):
            op = _ALLOWED_BINOPS.get(type(node.op))
            if op is None:
                raise ValueError(f"unsupported operator: {type(node.op).__name__}")
            return op(
                self._eval_node(node.left, names), self._eval_node(node.right, names)
            )
        if isinstance(node, ast.UnaryOp):
            op = _ALLOWED_UNARYOPS.get(type(node.op))
            if op is None:
                raise ValueError(f"unsupported unary op: {type(node.op).__name__}")
            return op(self._eval_node(node.operand, names))
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name):
                raise TypeError("only named function calls are allowed")
            func = names.get(node.func.id)
            if func is None:
                raise NameError(f"unknown function: {node.func.id!r}")
            if node.keywords:
                raise ValueError("keyword arguments are not allowed")
            args = [self._eval_node(a, names) for a in node.args]
            return func(*args)  # type: ignore[operator]
        if isinstance(node, ast.Name):
            value = names.get(node.id)
            if value is None:
                raise NameError(f"unknown name: {node.id!r}")
            return value  # type: ignore[return-value]
        raise ValueError(f"unsupported expression node: {type(node).__name__}")


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


def render_calculator(value: object) -> str:
    """Render the calculator template, wiring in the display component."""
    return _CALCULATOR_TEMPLATE.replace("{display}", render_display(value))
