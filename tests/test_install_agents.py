"""Install-path tests for Codex, Qwen, and Claude multi-home writes."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

from agent_tui_catalog import read_status_line_tokens

REPO_ROOT = Path(__file__).resolve().parents[1]
INSTALL_SH = REPO_ROOT / "install.sh"
FRAMEWORK = REPO_ROOT.parent / "linux_installation_scripts_functions"

pytestmark = pytest.mark.skipif(
    not (FRAMEWORK / "component_loader.sh").exists(),
    reason="shared component framework not available as a sibling checkout",
)


def run_install(target_home: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["TARGET_USER"] = env.get("USER", "")
    env["TARGET_HOME"] = str(target_home)
    return subprocess.run(
        ["bash", str(INSTALL_SH), *args],
        capture_output=True,
        text=True,
        env=env,
        check=False,
        stdin=subprocess.DEVNULL,
    )


def read_claude_segments(target_home: Path) -> list[str]:
    config = target_home / ".claude" / "claude-status-bar.conf"
    return [
        line.strip()
        for line in config.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    ]


def test_list_components_five_agents_in_order(tmp_path):
    result = run_install(tmp_path, "--list-components")
    assert result.returncode == 0, result.stderr
    ids = [line.split("\t")[0] for line in result.stdout.splitlines() if "\t" in line]
    assert ids == ["codex_tui", "qwen_tui", "openrouter_tui", "nvidia_tui", "claude_tui", "grok_tui", "cline_tui"]


def test_list_configurable_components_includes_all_five(tmp_path):
    result = run_install(tmp_path, "--list-configurable-components")
    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines() == [
        "codex_tui", "qwen_tui", "openrouter_tui", "nvidia_tui", "claude_tui", "grok_tui", "cline_tui",
    ]


def test_default_install_writes_codex_qwen_and_claude_configs(tmp_path):
    result = run_install(tmp_path, "--default")
    assert result.returncode == 0, result.stderr

    codex = tmp_path / ".codex" / "config.toml"
    codex_api = tmp_path / ".codex-api" / "config.toml"
    qwen = tmp_path / ".codex-qwen" / "config.toml"
    assert codex.exists()
    assert codex_api.exists()
    assert qwen.exists()

    openrouter = tmp_path / ".codex-openrouter" / "config.toml"
    assert openrouter.exists()

    nvidia = tmp_path / ".codex-nvidia" / "config.toml"
    assert nvidia.exists()

    codex_tokens = read_status_line_tokens(codex)
    api_tokens = read_status_line_tokens(codex_api)
    qwen_tokens = read_status_line_tokens(qwen)
    openrouter_tokens = read_status_line_tokens(openrouter)
    nvidia_tokens = read_status_line_tokens(nvidia)
    assert codex_tokens == api_tokens
    # Rate-limit fields plus run-state, context-used, codex-version, and
    # pull-request-number default off; the active worktree (current-dir) is on
    # and the project basename + git branch are removed from the status line.
    rich_default = [
        "model-with-reasoning", "current-dir", "context-remaining",
        "branch-changes", "used-tokens", "total-input-tokens", "total-output-tokens",
    ]
    assert codex_tokens == rich_default
    # The isolated Qwen (qa) and OpenRouter (oa) Codex instances share Codex's
    # rich default status line (tokens in/out/used, ...), minus the rate limits.
    assert qwen_tokens == rich_default
    assert openrouter_tokens == rich_default
    # The NVIDIA (na) instance shares the same rich default status line.
    assert nvidia_tokens == rich_default
    assert (tmp_path / ".config" / "claude_code_status_bar" / "field-selections.json").exists()

    claude = tmp_path / ".claude"
    assert (claude / "claude-status-bar").exists()
    settings = json.loads((claude / "settings.json").read_text(encoding="utf-8"))
    assert "statusLine" in settings
    # Rate-limit segments default off (dedicated taskbar bar owns them now).
    assert read_claude_segments(tmp_path) == [
        "model", "project", "context", "diff", "tokens", "cost",
    ]


def test_reinstall_is_idempotent_for_codex_homes(tmp_path):
    first = run_install(tmp_path, "--default")
    assert first.returncode == 0, first.stderr
    codex_after_first = (tmp_path / ".codex" / "config.toml").read_text(encoding="utf-8")

    second = run_install(tmp_path, "--default")
    assert second.returncode == 0, second.stderr
    codex_after_second = (tmp_path / ".codex" / "config.toml").read_text(encoding="utf-8")
    assert codex_after_first == codex_after_second


def test_reinstall_migrates_existing_codex_selection_to_worktree(tmp_path):
    selection = tmp_path / ".config" / "claude_code_status_bar" / "field-selections.json"
    selection.parent.mkdir(parents=True)
    selection.write_text(
        json.dumps({
            "codex": ["model-with-reasoning", "current-dir", "context-remaining"],
            "qwen": ["model-with-reasoning", "current-dir", "context-remaining"],
        }) + "\n",
        encoding="utf-8",
    )

    result = run_install(tmp_path, "--select", "qwen_tui")
    assert result.returncode == 0, result.stderr

    # The project basename and git branch are no longer part of the Codex
    # status line, so the existing worktree-only selection is left untouched.
    document = json.loads(selection.read_text(encoding="utf-8"))
    assert document["qwen"] == [
        "model-with-reasoning", "current-dir", "context-remaining",
    ]
