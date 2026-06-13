"""Status-line assembly for the Claude Code status bar."""

import os

from status_bar_format import format_reset, format_reset_day, format_tokens


def build_status_line(data: dict) -> str:
    """Build the status-bar text from a Claude Code status-line payload.

    Args:
        data: Parsed status-line JSON object supplied by Claude Code.

    Returns:
        A pipe-delimited status line. Missing values are omitted.
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
    used = ctx.get("total_input_tokens")
    size = ctx.get("context_window_size")
    pct = ctx.get("used_percentage")
    if used is not None and size:
        ctx_str = f"{format_tokens(used)}/{format_tokens(size)}"
        if pct is not None:
            ctx_str += f" ({pct}%)"
        parts.append(ctx_str)

    # Rate limits — 5-hour and weekly windows, shown as remaining (100 - used).
    rl = data.get("rate_limits") or {}
    five = rl.get("five_hour") or {}
    if five.get("used_percentage") is not None:
        reset = format_reset(five.get("resets_at"))
        parts.append(f"5h:{round(100 - five['used_percentage'])}%" + (f" (~{reset})" if reset else ""))
    week = rl.get("seven_day") or {}
    if week.get("used_percentage") is not None:
        reset_day = format_reset_day(week.get("resets_at"))
        suffix = f" ({reset_day})" if reset_day else ""
        parts.append(f"wk:{round(100 - week['used_percentage'])}%" + suffix)

    # Diff count and total cost.
    cost = data.get("cost") or {}
    added = cost.get("total_lines_added")
    removed = cost.get("total_lines_removed")
    if added is not None or removed is not None:
        parts.append(f"+{added or 0}/-{removed or 0}")
    usd = cost.get("total_cost_usd")
    if usd is not None:
        parts.append(f"${usd:.2f}")

    return " | ".join(part for part in parts if part)
