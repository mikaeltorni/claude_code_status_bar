"""status_bar_install.py - install-time Claude Code settings helpers.

Components:
  - configure_status_line: Merge the statusLine command into settings.json.
  - main: CLI entrypoint used by install.sh.
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def _read_settings(settings_file: Path) -> dict[str, Any]:
    """Read Claude settings JSON, returning an empty object when unavailable."""
    try:
        settings = json.loads(settings_file.read_text(encoding="utf-8"))
        if isinstance(settings, dict):
            return settings
        logger.warning("Ignoring non-object Claude settings file: %s", settings_file)
    except Exception as exc:
        logger.warning("Could not read Claude settings from %s: %s", settings_file, exc)
    return {}


def configure_status_line(settings_file: Path, status_script: Path) -> None:
    """Set Claude Code's statusLine command while preserving unrelated keys."""
    settings = _read_settings(settings_file)
    settings["statusLine"] = {
        "type": "command",
        "command": f"python3 {status_script}",
    }
    settings_file.parent.mkdir(parents=True, exist_ok=True)
    settings_file.write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")
    logger.info("Configured Claude Code statusLine in %s", settings_file)


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint used by the shell installer."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 2:
        print("Usage: status_bar_install.py <settings.json> <claude-status-bar>", file=sys.stderr)
        return 2
    configure_status_line(Path(args[0]), Path(args[1]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
