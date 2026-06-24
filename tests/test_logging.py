"""Tests for the centralized status-bar logging utility."""

from __future__ import annotations

import importlib
import logging

import status_bar_logging


def _fresh_module(monkeypatch, *, debug: str | None):
    """Reload ``status_bar_logging`` with a controlled debug environment.

    Args:
        monkeypatch: Pytest fixture used to set or clear the debug env var.
        debug: Value to assign to ``CLAUDE_STATUS_BAR_DEBUG``; ``None`` clears
            it so the default (enabled) behavior is exercised.

    Returns:
        The freshly reloaded ``status_bar_logging`` module, ensuring its
        one-time handler configuration runs against the patched environment.
    """
    if debug is None:
        monkeypatch.delenv("CLAUDE_STATUS_BAR_DEBUG", raising=False)
    else:
        monkeypatch.setenv("CLAUDE_STATUS_BAR_DEBUG", debug)
    return importlib.reload(status_bar_logging)


def test_debug_enabled_reflects_environment(monkeypatch):
    # Logging is on by default (unset) and only an explicit falsy value opts out.
    assert _fresh_module(monkeypatch, debug=None).debug_enabled() is True
    assert _fresh_module(monkeypatch, debug="0").debug_enabled() is False
    assert _fresh_module(monkeypatch, debug="FALSE").debug_enabled() is False
    assert _fresh_module(monkeypatch, debug="").debug_enabled() is False
    assert _fresh_module(monkeypatch, debug="1").debug_enabled() is True


def test_get_logger_namespaces_under_status_bar(monkeypatch):
    mod = _fresh_module(monkeypatch, debug="0")
    logger = mod.get_logger("status_bar_render")
    assert isinstance(logger, logging.Logger)
    assert logger.name == "status_bar.status_bar_render"


def test_disabled_logging_is_silent(monkeypatch, capsys):
    mod = _fresh_module(monkeypatch, debug="0")
    mod.get_logger("noisy").error("this must never reach stderr")
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""


def test_default_logging_never_reaches_stdout_or_stderr(monkeypatch, capsys, tmp_path):
    # Even with logging on by default, records go to the file, never the streams.
    monkeypatch.delenv("CLAUDE_STATUS_BAR_DEBUG", raising=False)
    mod = importlib.reload(status_bar_logging)
    monkeypatch.setattr(mod, "_log_dir", lambda: str(tmp_path / ".log"))
    mod._reset_for_tests()
    mod.get_logger("noisy").error("file only, please")
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""
    assert "file only, please" in (tmp_path / ".log" / "status-bar.log").read_text(
        encoding="utf-8"
    )


def test_enabled_logging_writes_to_repo_log_dir(monkeypatch, tmp_path):
    monkeypatch.setenv("CLAUDE_STATUS_BAR_DEBUG", "1")
    mod = importlib.reload(status_bar_logging)
    monkeypatch.setattr(mod, "_log_dir", lambda: str(tmp_path / ".log"))
    mod._reset_for_tests()  # force reconfiguration against the patched directory
    mod.get_logger("writer").info("hello log")

    log_file = tmp_path / ".log" / "status-bar.log"
    assert log_file.exists()
    assert "hello log" in log_file.read_text(encoding="utf-8")


def test_reconfiguration_does_not_duplicate_handlers(monkeypatch, tmp_path):
    monkeypatch.setenv("CLAUDE_STATUS_BAR_DEBUG", "1")
    mod = importlib.reload(status_bar_logging)
    monkeypatch.setattr(mod, "_log_dir", lambda: str(tmp_path / ".log"))

    mod._reset_for_tests()
    first = mod.get_logger("first")
    handler_count = len(logging.getLogger("status_bar").handlers)

    mod = importlib.reload(status_bar_logging)
    monkeypatch.setattr(mod, "_log_dir", lambda: str(tmp_path / ".log"))
    second = mod.get_logger("second")

    assert first.name == "status_bar.first"
    assert second.name == "status_bar.second"
    assert len(logging.getLogger("status_bar").handlers) == handler_count


def test_log_call_records_arguments_and_return_value(monkeypatch, tmp_path):
    monkeypatch.setenv("CLAUDE_STATUS_BAR_DEBUG", "1")
    mod = importlib.reload(status_bar_logging)
    monkeypatch.setattr(mod, "_log_dir", lambda: str(tmp_path / ".log"))
    mod._reset_for_tests()
    logger = mod.get_logger("decorated")

    @mod.log_call(logger)
    def combine(prefix: str, count: int = 1) -> str:
        return f"{prefix}:{count}"

    assert combine("tokens", count=3) == "tokens:3"

    log_text = (tmp_path / ".log" / "status-bar.log").read_text(encoding="utf-8")
    assert (
        "ENTER test_logging.py:"
        "test_log_call_records_arguments_and_return_value.<locals>.combine"
        "(prefix='tokens', count=3)"
    ) in log_text
    assert (
        "EXIT test_logging.py:"
        "test_log_call_records_arguments_and_return_value.<locals>.combine"
        " -> 'tokens:3'"
    ) in log_text
