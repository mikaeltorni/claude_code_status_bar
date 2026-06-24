"""Tests for install-time Claude Code settings wiring."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "status_bar_install.py"


def load_module():
    spec = importlib.util.spec_from_file_location("status_bar_install", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_configure_status_line_preserves_unrelated_settings(tmp_path):
    mod = load_module()
    settings_file = tmp_path / ".claude" / "settings.json"
    settings_file.parent.mkdir()
    settings_file.write_text(json.dumps({"theme": "dark"}), encoding="utf-8")

    mod.configure_status_line(settings_file, tmp_path / ".claude" / "claude-status-bar")

    settings = json.loads(settings_file.read_text(encoding="utf-8"))
    assert settings["theme"] == "dark"
    assert settings["statusLine"] == {
        "type": "command",
        "command": f"python3 {tmp_path / '.claude' / 'claude-status-bar'}",
    }


def test_configure_status_line_quotes_paths_with_spaces(tmp_path):
    mod = load_module()
    settings_file = tmp_path / "Claude Config" / "settings.json"
    status_script = tmp_path / "Claude Config" / "claude-status-bar"

    mod.configure_status_line(settings_file, status_script)

    settings = json.loads(settings_file.read_text(encoding="utf-8"))
    assert settings["statusLine"]["command"] == f"python3 '{status_script}'"


def test_install_shell_delegates_settings_write_to_python_module():
    # The settings write lives in the install-step library, invoked via the
    # python module rather than an inline heredoc. Assert across every installer
    # shell file so the delegation can't regress into a script.
    shell_files = [
        ROOT / "install.sh",
        ROOT / "scripts" / "install_standalone.sh",
        ROOT / "lib" / "status_bar_install_lib.sh",
    ]
    combined = "\n".join(f.read_text(encoding="utf-8") for f in shell_files)
    assert "status_bar_install.py" in combined
    assert "python3 - <<'PY'" not in combined
    assert "<<'PY'" not in combined
