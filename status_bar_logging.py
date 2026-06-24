"""status_bar_logging.py - centralized logging for the Claude Code status bar.

The status bar must print exactly one line to stdout, so every diagnostic is
routed to a file and never touches stdout or stderr. Logging is **on by
default**: records are written to ``<module-dir>/.log/status-bar.log`` with
timestamps on every run. Setting ``CLAUDE_STATUS_BAR_DEBUG`` to a falsy value
(``0``, ``false``, ``no``, or the empty string) opts out, replacing the file
handler with a silent null handler for the rare case where on-disk diagnostics
are unwanted.

Components:
  - debug_enabled: Report whether file logging is currently enabled.
  - get_logger: Return a namespaced logger wired to the shared file handler.
  - log_call: Decorate selected functions with standard argument/return tracing.

Usage example:
    from status_bar_logging import get_logger

    logger = get_logger(__name__)
    logger.debug("rendering status line with %d parts", len(parts))
"""

from __future__ import annotations

import functools
import inspect
import logging
import os
from pathlib import Path
from typing import Any, Callable, TypeVar

# Environment values that disable logging (anything else, including unset,
# enables it). Logging defaults to on per the always-on diagnostics policy.
_DISABLED_VALUES = ("", "0", "false", "no")

# Shared logger namespace and on-disk artifacts.
_ROOT_LOGGER_NAME = "status_bar"
_LOG_DIR_NAME = ".log"
_LOG_FILE_NAME = "status-bar.log"

# Guards the one-time handler configuration performed by ``_configure``.
_configured = False
F = TypeVar("F", bound=Callable[..., Any])


def debug_enabled() -> bool:
    """Report whether file logging is currently enabled.

    Logging is on by default; it is disabled only when
    ``CLAUDE_STATUS_BAR_DEBUG`` is explicitly set to a falsy value.

    Returns:
        bool: ``True`` unless ``CLAUDE_STATUS_BAR_DEBUG`` is set to ``0``,
        ``false``, ``no``, or the empty string.
    """
    return os.environ.get("CLAUDE_STATUS_BAR_DEBUG", "1").lower() not in _DISABLED_VALUES


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

    When logging is disabled (opt-out via ``CLAUDE_STATUS_BAR_DEBUG``), a
    :class:`logging.NullHandler` is attached and the level is raised above all
    records so logging calls become cheap no-ops. When enabled (the default), a
    single :class:`logging.FileHandler` writing to
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
    root.handlers.clear()

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


def log_call(logger: logging.Logger, level: int = logging.DEBUG) -> Callable[[F], F]:
    """Trace a function call by logging bound arguments on entry and return.

    Each record includes ``file:qualname`` for the wrapped function so status-bar
    diagnostics are searchable without scattering hardcoded context strings
    through feature modules. The decorator logs nothing beyond the entry
    arguments and exit value.

    Args:
        logger: Centralized logger returned by :func:`get_logger`.
        level: Logging level for the entry and exit records.

    Returns:
        Callable[[F], F]: A decorator for the target function.
    """

    def decorator(func: F) -> F:
        location = f"{Path(func.__code__.co_filename).name}:{func.__qualname__}"
        signature = inspect.signature(func)

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            bound = signature.bind(*args, **kwargs)
            bound.apply_defaults()
            rendered = ", ".join(
                f"{name}={value!r}" for name, value in bound.arguments.items()
            )
            logger.log(level, "ENTER %s(%s)", location, rendered)
            result = func(*args, **kwargs)
            logger.log(level, "EXIT %s -> %r", location, result)
            return result

        return wrapper  # type: ignore[return-value]

    return decorator
