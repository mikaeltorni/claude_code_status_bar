#!/usr/bin/env python3
"""Preserving installer for native Codex TUI status-line configuration."""

from pathlib import Path
import sys


def configure_codex(path: Path) -> None:
    """Set the supported rich status fields without replacing other TOML keys."""
    lines = path.read_text().splitlines(keepends=True) if path.exists() else []
    status = 'status_line = ["model-with-reasoning","current-dir","git-branch","context-remaining","five-hour-limit","weekly-limit"]\n'
    start = next((i for i, line in enumerate(lines) if line.strip() == "[tui]"), None)
    if start is None:
        text = "".join(lines).rstrip() + ("\n\n" if lines else "") + "[tui]\n" + status
    else:
        end = next((i for i in range(start + 1, len(lines)) if lines[i].lstrip().startswith("[")), len(lines))
        item = next((i for i in range(start + 1, end) if lines[i].split("#", 1)[0].partition("=")[0].strip() == "status_line"), None)
        if item is None:
            lines.insert(start + 1, status)
        else:
            lines[item] = status
        text = "".join(lines)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    path.chmod(0o600)


if __name__ == "__main__":
    configure_codex(Path(sys.argv[1]))
