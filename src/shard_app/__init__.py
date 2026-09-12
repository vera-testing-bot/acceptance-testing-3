"""Trivial module so an acceptance shard repo has code to change."""


def add(left: int, right: int) -> int:
    """Return the sum of two integers."""
    return left + right


def is_palindrome(text: str) -> bool:
    """Return True when *text* is a palindrome, ignoring case and non-alphanumeric characters."""
    cleaned = [ch.lower() for ch in text if ch.isalnum()]
    return cleaned == cleaned[::-1]
