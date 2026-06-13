"""Formatting helpers for Claude Code status-bar values."""

import time


def format_tokens(n: float) -> str:
    """Format a token count as a compact string such as ``63.2k`` or ``1.0M``."""
    n = int(n)
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}k"
    return str(n)


def format_reset(ts) -> str:
    """Format a Unix reset timestamp as compact time remaining."""
    try:
        remaining = int(ts) - int(time.time())
    except (TypeError, ValueError):
        return ""
    if remaining <= 0:
        return "now"
    hours, rem = divmod(remaining, 3600)
    minutes = rem // 60
    if hours:
        return f"{hours}h{minutes:02d}m"
    return f"{minutes}m"


def format_reset_day(ts) -> str:
    """Format a Unix reset timestamp as a local weekday and clock time."""
    try:
        reset = int(ts)
    except (TypeError, ValueError):
        return ""
    return time.strftime("%a %H:%M", time.localtime(reset))
