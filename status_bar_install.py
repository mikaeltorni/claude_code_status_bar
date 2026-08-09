"""status_bar_install.py - install-time Claude Code settings helpers.

Components:
  - configure_status_line: Merge the statusLine command into settings.json.
  - main: CLI entrypoint used by install.sh.
"""

from __future__ import annotations

import json
import shlex
import sys
from pathlib import Path
from typing import Any

from status_bar_logging import get_logger, log_call

logger = get_logger(__name__)


@log_call(logger)
def _read_settings(settings_file: Path) -> dict[str, Any]:
    """Read Claude settings JSON, returning an empty object when unavailable.

    Args:
        settings_file: Path to the user's ``settings.json``. May be missing,
            empty, or hold a non-object value.

    Returns:
        dict[str, Any]: The parsed settings object, or an empty dict when the
        file is absent, unreadable, or does not contain a JSON object. Read
        failures are logged at WARNING level rather than raised so the installer
        can recreate the file from scratch.
    """
    try:
        settings = json.loads(settings_file.read_text(encoding="utf-8"))
        if isinstance(settings, dict):
            return settings
        logger.warning("Ignoring non-object Claude settings file: %s", settings_file)
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Could not read Claude settings from %s: %s", settings_file, exc)
    return {}


@log_call(logger)
def configure_status_line(settings_file: Path, status_script: Path) -> None:
    """Set Claude Code's statusLine command while preserving unrelated keys.

    Reads any existing settings, overwrites only the ``statusLine`` key with a
    command that runs ``status_script`` via ``python3``, and writes the merged
    result back (creating parent directories as needed). This is idempotent and
    non-destructive: re-running it leaves every other setting untouched.

    Args:
        settings_file: Path to the user's ``settings.json`` to update in place.
        status_script: Path to the installed ``claude-status-bar`` executable to
            wire in as the status-line command.

    Returns:
        None.
    """
    settings = _read_settings(settings_file)
    settings["statusLine"] = {
        "type": "command",
        "command": f"python3 {shlex.quote(str(status_script))}",
    }
    settings_file.parent.mkdir(parents=True, exist_ok=True)
    settings_file.write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")
    logger.info("Configured Claude Code statusLine in %s", settings_file)


@log_call(logger)
def unconfigure_status_line(settings_file: Path) -> bool:
    """Remove only this repo's ``statusLine`` wiring from Claude's settings.

    The uninstall counterpart of :func:`configure_status_line`. Every other
    setting (theme, permissions, hooks, …) is preserved, and the file is left
    untouched when it does not exist or carries no ``statusLine`` key, so
    uninstalling a component the user never installed is a safe no-op.

    Args:
        settings_file: Path to the user's ``settings.json``.

    Returns:
        bool: ``True`` when a ``statusLine`` key was removed and the file
        rewritten, ``False`` when there was nothing to remove.
    """
    if not settings_file.exists():
        logger.info("No Claude settings at %s; nothing to unwire", settings_file)
        return False
    settings = _read_settings(settings_file)
    if "statusLine" not in settings:
        logger.info("No statusLine key in %s; nothing to unwire", settings_file)
        return False
    del settings["statusLine"]
    settings_file.write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")
    logger.info("Removed Claude Code statusLine from %s", settings_file)
    return True


@log_call(logger)
def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint used by the shell installer.

    Args:
        argv: Optional argument list (excluding the program name). When ``None``,
            ``sys.argv[1:]`` is used. Two forms are accepted: ``<settings.json>
            <claude-status-bar>`` to wire the status line in, and ``--remove
            <settings.json>`` to unwire it during uninstall.

    Returns:
        int: Process exit code -- ``0`` on success, or ``2`` when the wrong
        number of arguments is supplied (usage error printed to stderr).
    """
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) == 2 and args[0] == "--remove":
        unconfigure_status_line(Path(args[1]))
        return 0
    if len(args) != 2:
        print(
            "Usage: status_bar_install.py <settings.json> <claude-status-bar>\n"
            "       status_bar_install.py --remove <settings.json>",
            file=sys.stderr,
        )
        return 2
    configure_status_line(Path(args[0]), Path(args[1]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
