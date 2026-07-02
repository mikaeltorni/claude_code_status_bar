"""Structural tests for shared menu preview hooks."""

from __future__ import annotations

import os
import subprocess
import textwrap
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
HOOKS = REPO_ROOT / "lib" / "status_bar_menu_hooks.sh"
FRAMEWORK = REPO_ROOT.parent / "linux_installation_scripts_functions"
MENU = FRAMEWORK / "component_menu.sh"

pytestmark = pytest.mark.skipif(
    not MENU.exists(),
    reason="shared component menu not available as a sibling checkout",
)


def _nonempty_lines(output: str) -> list[str]:
    return [line for line in output.splitlines() if line.strip()]


def _run_render(script_body: str) -> subprocess.CompletedProcess[str]:
    script = textwrap.dedent(
        f"""
        source "{MENU}"
        STATUS_BAR_REPO_DIR="{REPO_ROOT}"
        source "{HOOKS}"
        status_bar_register_menu_preview_hooks
        {script_body}
        """
    )
    env = dict(os.environ)
    env.update({"LINES": "30", "COLUMNS": "120"})
    return subprocess.run(
        ["bash", "-c", script],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )


def test_submenu_preview_is_above_footer_help():
    body = textwrap.dedent(
        """
        CM_REPOS+=(claude_code_status_bar)
        CM_REPO_LABEL[claude_code_status_bar]="Agent TUI status bars"
        CM_REPO_ENABLED[claude_code_status_bar]=1
        CM_COMP_IDS[claude_code_status_bar]="codex_tui qwen_tui"
        CM_COMP_LABEL[claude_code_status_bar|codex_tui]="Codex"
        CM_COMP_LABEL[claude_code_status_bar|qwen_tui]="Qwen"
        CM_COMP_ON[claude_code_status_bar|codex_tui]=1
        CM_COMP_ON[claude_code_status_bar|qwen_tui]=1
        out="$(cm_render_submenu claude_code_status_bar 0 "Configure" "footer help")"
        printf '%s' "$out"
        """
    )
    result = _run_render(body)
    assert result.returncode == 0, result.stderr
    lines = _nonempty_lines(result.stdout)
    assert len(lines) >= 2
    assert "footer help" in lines[-1]
    assert "Preview:" in lines[-2]
    assert "gpt-5.5" in lines[-2] or "ornstein" in lines[-2].lower()


def test_aggregate_preview_is_above_help_line():
    body = textwrap.dedent(
        """
        CM_REPOS=(other_repo claude_code_status_bar)
        CM_REPO_LABEL[claude_code_status_bar]="Agent TUI status bars"
        CM_REPO_ENABLED[claude_code_status_bar]=1
        out="$(cm_render_aggregate 1)"
        printf '%s' "$out"
        """
    )
    result = _run_render(body)
    assert result.returncode == 0, result.stderr
    lines = _nonempty_lines(result.stdout)
    assert len(lines) >= 2
    assert "[enter] apply" in lines[-1] or "configure" in lines[-1]
    assert "Preview:" in lines[-2]
    assert "[Codex]" in lines[-2]
    assert "[Qwen]" in lines[-2]