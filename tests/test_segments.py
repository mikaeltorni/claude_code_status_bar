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
        "total_output_tokens": 5120,
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
    assert line.count("|") == 7  # eight segments => seven separators
    assert "in:63.2k out:5.1k" in line
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


def test_tokens_segment_never_shrinks_within_a_session(monkeypatch, tmp_path):
    # Sidechain payloads (subagents, haiku utility calls) report tiny totals;
    # the segment must hold the session's high-water mark instead of dipping.
    monkeypatch.setattr(status_bar_render, "__file__", str(tmp_path / "render.py"))
    monkeypatch.setattr(status_bar_render, "enabled_segments", lambda: {"tokens"})
    payload = dict(FULL_PAYLOAD, session_id="sess-1")
    assert status_bar_render.build_status_line(payload) == "in:63.2k out:5.1k"
    payload["context_window"] = dict(
        FULL_PAYLOAD["context_window"], total_input_tokens=6, total_output_tokens=1
    )
    assert status_bar_render.build_status_line(payload) == "in:63.2k out:5.1k"
    # A genuinely larger total still moves the mark forward.
    payload["context_window"]["total_input_tokens"] = 70_000
    assert status_bar_render.build_status_line(payload) == "in:70.0k out:5.1k"


def test_tokens_high_water_is_isolated_per_session(monkeypatch, tmp_path):
    monkeypatch.setattr(status_bar_render, "__file__", str(tmp_path / "render.py"))
    monkeypatch.setattr(status_bar_render, "enabled_segments", lambda: {"tokens"})
    big = dict(FULL_PAYLOAD, session_id="sess-a")
    assert status_bar_render.build_status_line(big) == "in:63.2k out:5.1k"
    small = dict(FULL_PAYLOAD, session_id="sess-b")
    small["context_window"] = dict(
        FULL_PAYLOAD["context_window"], total_input_tokens=6, total_output_tokens=1
    )
    assert status_bar_render.build_status_line(small) == "in:6 out:1"
