"""Simulated status-bar previews for all five agent TUIs."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from agent_field_selection import (
    COMPONENT_TO_AGENT,
    catalog_for_agent,
    get_fields,
    label_for_field,
    selection_path,
)
from status_bar_render import build_status_line

CLAUDE_FIXTURE: dict = {
    "model": {"display_name": "Opus"},
    "effort": {"level": "low"},
    "workspace": {"project_dir": "/home/u/claude_code_status_bar"},
    "context_window": {
        "total_input_tokens": 63249,
        "total_output_tokens": 5120,
        "context_window_size": 200000,
        "used_percentage": 31,
    },
    "rate_limits": {
        "five_hour": {"used_percentage": 10, "resets_at": 99999999999},
        "seven_day": {"used_percentage": 40, "resets_at": 99999999999},
    },
    "cost": {"total_lines_added": 120, "total_lines_removed": 8, "total_cost_usd": 1.42},
}

CODEX_FIXTURE: dict[str, str] = {
    "model-with-reasoning": "gpt-5.5 · low",
    "current-dir": "claude_code_status_bar",
    "git-branch": "master",
    "context-remaining": "69% ctx",
    "five-hour-limit": "5h:90%",
    "weekly-limit": "wk:60%",
    "run-state": "idle",
    "context-used": "63.2k/200.0k",
    "codex-version": "codex 0.42",
    "pull-request-number": "PR #128",
    "branch-changes": "+12/-3",
    "used-tokens": "63.2k used",
    "total-input-tokens": "in:58.1k",
    "total-output-tokens": "out:5.1k",
}

QWEN_FIXTURE: dict[str, str] = {
    **CODEX_FIXTURE,
    "model-with-reasoning": "ornstein3.6-35b · high",
    "current-dir": "agent_command_center",
    "context-remaining": "42% ctx",
}

OPENROUTER_FIXTURE: dict[str, str] = {
    **CODEX_FIXTURE,
    "model-with-reasoning": "tencent/hy3:free · high",
    "current-dir": "agent_command_center",
    "context-remaining": "42% ctx",
}

NVIDIA_FIXTURE: dict[str, str] = {
    **CODEX_FIXTURE,
    "model-with-reasoning": "deepseek-ai/deepseek-v4-pro · high",
    "current-dir": "agent_command_center",
    "context-remaining": "42% ctx",
}

GROK_FIXTURE: dict[str, str] = {
    "model": "grok-build",
    "working-directory": "installation_scripts",
    "session-state": "ready",
    "context-usage": "18% ctx",
    "tool-activity": "2 tools",
}

CLINE_FIXTURE: dict[str, str] = {
    "model": "claude-sonnet-4",
    "workspace": "linux_programming_setup",
    "context-window": "41% ctx",
    "session-cost": "$0.84",
    "diff-stats": "+45/-6",
}


def _join_segments(parts: list[str]) -> str:
    return " · ".join(part for part in parts if part)


def preview_codex_tokens(tokens: list[str], fixture: dict[str, str]) -> str:
    parts = [fixture[token] for token in tokens if token in fixture]
    return _join_segments(parts)


def preview_claude_segments(segments: list[str]) -> str:
    import status_bar_render as render_mod

    original = render_mod.enabled_segments
    try:
        render_mod.enabled_segments = lambda: set(segments)  # type: ignore[method-assign]
        return build_status_line(CLAUDE_FIXTURE)
    finally:
        render_mod.enabled_segments = original  # type: ignore[method-assign]


def preview_for_agent(agent: str, fields: list[str] | None = None, target_home: Path | None = None) -> str:
    agent = COMPONENT_TO_AGENT.get(agent, agent)
    selected = list(fields or get_fields(agent, selection_path(target_home)))
    if agent == "codex":
        return preview_codex_tokens(selected, CODEX_FIXTURE)
    if agent == "qwen":
        return preview_codex_tokens(selected, QWEN_FIXTURE)
    if agent == "openrouter":
        return preview_codex_tokens(selected, OPENROUTER_FIXTURE)
    if agent == "nvidia":
        return preview_codex_tokens(selected, NVIDIA_FIXTURE)
    if agent == "claude":
        return preview_claude_segments(selected)
    if agent == "grok":
        return preview_codex_tokens(selected, GROK_FIXTURE)
    if agent == "cline":
        return preview_codex_tokens(selected, CLINE_FIXTURE)
    return ""


def preview_for_component(component_id: str, target_home: Path | None = None) -> str:
    agent = COMPONENT_TO_AGENT.get(component_id)
    if not agent:
        return ""
    return preview_for_agent(agent, target_home=target_home)


AGGREGATE_AGENT_LABELS: tuple[tuple[str, str], ...] = (
    ("codex", "Codex"),
    ("qwen", "Qwen"),
    ("openrouter", "OpenRouter"),
    ("nvidia", "NVIDIA"),
    ("claude", "Claude"),
    ("grok", "Grok"),
    ("cline", "Cline"),
)


def preview_all_agents(target_home: Path | None = None) -> str:
    """Return a multi-line summary of all five agent previews (menu order)."""
    parts: list[str] = []
    for agent, label in AGGREGATE_AGENT_LABELS:
        line = preview_for_agent(agent, target_home=target_home)
        if line:
            parts.append(f"[{label}] {line}")
    return "\n".join(parts)


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        print("Usage: status_bar_preview.py {codex|qwen|openrouter|nvidia|claude|grok|cline|component} ...", file=sys.stderr)
        return 2
    command = args[0]
    if command == "component":
        component = args[1] if len(args) > 1 else ""
        home = Path(args[2]) if len(args) > 2 else None
        print(preview_for_component(component, home))
        return 0
    if command == "aggregate":
        home = Path(args[1]) if len(args) > 1 else None
        print(preview_all_agents(home))
        return 0
    home = Path(args[2]) if len(args) > 2 and str(args[2]).startswith(("/", ".")) else None
    if len(args) > 1 and args[1].startswith("["):
        fields = json.loads(args[1])
    else:
        fields = get_fields(command, selection_path(home))
    print(preview_for_agent(command, fields, home))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())