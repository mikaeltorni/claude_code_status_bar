"""Tests for simulated status-bar previews."""

from __future__ import annotations

from status_bar_preview import preview_all_agents, preview_for_agent


def test_codex_preview_is_non_empty_and_changes_when_field_removed():
    full = preview_for_agent("codex", [
        "model-with-reasoning", "current-dir", "project-name",
        "context-remaining", "five-hour-limit", "weekly-limit",
    ])
    reduced = preview_for_agent("codex", ["model-with-reasoning", "current-dir"])
    assert full
    assert reduced
    assert full != reduced
    assert "claude_code_status_bar" in full
    assert "master" not in reduced


def test_codex_default_preview_shows_worktree_without_master_branch(tmp_path):
    line = preview_for_agent("codex", target_home=tmp_path)

    assert "claude_code_status_bar" in line
    assert "master" not in line


def test_qwen_preview_uses_local_fixture():
    line = preview_for_agent("qwen", ["model-with-reasoning", "current-dir", "context-remaining"])
    assert "ornstein" in line
    assert "agent_command_center" in line


def test_aggregate_preview_lists_all_agents_on_separate_lines():
    text = preview_all_agents()
    lines = [line for line in text.splitlines() if line.strip()]
    assert len(lines) == 7
    for label in ("Codex", "Qwen", "OpenRouter", "NVIDIA", "Claude", "Grok", "Cline"):
        assert any(f"[{label}]" in line for line in lines)
    assert all(line.startswith("[") for line in lines)
    assert " | [" not in text
    assert lines[0].startswith("[Codex]")
    assert lines[1].startswith("[Qwen]")


def test_claude_preview_honors_segment_selection():
    full = preview_for_agent("claude", list(__import__("status_bar_config").SEGMENT_IDS))
    subset = preview_for_agent("claude", ["model", "project"])
    assert full
    assert subset
    assert full != subset
    assert "claude_code_status_bar" in full
    assert "claude_code_status_bar" in subset
    assert "$1.42" in full
    assert "$1.42" not in subset
