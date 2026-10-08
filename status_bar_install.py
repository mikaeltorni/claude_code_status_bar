"""status_bar_install.py - install-time Claude Code settings helpers.

Components:
  - configure_status_line: Merge the statusLine command into settings.json.
  - ensure_project_trust / ensure_known_projects_trust: Mark workspaces trusted
    so Claude Code actually invokes statusLine (it skips the command when
    workspace trust has not been accepted for that git root).
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

# Claude Code re-runs the statusLine command every N seconds in addition to
# event-driven updates so model/context usage stay current while idle at the
# prompt. Minimum accepted by Claude is 1.
STATUS_LINE_REFRESH_INTERVAL_SECONDS = 5


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
    command that runs the installed ``status_script`` executable, and writes the merged
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
        "command": shlex.quote(str(status_script)),
        "refreshInterval": STATUS_LINE_REFRESH_INTERVAL_SECONDS,
    }
    settings_file.parent.mkdir(parents=True, exist_ok=True)
    settings_file.write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")
    logger.info(
        "Configured Claude Code statusLine in %s (refreshInterval=%ss)",
        settings_file,
        STATUS_LINE_REFRESH_INTERVAL_SECONDS,
    )


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


def _read_claude_json(claude_json: Path) -> dict[str, Any]:
    """Load ``~/.claude.json`` project state, or an empty object when missing."""
    try:
        data = json.loads(claude_json.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
        logger.warning("Ignoring non-object Claude config: %s", claude_json)
    except FileNotFoundError:
        return {}
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Could not read Claude config from %s: %s", claude_json, exc)
    return {}


@log_call(logger)
def ensure_project_trust(claude_json: Path, project_path: str | Path) -> bool:
    """Mark a workspace trusted so Claude Code will run the statusLine command.

    Claude Code skips ``statusLine`` (and hooks) when
    ``projects[<git-root>].hasTrustDialogAccepted`` is not true for the session
    working directory. Accepting trust here is the non-interactive equivalent of
    answering the first-run trust dialog, which is required for the installed
    bar to appear at all.

    Args:
        claude_json: Path to the user's ``~/.claude.json`` (or a test copy).
        project_path: Absolute or relative project directory to trust. Resolved
            before writing so keys match Claude Code's path normalization.

    Returns:
        bool: ``True`` when the file was written because trust was newly set
        (or the project entry was created), ``False`` when it was already
        trusted or the path could not be resolved.
    """
    try:
        key = str(Path(project_path).expanduser().resolve())
    except OSError as exc:
        logger.warning("Cannot resolve project path %s: %s", project_path, exc)
        return False

    data = _read_claude_json(claude_json)
    projects = data.setdefault("projects", {})
    if not isinstance(projects, dict):
        projects = {}
        data["projects"] = projects

    entry = projects.get(key)
    if not isinstance(entry, dict):
        entry = {}
        projects[key] = entry

    if entry.get("hasTrustDialogAccepted") is True:
        logger.debug("Project already trusted: %s", key)
        return False

    entry["hasTrustDialogAccepted"] = True
    claude_json.parent.mkdir(parents=True, exist_ok=True)
    claude_json.write_text(json.dumps(data) + "\n", encoding="utf-8")
    logger.info("Accepted Claude workspace trust for %s in %s", key, claude_json)
    return True


@log_call(logger)
def ensure_known_projects_trust(claude_json: Path) -> list[str]:
    """Trust every project path already recorded in ``claude.json`` that still exists.

    Used at install time so workspaces the user has already opened with Claude
    Code (but never answered the trust dialog for) start running statusLine
    after a reinstall. Paths that no longer exist on disk are left unchanged.

    Args:
        claude_json: Path to the user's ``~/.claude.json`` (or a test copy).

    Returns:
        list[str]: Absolute project paths whose trust flag was newly set.
    """
    data = _read_claude_json(claude_json)
    projects = data.get("projects")
    if not isinstance(projects, dict) or not projects:
        logger.info("No projects in %s; nothing to trust", claude_json)
        return []

    updated: list[str] = []
    for raw_key in list(projects.keys()):
        path = Path(str(raw_key)).expanduser()
        try:
            if not path.is_dir():
                continue
            if ensure_project_trust(claude_json, path):
                updated.append(str(path.resolve()))
        except OSError as exc:
            logger.debug("Skipping project %s: %s", raw_key, exc)

    if updated:
        logger.info(
            "Accepted Claude workspace trust for %d project(s) via %s",
            len(updated),
            claude_json,
        )
    return updated


@log_call(logger)
def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint used by the shell installer.

    Args:
        argv: Optional argument list (excluding the program name). When ``None``,
            ``sys.argv[1:]`` is used. Accepted forms:

            - ``<settings.json> <claude-status-bar>`` — wire statusLine in
            - ``--remove <settings.json>`` — unwire statusLine on uninstall
            - ``--ensure-trust <claude.json> <project-path>`` — trust one workspace
            - ``--ensure-known-trust <claude.json>`` — trust all known existing paths

    Returns:
        int: Process exit code -- ``0`` on success, or ``2`` when the wrong
        number of arguments is supplied (usage error printed to stderr).
    """
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) == 2 and args[0] == "--remove":
        unconfigure_status_line(Path(args[1]))
        return 0
    if len(args) == 3 and args[0] == "--ensure-trust":
        ensure_project_trust(Path(args[1]), args[2])
        return 0
    if len(args) == 2 and args[0] == "--ensure-known-trust":
        ensure_known_projects_trust(Path(args[1]))
        return 0
    if len(args) != 2:
        print(
            "Usage: status_bar_install.py <settings.json> <claude-status-bar>\n"
            "       status_bar_install.py --remove <settings.json>\n"
            "       status_bar_install.py --ensure-trust <claude.json> <project-path>\n"
            "       status_bar_install.py --ensure-known-trust <claude.json>",
            file=sys.stderr,
        )
        return 2
    configure_status_line(Path(args[0]), Path(args[1]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
