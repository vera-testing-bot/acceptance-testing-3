"""Tests for the value formatting helper (phase 2)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from shard_app.formatting import format_value


def test_format_value_formats_integer() -> None:
    assert format_value(5) == "5"


def test_format_value_trims_trailing_zeros() -> None:
    assert format_value(2.50) == "2.5"


def test_format_value_handles_error_strings() -> None:
    assert format_value("Error") == "Error"


def test_format_value_rejects_garbage() -> None:
    assert format_value("nope") == "Error"


def test_format_value_rejects_nan() -> None:
    import math

    assert format_value(math.nan) == "Error"
