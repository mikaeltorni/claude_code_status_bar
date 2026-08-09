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


def test_readonly_flags_route_through_the_shared_framework_helper():
    """Side-effect-free flags must not fall through to main().

    The hand-maintained list omitted --uninstall and --export-selection, so an
    uninstall ran through main() and wrapped itself in the "Installing agent
    TUI status bars" / "Status bar setup complete." banners.
    """
    text = (ROOT / "scripts" / "install_standalone.sh").read_text(encoding="utf-8")

    assert "isc_route_readonly_args" in text
    assert "--list-components|--list-configurable-components" not in text, (
        "hand-rolled readonly flag list reintroduced"
    )


def test_uninstall_does_not_print_install_banners():
    """An uninstall must not announce an installation."""
    import subprocess

    functions_dir = ROOT.parent / "linux_installation_scripts_functions"
    if not functions_dir.is_dir():
        functions_dir = Path.home() / "projects/linux_installation_scripts_functions"
    if not functions_dir.is_dir():
        import pytest

        pytest.skip("installer framework checkout unavailable")

    import os

    env = dict(os.environ, ISC_FUNCTIONS_DIR=str(functions_dir))
    result = subprocess.run(
        ["bash", str(ROOT / "scripts" / "install_standalone.sh"),
         "--uninstall", "definitely_not_a_component"],
        capture_output=True, text=True, timeout=120, env=env,
    )
    combined = result.stdout + result.stderr

    assert "Installing agent TUI status bars" not in combined
    assert "Status bar setup complete" not in combined
