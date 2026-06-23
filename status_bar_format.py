"""status_bar_format.py - value formatting helpers for the status bar.

Pure, side-effect-free helpers that turn raw status-line values into the compact
strings shown in the Claude Code status bar. Each helper degrades gracefully on
malformed input (returning an empty string) and records a debug diagnostic via
the centralized logger.

Components:
  - format_tokens: Render a token count as a compact ``63.2k`` / ``1.0M`` string.
  - format_reset: Render a Unix reset timestamp as relative time remaining.
  - format_reset_day: Render a Unix reset timestamp as a local weekday + time.
"""

from __future__ import annotations

import time
from typing import SupportsFloat

from status_bar_logging import get_logger

logger = get_logger(__name__)


def format_tokens(n: SupportsFloat) -> str:
    """Format a token count as a compact human-readable string.

    Args:
        n: Token count to format. Any value accepted by ``int()`` is supported;
            floats are truncated toward zero before formatting (e.g. ``999.9``
            -> ``"999"``).

    Returns:
        str: ``"<x.x>M"`` for millions, ``"<x.x>k"`` for thousands, otherwise
        the plain integer as a string (e.g. ``63_249`` -> ``"63.2k"``), or
        ``""`` on invalid input.
    """
    try:
        n = int(n)
    except (TypeError, ValueError):
        logger.debug("format_tokens received invalid token count: %r", n)
        return ""
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}k"
    return str(n)


def format_reset(ts: object) -> str:
    """Format a Unix reset timestamp as compact time remaining from now.

    Args:
        ts: Unix epoch seconds for the reset, as anything ``int()`` accepts
            (int, float, or numeric string). Invalid values yield ``""``.

    Returns:
        str: ``"now"`` if the reset is due, ``"<h>h<mm>m"`` when an hour or more
        remains, ``"<m>m"`` for sub-hour windows, or ``""`` on invalid input.
    """
    try:
        remaining = int(ts) - int(time.time())
    except (TypeError, ValueError):
        logger.debug("format_reset received invalid timestamp: %r", ts)
        return ""
    if remaining <= 0:
        return "now"
    hours, rem = divmod(remaining, 3600)
    minutes = rem // 60
    if hours:
        return f"{hours}h{minutes:02d}m"
    return f"{minutes}m"


def format_reset_day(ts: object) -> str:
    """Format a Unix reset timestamp as a local weekday and clock time.

    Args:
        ts: Unix epoch seconds for the reset, as anything ``int()`` accepts
            (int, float, or numeric string). Invalid values yield ``""``.

    Returns:
        str: The reset rendered in local time as ``"%a %H:%M"`` (e.g.
        ``"Sat 22:22"``), or ``""`` on invalid input.
    """
    try:
        reset = int(ts)
    except (TypeError, ValueError):
        logger.debug("format_reset_day received invalid timestamp: %r", ts)
        return ""
    return time.strftime("%a %H:%M", time.localtime(reset))
