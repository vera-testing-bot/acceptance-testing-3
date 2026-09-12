"""The acceptance shard calculator app.

The package exposes :func:`add` (kept for the seed test) plus the unified data
access layer (:mod:`shard_app.store`) and the components that sit on top of it
(:mod:`shard_app.calculator`).
"""

from __future__ import annotations

from .calculator import Calculator, HistoryPanel, Settings
from .store import (
    CURRENT_SHAPE,
    SCHEMA_VERSION,
    FileBackend,
    MemoryBackend,
    Schema,
    Store,
    Transition,
    migrate,
)

__all__ = [
    "CURRENT_SHAPE",
    "SCHEMA_VERSION",
    "Calculator",
    "FileBackend",
    "HistoryPanel",
    "MemoryBackend",
    "Schema",
    "Settings",
    "Store",
    "Transition",
    "add",
    "migrate",
]


def add(left: int, right: int) -> int:
    """Return the sum of two integers."""
    return left + right


def is_palindrome(text: str) -> bool:
    """Return True when *text* is a palindrome, ignoring case and non-alphanumeric characters."""
    cleaned = [ch.lower() for ch in text if ch.isalnum()]
    return cleaned == cleaned[::-1]
