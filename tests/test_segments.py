"""Tests that the renderer honors the installed segment selection."""

from __future__ import annotations

import status_bar_render

# A payload that populates every segment, so omissions are caused purely by the
# selection rather than by missing data.
FULL_PAYLOAD = {
    "model": {"display_name": "Opus"},
    "effort": {"level": "low"},
    "workspace": {"project_dir": "/home/u/claude_code_status_bar"},
    "context_window": {
        "total_input_tokens": 63249,
        "context_window_size": 200000,
        "used_percentage": 31,
    },
    "rate_limits": {
        "five_hour": {"used_percentage": 10, "resets_at": 99999999999},
        "seven_day": {"used_percentage": 40, "resets_at": 99999999999},
    },
    "cost": {"total_lines_added": 120, "total_lines_removed": 8, "total_cost_usd": 1.42},
}


def test_none_selection_renders_every_segment(monkeypatch):
    monkeypatch.setattr(status_bar_render, "enabled_segments", lambda: None)
    line = status_bar_render.build_status_line(FULL_PAYLOAD)
    assert line.count("|") == 6  # seven segments => six separators
    assert "Opus · low" in line
    assert "claude_code_status_bar" in line
    assert "$1.42" in line


def test_empty_selection_renders_nothing(monkeypatch):
    monkeypatch.setattr(status_bar_render, "enabled_segments", lambda: set())
    assert status_bar_render.build_status_line(FULL_PAYLOAD) == ""


def test_subset_selection_renders_only_those_segments_in_order(monkeypatch):
    monkeypatch.setattr(
        status_bar_render, "enabled_segments", lambda: {"cost", "model"}
    )
    line = status_bar_render.build_status_line(FULL_PAYLOAD)
    # Order follows the registry (model before cost), regardless of set order.
    assert line == "Opus · low | $1.42"


def test_disabled_segment_is_omitted_even_when_data_present(monkeypatch):
    enabled = set(status_bar_render.SEGMENT_IDS) - {"project"}
    monkeypatch.setattr(status_bar_render, "enabled_segments", lambda: enabled)
    line = status_bar_render.build_status_line(FULL_PAYLOAD)
    assert "claude_code_status_bar" not in line
    assert "Opus · low" in line
