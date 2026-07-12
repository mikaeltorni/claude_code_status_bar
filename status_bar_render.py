"""status_bar_render.py - status-line assembly for the Claude Code status bar.

Turns the parsed status-line JSON payload Claude Code sends on stdin into the
single pipe-delimited line shown in the bottom bar. The bar is built from an
ordered registry of independently selectable *segments*; each segment renderer
returns its text or ``None`` when its source values are absent or malformed, so
the bar always renders. Which segments are eligible is resolved per render from
the installed selection (see :mod:`status_bar_config`): when no selection config
exists every segment is shown, preserving the full bar for manual installs.

Components:
  - build_status_line: Assemble the full status line from a payload dict.
"""

from __future__ import annotations

import json
import os

from status_bar_config import SEGMENT_IDS, enabled_segments, is_segment_enabled
from status_bar_format import format_reset, format_reset_day, format_tokens
from status_bar_logging import get_logger, log_call

logger = get_logger(__name__)


def _number(value: object, field: str) -> float | None:
    """Coerce a status payload number, logging malformed fields at debug level."""
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        logger.debug("omitting malformed numeric field %s: %r", field, value)
        return None


def _segment_model(data: dict) -> str | None:
    """Render the model name and optional reasoning effort (e.g. ``Opus · low``)."""
    model = data.get("model") or {}
    model_name = model.get("display_name") or model.get("id") or ""
    effort = (data.get("effort") or {}).get("level")
    if model_name and effort:
        return f"{model_name} · {effort}"
    if model_name:
        return str(model_name)
    return None



def _segment_context(data: dict) -> str | None:
    """Render context-window usage as ``used/size (pct%)``."""
    ctx = data.get("context_window") or {}
    used = _number(ctx.get("total_input_tokens"), "context_window.total_input_tokens")
    size = _number(ctx.get("context_window_size"), "context_window.context_window_size")
    pct = _number(ctx.get("used_percentage"), "context_window.used_percentage")
    if used is not None and size:
        ctx_str = f"{format_tokens(used)}/{format_tokens(size)}"
        if pct is not None:
            ctx_str += f" ({pct:g}%)"
        return ctx_str
    return None


def _segment_five_hour(data: dict) -> str | None:
    """Render the 5-hour rate limit as remaining percent and reset countdown."""
    five = (data.get("rate_limits") or {}).get("five_hour") or {}
    five_used = _number(five.get("used_percentage"), "rate_limits.five_hour.used_percentage")
    if five_used is None:
        return None
    reset = format_reset(five.get("resets_at"))
    return f"5h:{round(100 - five_used)}%" + (f" (~{reset})" if reset else "")


def _segment_weekly(data: dict) -> str | None:
    """Render the weekly rate limit as remaining percent and reset weekday."""
    week = (data.get("rate_limits") or {}).get("seven_day") or {}
    week_used = _number(week.get("used_percentage"), "rate_limits.seven_day.used_percentage")
    if week_used is None:
        return None
    reset_day = format_reset_day(week.get("resets_at"))
    suffix = f" ({reset_day})" if reset_day else ""
    return f"wk:{round(100 - week_used)}%" + suffix


def _segment_diff(data: dict) -> str | None:
    """Render the session diff line count as ``+added/-removed``."""
    cost = data.get("cost") or {}
    added = _number(cost.get("total_lines_added"), "cost.total_lines_added")
    removed = _number(cost.get("total_lines_removed"), "cost.total_lines_removed")
    if added is not None or removed is not None:
        return f"+{int(added or 0)}/-{int(removed or 0)}"
    return None


def _token_high_water(session_id: str, tokens_in: int, tokens_out: int) -> tuple[int, int]:
    """Clamp cumulative token totals to a per-session high-water mark.

    ``context_window.total_*_tokens`` reflect the *most recent* API response.
    Sidechain calls (subagents, haiku utility calls such as title generation)
    report tiny totals, which made the bar flicker between e.g. 162k and 1-6.
    Cumulative session totals never legitimately shrink, so we persist the max
    seen per session and never render below it. State errors are non-fatal.
    """
    if not session_id:
        return tokens_in, tokens_out
    try:
        state_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".state")
        os.makedirs(state_dir, exist_ok=True)
        path = os.path.join(state_dir, f"tokens-{session_id}.json")
        prev_in = prev_out = 0
        try:
            with open(path, encoding="utf-8") as fh:
                prev = json.load(fh)
            prev_in = int(prev.get("in", 0))
            prev_out = int(prev.get("out", 0))
        except (OSError, ValueError):
            pass
        tokens_in = max(tokens_in, prev_in)
        tokens_out = max(tokens_out, prev_out)
        if tokens_in > prev_in or tokens_out > prev_out:
            tmp = f"{path}.tmp.{os.getpid()}"
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump({"in": tokens_in, "out": tokens_out}, fh)
            os.replace(tmp, path)
    except OSError:
        logger.debug("token high-water state unavailable", exc_info=True)
    return tokens_in, tokens_out


def _segment_tokens(data: dict) -> str | None:
    """Render token in/out counts as ``in:x out:y`` (Codex-style)."""
    ctx = data.get("context_window") or {}
    tokens_in = _number(ctx.get("total_input_tokens"), "context_window.total_input_tokens")
    tokens_out = _number(ctx.get("total_output_tokens"), "context_window.total_output_tokens")
    if tokens_in is None and tokens_out is None:
        return None
    tokens_in, tokens_out = _token_high_water(
        str(data.get("session_id") or ""), int(tokens_in or 0), int(tokens_out or 0)
    )
    return f"in:{format_tokens(tokens_in)} out:{format_tokens(tokens_out)}"


def _segment_cost(data: dict) -> str | None:
    """Render the total session cost as ``$x.xx``."""
    usd = _number((data.get("cost") or {}).get("total_cost_usd"), "cost.total_cost_usd")
    if usd is not None:
        return f"${usd:.2f}"
    return None


# Ordered segment registry: (id, renderer). The ids and order mirror
# status_bar_config.SEGMENT_IDS and the installer manifest.
_SEGMENTS: tuple[tuple[str, "callable"], ...] = (
    ("model", _segment_model),
    ("context", _segment_context),
    ("five_hour", _segment_five_hour),
    ("weekly", _segment_weekly),
    ("diff", _segment_diff),
    ("tokens", _segment_tokens),
    ("cost", _segment_cost),
)

assert tuple(seg_id for seg_id, _ in _SEGMENTS) == SEGMENT_IDS, (
    "render registry and SEGMENT_IDS are out of sync"
)


@log_call(logger)
def build_status_line(data: dict) -> str:
    """Build the status-bar text from a Claude Code status-line payload.

    Segments, in order: model + reasoning effort, context-window
    usage, 5-hour rate limit, weekly rate limit, diff line count, and total cost.
    Only segments enabled by the installed selection (see
    :func:`status_bar_config.enabled_segments`) are considered; the rest, and any
    whose values are missing or malformed, are omitted.

    Args:
        data: Parsed status-line JSON object supplied by Claude Code. May be
            empty or partial; any missing or malformed segment is omitted.

    Returns:
        str: A pipe-delimited (`` | ``) status line containing only the segments
        that are enabled and could be rendered, or an empty string when nothing
        is available.
    """
    enabled = enabled_segments()
    parts = []
    for seg_id, renderer in _SEGMENTS:
        if not is_segment_enabled(seg_id, enabled):
            continue
        value = renderer(data)
        if value:
            parts.append(value)

    line = " | ".join(parts)
    logger.debug("built status line with %d segment(s): %r", len(parts), line)
    return line
