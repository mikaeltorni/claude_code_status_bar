"""status_bar_render.py - status-line assembly for the Claude Code status bar.

Turns the parsed status-line JSON payload Claude Code sends on stdin into the
single pipe-delimited line shown in the bottom bar. Every segment is optional:
absent or malformed values are simply omitted so the bar always renders.

Components:
  - build_status_line: Assemble the full status line from a payload dict.
"""

from __future__ import annotations

import os

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


@log_call(logger)
def build_status_line(data: dict) -> str:
    """Build the status-bar text from a Claude Code status-line payload.

    Segments, in order: model + reasoning effort, repository name, context-window
    usage, 5-hour rate limit, weekly rate limit, diff line count, and total cost.

    Args:
        data: Parsed status-line JSON object supplied by Claude Code. May be
            empty or partial; any missing or malformed segment is omitted.

    Returns:
        str: A pipe-delimited (`` | ``) status line containing only the segments
        that could be rendered, or an empty string when nothing is available.
    """
    parts = []

    # Model + reasoning effort (one/two words).
    model = data.get("model") or {}
    model_name = model.get("display_name") or model.get("id") or ""
    effort = (data.get("effort") or {}).get("level")
    if model_name and effort:
        parts.append(f"{model_name} · {effort}")
    elif model_name:
        parts.append(str(model_name))

    # Full project path.
    workspace = data.get("workspace") or {}
    project_path = workspace.get("project_dir") or workspace.get("current_dir") or data.get("cwd")
    if project_path:
        parts.append(os.path.basename(str(project_path).rstrip("/")))

    # Context-window usage in numbers.
    ctx = data.get("context_window") or {}
    used = _number(ctx.get("total_input_tokens"), "context_window.total_input_tokens")
    size = _number(ctx.get("context_window_size"), "context_window.context_window_size")
    pct = _number(ctx.get("used_percentage"), "context_window.used_percentage")
    if used is not None and size:
        ctx_str = f"{format_tokens(used)}/{format_tokens(size)}"
        if pct is not None:
            ctx_str += f" ({pct:g}%)"
        parts.append(ctx_str)

    # Rate limits — 5-hour and weekly windows, shown as remaining (100 - used).
    rl = data.get("rate_limits") or {}
    five = rl.get("five_hour") or {}
    five_used = _number(five.get("used_percentage"), "rate_limits.five_hour.used_percentage")
    if five_used is not None:
        reset = format_reset(five.get("resets_at"))
        parts.append(f"5h:{round(100 - five_used)}%" + (f" (~{reset})" if reset else ""))
    week = rl.get("seven_day") or {}
    week_used = _number(week.get("used_percentage"), "rate_limits.seven_day.used_percentage")
    if week_used is not None:
        reset_day = format_reset_day(week.get("resets_at"))
        suffix = f" ({reset_day})" if reset_day else ""
        parts.append(f"wk:{round(100 - week_used)}%" + suffix)

    # Diff count and total cost.
    cost = data.get("cost") or {}
    added = _number(cost.get("total_lines_added"), "cost.total_lines_added")
    removed = _number(cost.get("total_lines_removed"), "cost.total_lines_removed")
    if added is not None or removed is not None:
        parts.append(f"+{int(added or 0)}/-{int(removed or 0)}")
    usd = _number(cost.get("total_cost_usd"), "cost.total_cost_usd")
    if usd is not None:
        parts.append(f"${usd:.2f}")

    line = " | ".join(part for part in parts if part)
    logger.debug("built status line with %d segment(s): %r", len(parts), line)
    return line
