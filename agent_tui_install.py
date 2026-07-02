#!/usr/bin/env python3
"""Preserving installer for native Codex-style TUI status-line configuration."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from agent_tui_catalog import read_status_line_tokens, write_status_line_tokens


def configure_codex(path: Path, tokens: list[str] | None = None) -> None:
    """Set supported rich status fields without replacing other TOML keys."""
    if tokens is None:
        from agent_tui_catalog import CODEX_DEFAULT_FIELDS

        tokens = list(CODEX_DEFAULT_FIELDS)
    write_status_line_tokens(path, tokens)


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) < 2:
        print(
            "Usage: agent_tui_install.py {write|read} CONFIG_PATH [JSON tokens]",
            file=sys.stderr,
        )
        return 2
    command, config_path = args[0], Path(args[1])
    if command == "write":
        if len(args) > 2:
            tokens = json.loads(args[2]) if args[2].startswith("[") else args[2:]
        else:
            from agent_tui_catalog import CODEX_DEFAULT_FIELDS

            tokens = list(CODEX_DEFAULT_FIELDS)
        configure_codex(config_path, list(tokens))
        return 0
    if command == "read":
        tokens = read_status_line_tokens(config_path)
        print(json.dumps(tokens if tokens is not None else []))
        return 0
    print(f"Unknown command: {command}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())