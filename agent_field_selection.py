"""Persist per-agent TUI field selections for the status-bar installer."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from agent_tui_catalog import CODEX_DEFAULT_FIELDS, QWEN_DEFAULT_FIELDS, format_status_line_array
from status_bar_config import SEGMENT_IDS

AGENT_IDS: tuple[str, ...] = ("codex", "qwen", "openrouter", "nvidia", "claude", "grok", "cline")

COMPONENT_TO_AGENT: dict[str, str] = {
    "codex_tui": "codex",
    "qwen_tui": "qwen",
    "openrouter_tui": "openrouter",
    "nvidia_tui": "nvidia",
    "claude_tui": "claude",
    "grok_tui": "grok",
    "cline_tui": "cline",
}

# Native rich-display elements documented for agents without writable status_line keys.
GROK_FIELD_IDS: tuple[str, ...] = (
    "model",
    "working-directory",
    "session-state",
    "context-usage",
    "tool-activity",
)

CLINE_FIELD_IDS: tuple[str, ...] = (
    "model",
    "workspace",
    "context-window",
    "session-cost",
    "diff-stats",
)

# Claude Code status bar default segments. The 5-hour and weekly rate-limit
# segments are intentionally omitted from the default: those quotas now have a
# dedicated taskbar bar, so the CLI status line stays uncluttered by default.
# Both remain selectable in the field menu for anyone who wants them back.
CLAUDE_DEFAULT_FIELDS: tuple[str, ...] = tuple(
    seg for seg in SEGMENT_IDS if seg not in ("five_hour", "weekly")
)

GROK_DEFAULT_FIELDS: tuple[str, ...] = GROK_FIELD_IDS
CLINE_DEFAULT_FIELDS: tuple[str, ...] = CLINE_FIELD_IDS

GROK_FIELD_LABELS: dict[str, str] = {
    "model": "Active model",
    "working-directory": "Working directory",
    "session-state": "Session / turn state",
    "context-usage": "Context usage",
    "tool-activity": "Tool activity indicator",
}

CLINE_FIELD_LABELS: dict[str, str] = {
    "model": "Active model",
    "workspace": "Workspace / project",
    "context-window": "Context window usage",
    "session-cost": "Session cost",
    "diff-stats": "Diff line statistics",
}

DEFAULTS: dict[str, list[str]] = {
    "codex": list(CODEX_DEFAULT_FIELDS),
    "qwen": list(QWEN_DEFAULT_FIELDS),
    # OpenRouter Codex (oa) shares the Codex/Qwen field catalog and defaults.
    "openrouter": list(QWEN_DEFAULT_FIELDS),
    # NVIDIA Codex (na) shares the Codex/Qwen field catalog and defaults: the
    # full Codex rich status line minus the rate-limit segments.
    "nvidia": list(QWEN_DEFAULT_FIELDS),
    "claude": list(CLAUDE_DEFAULT_FIELDS),
    "grok": list(GROK_DEFAULT_FIELDS),
    "cline": list(CLINE_DEFAULT_FIELDS),
}


def selection_path(target_home: str | Path | None = None) -> Path:
    home = Path(target_home or os.environ.get("TARGET_HOME") or Path.home())
    return home / ".config" / "claude_code_status_bar" / "field-selections.json"


def _empty_document() -> dict[str, list[str]]:
    return {agent: list(DEFAULTS[agent]) for agent in AGENT_IDS}


def load_document(path: Path | None = None) -> dict[str, list[str]]:
    path = path or selection_path()
    if not path.exists():
        return _empty_document()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return _empty_document()
    doc = _empty_document()
    if isinstance(raw, dict):
        for agent in AGENT_IDS:
            values = raw.get(agent)
            if isinstance(values, list):
                doc[agent] = [str(v) for v in values]
    return doc


def save_document(doc: dict[str, list[str]], path: Path | None = None) -> None:
    path = path or selection_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    normalized = {agent: doc.get(agent, list(DEFAULTS[agent])) for agent in AGENT_IDS}
    path.write_text(json.dumps(normalized, indent=2) + "\n", encoding="utf-8")
    path.chmod(0o600)


def get_fields(agent: str, path: Path | None = None) -> list[str]:
    agent = COMPONENT_TO_AGENT.get(agent, agent)
    doc = load_document(path)
    return list(doc.get(agent, DEFAULTS.get(agent, [])))


def set_fields(agent: str, fields: list[str], path: Path | None = None) -> None:
    agent = COMPONENT_TO_AGENT.get(agent, agent)
    path = path or selection_path()
    doc = load_document(path)
    doc[agent] = list(fields)
    save_document(doc, path)


def toggle_field(agent: str, field_id: str, path: Path | None = None) -> list[str]:
    agent = COMPONENT_TO_AGENT.get(agent, agent)
    path = path or selection_path()
    doc = load_document(path)
    current = list(doc.get(agent, DEFAULTS.get(agent, [])))
    if field_id in current:
        current = [item for item in current if item != field_id]
    else:
        current.append(field_id)
    doc[agent] = current
    save_document(doc, path)
    return current


def catalog_for_agent(agent: str) -> tuple[str, ...]:
    agent = COMPONENT_TO_AGENT.get(agent, agent)
    if agent in ("codex", "qwen", "openrouter", "nvidia"):
        from agent_tui_catalog import CODEX_FIELD_IDS

        return CODEX_FIELD_IDS
    if agent == "claude":
        return SEGMENT_IDS
    if agent == "grok":
        return GROK_FIELD_IDS
    if agent == "cline":
        return CLINE_FIELD_IDS
    raise KeyError(agent)


def label_for_field(agent: str, field_id: str) -> str:
    agent = COMPONENT_TO_AGENT.get(agent, agent)
    if agent in ("codex", "qwen", "openrouter", "nvidia"):
        from agent_tui_catalog import CODEX_FIELD_LABELS

        return CODEX_FIELD_LABELS.get(field_id, field_id)
    if agent == "claude":
        return {
            "model": "Model + reasoning effort",
            "project": "Repository / workspace",
            "context": "Context window",
            "five_hour": "5-hour rate limit",
            "weekly": "Weekly rate limit",
            "diff": "Diff line count",
            "tokens": "Token in/out counts",
            "cost": "Session cost",
        }.get(field_id, field_id)
    if agent == "grok":
        return GROK_FIELD_LABELS.get(field_id, field_id)
    if agent == "cline":
        return CLINE_FIELD_LABELS.get(field_id, field_id)
    return field_id


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) < 2:
        print(
            "Usage: agent_field_selection.py {get|set|toggle|path} AGENT [FIELD] [PATH]",
            file=sys.stderr,
        )
        return 2
    command, agent = args[0], args[1]
    path = Path(args[-1]) if len(args) >= 3 and args[-1].startswith(("/", ".")) else None
    if command == "path":
        print(selection_path(path or (args[2] if len(args) > 2 else None)))
        return 0
    if command == "init":
        home = Path(args[1]) if len(args) > 1 else None
        save_document(_empty_document(), selection_path(home))
        return 0
    if command == "toml-array":
        home = Path(args[2]) if len(args) > 2 else None
        fields = get_fields(agent, selection_path(home))
        print(format_status_line_array(fields))
        return 0
    if command == "get":
        print(json.dumps(get_fields(agent, path)))
        return 0
    if command == "set":
        if len(args) < 3:
            print("Usage: agent_field_selection.py set AGENT JSON [PATH]", file=sys.stderr)
            return 2
        fields = json.loads(args[2])
        set_fields(agent, [str(item) for item in fields], path)
        return 0
    if command == "toggle":
        if len(args) < 3:
            print("Usage: agent_field_selection.py toggle AGENT FIELD [PATH]", file=sys.stderr)
            return 2
        print(json.dumps(toggle_field(agent, args[2], path)))
        return 0
    print(f"Unknown command: {command}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())