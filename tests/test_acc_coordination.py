"""Tests that ACC-style Qwen refresh honors status-bar field selections."""

from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

from agent_tui_catalog import read_status_line_tokens

REPO_ROOT = Path(__file__).resolve().parents[1]
ACC_ROOT = REPO_ROOT.parent / "agent_command_center"
QWEN_LIB = ACC_ROOT / "lib" / "qwen_codex.sh"
COORD_LIB = ACC_ROOT / "lib" / "status_bar_coordination.sh"


def test_write_qwen_config_toml_uses_status_bar_selections(tmp_path):
    if not QWEN_LIB.exists():
        import pytest

        pytest.skip("agent_command_center sibling checkout not available")
    selection_dir = tmp_path / ".config" / "claude_code_status_bar"
    selection_dir.mkdir(parents=True)
    (selection_dir / "field-selections.json").write_text(
        json.dumps({"qwen": ["model-with-reasoning", "git-branch"]}) + "\n",
        encoding="utf-8",
    )
    dest = tmp_path / "codex-qwen"
    dest.mkdir()
    script = "\n".join(
        [
            "set -euo pipefail",
            f"source {COORD_LIB}",
            f"source {QWEN_LIB}",
            f"export TARGET_HOME={tmp_path}",
            f"export CLAUDE_CODE_STATUS_BAR_DIR={REPO_ROOT}",
            'toml_string_array() { local -n arr=$1; printf \'["fallback"]\'; }',
            'run_as_target() { "$@"; }',
            "QWEN_CODEX_LOCAL_PROVIDER=lmstudio",
            "QWEN_CODEX_LMSTUDIO_MODEL=test-model",
            "QWEN_CODEX_CONTEXT_WINDOW=131072",
            "QWEN_CODEX_AUTO_COMPACT_TOKEN_LIMIT=65536",
            "QWEN_CODEX_REASONING_EFFORT=high",
            f'write_qwen_config_toml "{dest}"',
        ]
    )
    proc = subprocess.run(["bash", "-c", script], capture_output=True, text=True, check=False)
    assert proc.returncode == 0, proc.stderr + proc.stdout
    tokens = read_status_line_tokens(dest / "config.toml")
    # ``git-branch`` is no longer a valid Codex token and is normalized out of
    # the status_line (only ``current-dir`` carries the worktree identity).
    assert tokens == ["model-with-reasoning"]


def test_acc_postflight_reapplies_status_bar_install():
    """Check that ACC re-applies the status-bar TUI configs after install.

    Parameters: none.

    Returns: None.
    """
    print("parameters=none")
    if not (ACC_ROOT / "installer" / "components.sh").exists():
        import pytest

        pytest.skip("agent_command_center sibling checkout not available")
    components = (ACC_ROOT / "installer" / "components.sh").read_text(encoding="utf-8")
    coord = (ACC_ROOT / "lib" / "status_bar_coordination.sh").read_text(encoding="utf-8")
    assert "acc_reapply_status_bar_tui_configs" in coord
    assert "acc_reapply_status_bar_tui_configs" in components
    assert "codex_tui,qwen_tui" in coord
    print(None)