"""status_bar_logging.py - centralized logging for the Claude Code status bar.

The status bar must print exactly one line to stdout, so every diagnostic is
routed to a file and is opt-in: nothing is logged unless the environment
variable ``CLAUDE_STATUS_BAR_DEBUG`` is set to a truthy value. When enabled,
log records are written to ``<module-dir>/.log/status-bar.log`` with timestamps
and never touch stdout or stderr, keeping the status-line hot path silent and
fast by default.

Components:
  - debug_enabled: Report whether file logging is currently enabled.
  - get_logger: Return a namespaced logger wired to the shared file handler.

Usage example:
    from status_bar_logging import get_logger

    logger = get_logger(__name__)
    logger.debug("rendering status line with %d parts", len(parts))
"""

from __future__ import annotations

import logging
import os

# Environment values that disable logging (anything else enables it).
_DISABLED_VALUES = ("", "0", "false", "no")

# Shared logger namespace and on-disk artifacts.
_ROOT_LOGGER_NAME = "status_bar"
_LOG_DIR_NAME = ".log"
_LOG_FILE_NAME = "status-bar.log"

# Guards the one-time handler configuration performed by ``_configure``.
_configured = False


def debug_enabled() -> bool:
    """Report whether opt-in file logging is currently enabled.

    Returns:
        bool: ``True`` when ``CLAUDE_STATUS_BAR_DEBUG`` is set to a truthy
        value, otherwise ``False``.
    """
    return os.environ.get("CLAUDE_STATUS_BAR_DEBUG", "") not in _DISABLED_VALUES


def _log_dir() -> str:
    """Return the absolute path of the repository-local ``.log`` directory.

    Returns:
        str: ``<module-dir>/.log``, the only location status-bar logs are
        written to (kept beside the modules so it works both in the repository
        and in the installed ``~/.claude`` copy).
    """
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), _LOG_DIR_NAME)


def _configure() -> None:
    """Configure the shared ``status_bar`` logger exactly once.

    When logging is disabled (the default), a :class:`logging.NullHandler` is
    attached and the level is raised above all records so logging calls become
    cheap no-ops. When enabled, a single :class:`logging.FileHandler` writing to
    ``<module-dir>/.log/status-bar.log`` is attached. Any filesystem failure is
    swallowed and downgraded to the silent null handler so diagnostics can never
    break the status line.

    Returns:
        None.
    """
    global _configured
    if _configured:
        return
    _configured = True

    root = logging.getLogger(_ROOT_LOGGER_NAME)
    root.propagate = False  # Never bubble to the stderr "last resort" handler.

    if not debug_enabled():
        root.addHandler(logging.NullHandler())
        root.setLevel(logging.CRITICAL + 1)
        return

    try:
        os.makedirs(_log_dir(), exist_ok=True)
        handler = logging.FileHandler(
            os.path.join(_log_dir(), _LOG_FILE_NAME), encoding="utf-8"
        )
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s %(levelname)s %(name)s: %(message)s",
                "%Y-%m-%d %H:%M:%S",
            )
        )
        root.addHandler(handler)
        root.setLevel(logging.DEBUG)
    except OSError:
        # Logging is best-effort; fall back to silence rather than crashing.
        root.handlers.clear()
        root.addHandler(logging.NullHandler())
        root.setLevel(logging.CRITICAL + 1)


def _reset_for_tests() -> None:
    """Drop the cached configuration so the next ``get_logger`` reconfigures.

    Intended only for tests that need to exercise a patched ``_log_dir`` or a
    changed debug environment within a single process.

    Returns:
        None.
    """
    global _configured
    logging.getLogger(_ROOT_LOGGER_NAME).handlers.clear()
    _configured = False


def get_logger(name: str) -> logging.Logger:
    """Return a logger namespaced under the shared ``status_bar`` logger.

    Args:
        name: Caller module name (typically ``__name__``); used as the child
            logger suffix so records are attributed to their source module.

    Returns:
        logging.Logger: A configured logger that writes to the shared file
        handler when debug logging is enabled, and is otherwise silent.
    """
    _configure()
    return logging.getLogger(f"{_ROOT_LOGGER_NAME}.{name}")
