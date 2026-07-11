"""Tests for Codex status-line selection migrations."""

from __future__ import annotations

import json

from agent_field_selection import (
    CODEX_STYLE_AGENTS,
    CODEX_DEFAULT_FIELDS,
    LEGACY_CODEX_DEFAULT_FIELDS,
    load_document,
    migrate_codex_worktree_field,
)


def test_migrate_legacy_codex_defaults_to_worktree_field(tmp_path):
    path = tmp_path / "field-selections.json"
    path.write_text(
        json.dumps({agent: list(LEGACY_CODEX_DEFAULT_FIELDS) for agent in CODEX_STYLE_AGENTS}),
        encoding="utf-8",
    )

    assert migrate_codex_worktree_field(path) is True
    document = load_document(path)
    for agent in CODEX_STYLE_AGENTS:
        assert document[agent] == list(CODEX_DEFAULT_FIELDS)


def test_migrate_adds_worktree_to_existing_branchless_selection(tmp_path):
    path = tmp_path / "field-selections.json"
    path.write_text(
        json.dumps(
            {
                "codex": [
                    "model-with-reasoning",
                    "current-dir",
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
        "project-name",
        "context-remaining",
        "branch-changes",
    ]


def test_migrate_preserves_explicit_git_branch_selection(tmp_path):
    path = tmp_path / "field-selections.json"
    selected = ["model-with-reasoning", "current-dir", "git-branch"]
    path.write_text(json.dumps({"codex": selected}), encoding="utf-8")

    assert migrate_codex_worktree_field(path) is False
    assert load_document(path)["codex"] == selected
