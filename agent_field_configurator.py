#!/usr/bin/env python3
"""Interactive field checklist with a live simulated status-bar preview."""

from __future__ import annotations

import os
import sys
import termios
import tty
from pathlib import Path

from agent_field_selection import (
    COMPONENT_TO_AGENT,
    catalog_for_agent,
    get_fields,
    label_for_field,
    selection_path,
    set_fields,
    toggle_field,
)
from status_bar_preview import preview_for_agent

NATIVE_ONLY_AGENTS = frozenset({"grok", "cline"})


def _read_key() -> str:
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = os.read(fd, 1)
        if ch in (b"\x1b",):
            rest = os.read(fd, 2)
            seq = (ch + rest).decode("utf-8", "replace")
            if seq == "\x1b[A":
                return "UP"
            if seq == "\x1b[B":
                return "DOWN"
            if seq in ("\x1b[C", "\x1b[D"):
                return "IGNORE"
            return "ESC"
        if ch in (b"\r", b"\n"):
            return "ENTER"
        if ch == b" ":
            return "SPACE"
        if ch == b"q":
            return "QUIT"
        return ch.decode("utf-8", "replace")
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


def _clear() -> None:
    sys.stdout.write("\033[2J\033[H")
    sys.stdout.flush()


def _render(agent: str, selected_row: int, fields: list[str], target_home: Path) -> None:
    catalog = catalog_for_agent(agent)
    preview = preview_for_agent(agent, fields, target_home)
    title = {
        "codex": "Codex status bar fields",
        "qwen": "Qwen (local Codex) status bar fields",
        "claude": "Claude Code status bar segments",
        "grok": "Grok native TUI display (reference)",
        "cline": "Cline native TUI display (reference)",
    }.get(agent, agent)
    _clear()
    print(f"  {title}")
    if agent in NATIVE_ONLY_AGENTS:
        print("  Grok/Cline expose no writable status_line keys; toggles affect preview only.\n")
    else:
        print("  Toggle fields with SPACE. ENTER saves, q cancels.\n")
    for index, field_id in enumerate(catalog):
        mark = "›" if index == selected_row else " "
        box = "[x]" if field_id in fields else "[ ]"
        label = label_for_field(agent, field_id)
        print(f"   {mark} {box} {label}")
    print()
    print(f"  Preview: {preview or '(empty)'}")
    print()
    print("  [↑/↓] move  [space] toggle  [enter] save  [q] cancel")


def configure_agent_fields(agent: str, target_home: Path | None = None) -> int:
    agent = COMPONENT_TO_AGENT.get(agent, agent)
    home = target_home or Path(os.environ.get("TARGET_HOME") or Path.home())
    path = selection_path(home)
    fields = get_fields(agent, path)
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        set_fields(agent, fields, path)
        return 0
    row = 0
    catalog = catalog_for_agent(agent)
    while True:
        row = max(0, min(row, max(len(catalog) - 1, 0)))
        _render(agent, row, fields, home)
        key = _read_key()
        if key == "UP":
            row -= 1
        elif key == "DOWN":
            row += 1
        elif key == "SPACE" and catalog:
            fields = toggle_field(agent, catalog[row], path)
        elif key in ("ENTER", "RIGHT"):
            set_fields(agent, fields, path)
            return 0
        elif key in ("QUIT", "ESC", "LEFT"):
            return 1


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        print("Usage: agent_field_configurator.py AGENT [TARGET_HOME]", file=sys.stderr)
        return 2
    home = Path(args[1]) if len(args) > 1 else None
    return configure_agent_fields(args[0], home)


if __name__ == "__main__":
    raise SystemExit(main())