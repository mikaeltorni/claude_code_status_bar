"""Tests for Codex status-line selection migrations.

The Codex status line keeps the active worktree (``current-dir``) but drops the
project-root basename (``project-name``) and the Git branch (``git-branch``).
"""

from __future__ import annotations

import json

from agent_field_selection import (
    CODEX_STYLE_AGENTS,
    CODEX_DEFAULT_FIELDS,
    LEGACY_CODEX_DEFAULT_FIELDS,
    REMOVED_CODEX_DISPLAY_TOKENS,
    load_document,
    migrate_codex_worktree_field,
)


def test_removed_tokens_exclude_worktree():
    """The migration strips project/branch but never the worktree path."""
    assert "current-dir" not in REMOVED_CODEX_DISPLAY_TOKENS
    assert "project-name" in REMOVED_CODEX_DISPLAY_TOKENS
    assert "git-branch" in REMOVED_CODEX_DISPLAY_TOKENS


def test_migrate_legacy_codex_defaults_to_current_default(tmp_path):
    path = tmp_path / "field-selections.json"
    path.write_text(
        json.dumps({agent: list(LEGACY_CODEX_DEFAULT_FIELDS) for agent in CODEX_STYLE_AGENTS}),
        encoding="utf-8",
    )

    assert migrate_codex_worktree_field(path) is True
    document = load_document(path)
    for agent in CODEX_STYLE_AGENTS:
        assert document[agent] == list(CODEX_DEFAULT_FIELDS)
        assert "current-dir" in document[agent]


def test_migrate_strips_project_and_branch_but_keeps_worktree(tmp_path):
    path = tmp_path / "field-selections.json"
    path.write_text(
        json.dumps(
            {
                "codex": [
                    "model-with-reasoning",
                    "current-dir",
                    "project-name",
                    "git-branch",
                    "context-remaining",
                    "branch-changes",
                ]
            }
        ),
        encoding="utf-8",
    )

    assert migrate_codex_worktree_field(path) is True
    assert load_document(path)["codex"] == [
        "model-with-reasoning",
        "current-dir",
        "context-remaining",
        "branch-changes",
    ]


def test_migrate_strips_explicit_git_branch_selection(tmp_path):
    path = tmp_path / "field-selections.json"
    selected = ["model-with-reasoning", "current-dir", "git-branch"]
    path.write_text(json.dumps({"codex": selected}), encoding="utf-8")

    assert migrate_codex_worktree_field(path) is True
    assert load_document(path)["codex"] == ["model-with-reasoning", "current-dir"]


def test_migrate_does_not_invent_worktree_token(tmp_path):
    path = tmp_path / "field-selections.json"
    path.write_text(
        json.dumps(
            {
                "codex": [
                    "model-with-reasoning",
                    "context-remaining",
                    "branch-changes",
                ]
            }
        ),
        encoding="utf-8",
    )

    assert migrate_codex_worktree_field(path) is False
    assert load_document(path)["codex"] == [
        "model-with-reasoning",
        "context-remaining",
        "branch-changes",
    ]
