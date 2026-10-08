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
        "command": f"{tmp_path / '.claude' / 'claude-status-bar'}",
        "refreshInterval": mod.STATUS_LINE_REFRESH_INTERVAL_SECONDS,
    }


def test_configure_status_line_quotes_paths_with_spaces(tmp_path):
    mod = load_module()
    settings_file = tmp_path / "Claude Config" / "settings.json"
    status_script = tmp_path / "Claude Config" / "claude-status-bar"

    mod.configure_status_line(settings_file, status_script)

    settings = json.loads(settings_file.read_text(encoding="utf-8"))
    assert settings["statusLine"]["command"] == f"'{status_script}'"
    assert settings["statusLine"]["refreshInterval"] == mod.STATUS_LINE_REFRESH_INTERVAL_SECONDS


def test_ensure_project_trust_sets_has_trust_dialog_accepted(tmp_path):
    """Claude Code skips statusLine until the workspace is trusted."""
    mod = load_module()
    project = tmp_path / "phrase_automation"
    project.mkdir()
    claude_json = tmp_path / ".claude.json"
    claude_json.write_text(
        json.dumps(
            {
                "projects": {
                    str(project): {
                        "allowedTools": [],
                        "hasTrustDialogAccepted": False,
                        "projectOnboardingSeenCount": 1,
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    changed = mod.ensure_project_trust(claude_json, project)

    assert changed is True
    data = json.loads(claude_json.read_text(encoding="utf-8"))
    entry = data["projects"][str(project.resolve())]
    assert entry["hasTrustDialogAccepted"] is True
    assert entry["projectOnboardingSeenCount"] == 1


def test_ensure_project_trust_is_idempotent(tmp_path):
    mod = load_module()
    project = tmp_path / "installation_scripts"
    project.mkdir()
    claude_json = tmp_path / ".claude.json"
    key = str(project.resolve())
    claude_json.write_text(
        json.dumps({"projects": {key: {"hasTrustDialogAccepted": True}}}),
        encoding="utf-8",
    )

    assert mod.ensure_project_trust(claude_json, project) is False
    data = json.loads(claude_json.read_text(encoding="utf-8"))
    assert data["projects"][key]["hasTrustDialogAccepted"] is True


def test_ensure_known_projects_trust_only_updates_existing_paths(tmp_path):
    mod = load_module()
    present = tmp_path / "present_repo"
    present.mkdir()
    missing = tmp_path / "missing_repo"
    claude_json = tmp_path / ".claude.json"
    claude_json.write_text(
        json.dumps(
            {
                "projects": {
                    str(present): {"hasTrustDialogAccepted": False},
                    str(missing): {"hasTrustDialogAccepted": False},
                }
            }
        ),
        encoding="utf-8",
    )

    updated = mod.ensure_known_projects_trust(claude_json)

    assert str(present.resolve()) in updated
    assert str(missing.resolve()) not in updated
    data = json.loads(claude_json.read_text(encoding="utf-8"))
    assert data["projects"][str(present.resolve())]["hasTrustDialogAccepted"] is True
    # Missing path key is left as-is (may use unresolved form).
    missing_entry = next(
        v for k, v in data["projects"].items() if k.endswith("missing_repo")
    )
    assert missing_entry["hasTrustDialogAccepted"] is False


def test_main_ensure_trust_cli(tmp_path):
    mod = load_module()
    project = tmp_path / "repo"
    project.mkdir()
    claude_json = tmp_path / ".claude.json"
    claude_json.write_text(json.dumps({"projects": {}}), encoding="utf-8")

    code = mod.main(["--ensure-trust", str(claude_json), str(project)])

    assert code == 0
    data = json.loads(claude_json.read_text(encoding="utf-8"))
    assert data["projects"][str(project.resolve())]["hasTrustDialogAccepted"] is True


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
    assert "status-bar-tools" in combined
    assert "settings" in combined
    assert "python3 - <<'PY'" not in combined
    assert "<<'PY'" not in combined


def test_claude_status_bar_build_keeps_existing_rustup_toolchain():
    """The release build must see an already installed rustup toolchain.

    Parameters: none.

    Returns: None.
    """
    print("parameters=none")
    text = (ROOT / "lib" / "status_bar_install_lib.sh").read_text(encoding="utf-8")
    assert "command -v cargo" in text
    assert 'CARGO_HOME="$TARGET_HOME/.cargo"' in text
    assert 'RUSTUP_HOME="$TARGET_HOME/.rustup"' in text
    assert "--locked" in text
    print(None)


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
