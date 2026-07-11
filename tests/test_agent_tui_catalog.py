"""Tests for shared Codex TUI catalog and TOML writer."""

from __future__ import annotations

import json

from agent_tui_catalog import (
    CODEX_DEFAULT_FIELDS,
    CODEX_FIELD_IDS,
    read_status_line_tokens,
    write_status_line_tokens,
)


def test_project_name_is_the_default_codex_worktree_field():
    """Codex defaults use its project-root/worktree name instead of ``master``."""
    assert "project-name" in CODEX_FIELD_IDS
    assert "project-name" in CODEX_DEFAULT_FIELDS
    assert "git-branch" not in CODEX_DEFAULT_FIELDS


def test_write_preserves_unrelated_toml_keys(tmp_path):
    config = tmp_path / "config.toml"
    config.write_text(
        'approval_policy = "never"\n\n[tui]\nstatus_line = ["old"]\n',
        encoding="utf-8",
    )
    write_status_line_tokens(config, list(CODEX_DEFAULT_FIELDS))
    text = config.read_text(encoding="utf-8")
    assert 'approval_policy = "never"' in text
    assert read_status_line_tokens(config) == list(CODEX_DEFAULT_FIELDS)


def test_write_creates_tui_section_when_missing(tmp_path):
    config = tmp_path / "config.toml"
    write_status_line_tokens(config, ["model-with-reasoning", "current-dir"])
    assert "[tui]" in config.read_text(encoding="utf-8")
    assert read_status_line_tokens(config) == ["model-with-reasoning", "current-dir"]


def test_agent_tui_install_cli_round_trip(tmp_path):
    from agent_tui_install import main as install_main

    config = tmp_path / "config.toml"
    tokens = json.dumps(list(CODEX_DEFAULT_FIELDS))
    assert install_main(["write", str(config), tokens]) == 0
    assert read_status_line_tokens(config) == list(CODEX_DEFAULT_FIELDS)
