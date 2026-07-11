"""Shared Codex-style TUI status-line catalog and TOML writer.

Codex (``ca``) and Qwen local Codex (``qa``) both use ``[tui] status_line`` in
their config.toml homes. This module is the single source of truth for supported
field tokens, default selections, parsing, and idempotent upserts.
"""

from __future__ import annotations

from pathlib import Path

# Canonical token order for menus and stable TOML output.
CODEX_FIELD_IDS: tuple[str, ...] = (
    "model-with-reasoning",
    "current-dir",
    "project-name",
    "git-branch",
    "context-remaining",
    "five-hour-limit",
    "weekly-limit",
    "run-state",
    "context-used",
    "codex-version",
    "pull-request-number",
    "branch-changes",
    "used-tokens",
    "total-input-tokens",
    "total-output-tokens",
)

# Codex status-line defaults. ``project-name`` is Codex's project-root basename,
# which is the active Git worktree name and matches Claude Code's project
# segment. The branch token stays selectable but is off by default so a branch
# such as ``master`` does not hide the worktree identity. The 5-hour and weekly
# rate-limit fields stay off (the dedicated taskbar bar owns those quotas).
# run-state, context-used, codex-version, and pull-request-number are also off
# by default to keep the line focused. All of these remain selectable.
CODEX_DEFAULT_OFF: tuple[str, ...] = (
    "five-hour-limit",
    "weekly-limit",
    "git-branch",
    "run-state",
    "context-used",
    "codex-version",
    "pull-request-number",
)
CODEX_DEFAULT_FIELDS: tuple[str, ...] = tuple(
    token for token in CODEX_FIELD_IDS if token not in CODEX_DEFAULT_OFF
)

# The Local/Qwen (qa), OpenRouter (oa), and NVIDIA (na) isolated Codex
# instances share the same rich native status line as Codex (worktree name,
# tokens used, input/output token totals, branch changes, ...), excluding the
# 5-hour/weekly rate-limit and branch fields which the dedicated taskbar bar
# owns or which are intentionally not part of the default identity display.
QWEN_DEFAULT_FIELDS: tuple[str, ...] = CODEX_DEFAULT_FIELDS

CODEX_FIELD_LABELS: dict[str, str] = {
    "model-with-reasoning": "Model + reasoning effort",
    "current-dir": "Current directory",
    "project-name": "Project / worktree name",
    "git-branch": "Git branch",
    "context-remaining": "Context remaining",
    "five-hour-limit": "5-hour rate limit",
    "weekly-limit": "Weekly rate limit",
    "run-state": "Run state",
    "context-used": "Context used",
    "codex-version": "Codex version",
    "pull-request-number": "Pull request number",
    "branch-changes": "Branch changes",
    "used-tokens": "Used tokens",
    "total-input-tokens": "Total input tokens",
    "total-output-tokens": "Total output tokens",
}


def normalize_tokens(tokens: list[str] | tuple[str, ...]) -> list[str]:
    """Return valid tokens in canonical catalog order."""
    wanted = set(tokens)
    return [token for token in CODEX_FIELD_IDS if token in wanted]


def format_status_line_array(tokens: list[str]) -> str:
    """Format a TOML array assignment value for status_line."""
    ordered = normalize_tokens(tokens)
    inner = ",".join(f'"{token}"' for token in ordered)
    return f"[{inner}]"


def read_status_line_tokens(path: Path) -> list[str] | None:
    """Read enabled status-line tokens from a Codex config.toml."""
    if not path.exists():
        return None
    in_tui = False
    tokens: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        if line == "[tui]":
            in_tui = True
            continue
        if line.startswith("[") and line.endswith("]"):
            in_tui = False
            continue
        if not in_tui:
            continue
        key, _, value = line.partition("=")
        if key.strip() != "status_line":
            continue
        value = value.strip()
        if not (value.startswith("[") and value.endswith("]")):
            continue
        body = value[1:-1].strip()
        if not body:
            return []
        parts: list[str] = []
        for item in body.split(","):
            item = item.strip().strip('"').strip("'")
            if item in CODEX_FIELD_IDS:
                parts.append(item)
        return normalize_tokens(parts)
    return None


def write_status_line_tokens(path: Path, tokens: list[str]) -> None:
    """Upsert ``[tui] status_line`` without replacing unrelated TOML keys."""
    ordered = normalize_tokens(tokens)
    status = f"status_line = {format_status_line_array(ordered)}\n"
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True) if path.exists() else []
    start = next((i for i, line in enumerate(lines) if line.strip() == "[tui]"), None)
    if start is None:
        text = "".join(lines).rstrip() + ("\n\n" if lines else "") + "[tui]\n" + status
    else:
        end = next(
            (i for i in range(start + 1, len(lines)) if lines[i].lstrip().startswith("[")),
            len(lines),
        )
        item = next(
            (
                i
                for i in range(start + 1, end)
                if lines[i].split("#", 1)[0].partition("=")[0].strip() == "status_line"
            ),
            None,
        )
        if item is None:
            lines.insert(start + 1, status)
        else:
            lines[item] = status
        text = "".join(lines)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    path.chmod(0o600)
