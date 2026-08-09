"""Tests for shared Codex TUI catalog and TOML writer."""

from __future__ import annotations

import json

from agent_tui_catalog import (
    CODEX_DEFAULT_FIELDS,
    CODEX_FIELD_IDS,
    read_status_line_tokens,
    remove_status_line,
    write_status_line_tokens,
)


def test_codex_defaults_drop_project_and_branch_but_keep_worktree():
    """Codex defaults omit project-root basename and branch, keep worktree.

    The project-root basename (``project-name``) and the Git branch
    (``git-branch``) are removed from the Codex status line; the active worktree
    (``current-dir``) stays. None of the removed tokens exist in the catalog, and
    ``current-dir`` is present in both the catalog and the defaults.
    """
    assert "current-dir" in CODEX_FIELD_IDS
    assert "current-dir" in CODEX_DEFAULT_FIELDS
    assert "project-name" not in CODEX_FIELD_IDS
    assert "project-name" not in CODEX_DEFAULT_FIELDS
    assert "git-branch" not in CODEX_FIELD_IDS
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


def test_remove_status_line_drops_key_and_empty_section(tmp_path):
    """Uninstall removes only the status_line key and a now-empty [tui] table."""
    config = tmp_path / "config.toml"
    config.write_text(
        'approval_policy = "never"\n\n[tui]\nstatus_line = ["current-dir"]\n',
        encoding="utf-8",
    )
    assert remove_status_line(config) is True
    text = config.read_text(encoding="utf-8")
    assert 'approval_policy = "never"' in text
    assert "status_line" not in text
    assert "[tui]" not in text
    assert read_status_line_tokens(config) is None


def test_remove_status_line_keeps_other_tui_keys(tmp_path):
    """A [tui] table with other keys survives; only status_line is dropped."""
    config = tmp_path / "config.toml"
    config.write_text(
        '[tui]\nnotifications = true\nstatus_line = ["current-dir"]\n\n[other]\nx = 1\n',
        encoding="utf-8",
    )
    assert remove_status_line(config) is True
    text = config.read_text(encoding="utf-8")
    assert "[tui]" in text
    assert "notifications = true" in text
    assert "status_line" not in text
    assert "[other]" in text


def test_remove_status_line_is_a_noop_when_absent(tmp_path):
    """Removing from a missing or unconfigured file reports no change."""
    missing = tmp_path / "missing.toml"
    assert remove_status_line(missing) is False
    assert not missing.exists()
    config = tmp_path / "config.toml"
    config.write_text('approval_policy = "never"\n', encoding="utf-8")
    assert remove_status_line(config) is False
    assert config.read_text(encoding="utf-8") == 'approval_policy = "never"\n'


def test_agent_tui_install_cli_remove(tmp_path):
    """The installer CLI exposes a `remove` command for uninstall paths."""
    import agent_tui_install

    config = tmp_path / "config.toml"
    write_status_line_tokens(config, list(CODEX_DEFAULT_FIELDS))
    assert agent_tui_install.main(["remove", str(config)]) == 0
    assert read_status_line_tokens(config) is None
