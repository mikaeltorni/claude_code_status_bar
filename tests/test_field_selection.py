"""Tests for Codex status-line selection migrations."""

from __future__ import annotations

import json

from agent_field_selection import (
    CODEX_STYLE_AGENTS,
    CODEX_DEFAULT_FIELDS,
    load_document,
    migrate_codex_worktree_field,
)


def test_migrate_drops_worktree_project_and_branch_tokens_from_all_style_agents(tmp_path):
    path = tmp_path / "field-selections.json"
    path.write_text(
        json.dumps(
            {
                agent: [
                    "model-with-reasoning",
                    "current-dir",
                    "project-name",
                    "git-branch",
                    "context-remaining",
                    "branch-changes",
                ]
                for agent in CODEX_STYLE_AGENTS
            }
        ),
        encoding="utf-8",
    )

    assert migrate_codex_worktree_field(path) is True
    document = load_document(path)
    for agent in CODEX_STYLE_AGENTS:
        # current-dir, project-name, and git-branch are removed; the remaining
        # fields keep their order.
        assert document[agent] == [
            "model-with-reasoning",
            "context-remaining",
            "branch-changes",
        ]


def test_migrate_strips_explicit_git_branch_selection(tmp_path):
    path = tmp_path / "field-selections.json"
    selected = ["model-with-reasoning", "current-dir", "git-branch"]
    path.write_text(json.dumps({"codex": selected}), encoding="utf-8")

    # The git-branch and current-dir tokens are no longer part of the Codex
    # status line, so they are stripped; the remaining fields keep their order.
    assert migrate_codex_worktree_field(path) is True
    assert load_document(path)["codex"] == ["model-with-reasoning"]


def test_migrate_strips_explicit_project_name_selection(tmp_path):
    path = tmp_path / "field-selections.json"
    selected = ["model-with-reasoning", "current-dir", "project-name"]
    path.write_text(json.dumps({"codex": selected}), encoding="utf-8")

    assert migrate_codex_worktree_field(path) is True
    assert load_document(path)["codex"] == ["model-with-reasoning"]


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
    # current-dir must NOT be re-added; the TUI status line is rid of it.
    assert load_document(path)["codex"] == [
        "model-with-reasoning",
        "context-remaining",
        "branch-changes",
    ]
