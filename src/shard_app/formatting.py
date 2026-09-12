"""Value formatting helper for the calculator display (phase 2).

Every value rendered to the display flows through :func:`format_value` so that
formatting lives in exactly one place.
"""

import math

_ERROR = "Error"


def format_value(value: object) -> str:
    """Return a display-ready string for *value*.

    Integers render without a trailing ``.0``; floats shed surplus trailing
    zeros; anything that is not a real number (strings other than the sentinel
    ``"Error"``, NaN, non-numeric input) collapses to ``"Error"``.
    """
    if isinstance(value, bool):
        return _ERROR
    if isinstance(value, str):
        return value if value == _ERROR else _ERROR
    try:
        number = float(value)
    except (TypeError, ValueError):
        return _ERROR
    if math.isnan(number):
        return _ERROR
    if number.is_integer():
        return str(int(number))
    text = repr(number)
    return text.rstrip("0").rstrip(".") if "." in text else text
