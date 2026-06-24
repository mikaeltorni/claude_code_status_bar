"""Tests for status-bar segment-selection config resolution and writing."""

from __future__ import annotations

import importlib

import status_bar_config


def _module(monkeypatch, config_path):
    """Reload the config module pointing _config_path at a tmp file."""
    mod = importlib.reload(status_bar_config)
    monkeypatch.setattr(mod, "_config_path", lambda: str(config_path))
    return mod


def test_absent_config_enables_all_segments(monkeypatch, tmp_path):
    mod = _module(monkeypatch, tmp_path / "missing.conf")
    assert mod.enabled_segments() is None


def test_init_creates_empty_selection(monkeypatch, tmp_path):
    config = tmp_path / "claude-status-bar.conf"
    mod = _module(monkeypatch, config)
    assert mod.main(["init", str(config)]) == 0
    # File exists (so renderer filters) but selects nothing.
    assert config.exists()
    assert mod.enabled_segments() == set()


def test_enable_appends_only_valid_ids(monkeypatch, tmp_path):
    config = tmp_path / "claude-status-bar.conf"
    mod = _module(monkeypatch, config)
    mod.main(["init", str(config)])
    assert mod.main(["enable", "model", str(config)]) == 0
    assert mod.main(["enable", "cost", str(config)]) == 0
    # Re-enabling is idempotent.
    assert mod.main(["enable", "model", str(config)]) == 0
    assert mod.enabled_segments() == {"model", "cost"}


def test_enable_rejects_unknown_segment(monkeypatch, tmp_path):
    config = tmp_path / "claude-status-bar.conf"
    mod = _module(monkeypatch, config)
    mod.main(["init", str(config)])
    assert mod.main(["enable", "bogus", str(config)]) == 2
    assert mod.enabled_segments() == set()


def test_written_config_is_in_canonical_bar_order(monkeypatch, tmp_path):
    config = tmp_path / "claude-status-bar.conf"
    mod = _module(monkeypatch, config)
    mod.main(["init", str(config)])
    # Enable out of order; the file must list ids in SEGMENT_IDS order.
    for seg in ("cost", "model", "context"):
        mod.main(["enable", seg, str(config)])
    listed = [
        line.strip()
        for line in config.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    ]
    assert listed == ["model", "context", "cost"]


def test_unknown_and_blank_lines_are_ignored(monkeypatch, tmp_path):
    config = tmp_path / "claude-status-bar.conf"
    config.write_text(
        "# a comment\n\nmodel\nnot_a_segment\n  cost  # trailing\n", encoding="utf-8"
    )
    mod = _module(monkeypatch, config)
    assert mod.enabled_segments() == {"model", "cost"}


def test_is_segment_enabled_honors_all_and_subset():
    assert status_bar_config.is_segment_enabled("model", None) is True
    assert status_bar_config.is_segment_enabled("model", {"model"}) is True
    assert status_bar_config.is_segment_enabled("cost", {"model"}) is False
