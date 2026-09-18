"""Trivial module so an acceptance shard repo has code to change."""


def add(left: int, right: int) -> int:
    """Return the sum of two integers.

    Args:
        left: The first integer addend.
        right: The second integer addend.

    Returns:
        The integer sum of ``left`` and ``right``.
    """
    return left + right


def is_palindrome(text: str) -> bool:
    """Return True when ``text`` reads the same forwards and backwards.

    Comparison ignores case and any non-alphanumeric characters.
    """
    cleaned = [ch.lower() for ch in text if ch.isalnum()]
    return cleaned == cleaned[::-1]
