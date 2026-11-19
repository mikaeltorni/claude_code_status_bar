"""End-to-end tests for the component-based install.sh into a clean home.

These run the real installer against a temporary ``TARGET_HOME`` (no sudo, no
touching the developer's ~/.claude) and assert the standard component contract:
listing is side-effect free, selection installs exactly the chosen segments, the
core files land in place, and re-running is idempotent with the bundled framework.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
INSTALL_SH = REPO_ROOT / "install.sh"


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


def read_segments(target_home: Path) -> list[str]:
    config = target_home / ".claude" / "claude-status-bar.conf"
    return [
        line.strip()
        for line in config.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    ]


def test_list_components_is_side_effect_free(tmp_path):
    result = run_install(tmp_path, "--list-components")
    assert result.returncode == 0, result.stderr
    ids = [line.split("\t")[0] for line in result.stdout.splitlines() if "\t" in line]
    assert ids == ["codex_tui", "qwen_tui", "openrouter_tui", "nvidia_tui", "claude_tui", "grok_tui", "cline_tui"]
    assert not (tmp_path / ".claude").exists()


def test_framework_resolves_without_home_projects_path(tmp_path):
    """Discover components with bundled support in a clean home.

    Parameters: tmp_path - temporary target and launcher home.
    Returns: None.
    """
    print(f"tmp_path={tmp_path}")
    env_home = tmp_path / "scratch-home"
    env_home.mkdir()
    env = dict(os.environ)
    env.pop("ISC_FUNCTIONS_DIR", None)
    env.pop("ISC_COMPONENT_LIB_DIR", None)
    env["HOME"] = str(env_home)
    env["TARGET_USER"] = env.get("USER", "")
    env["TARGET_HOME"] = str(tmp_path / "target")
    result = subprocess.run(
        ["bash", str(INSTALL_SH), "--list-components"],
        capture_output=True,
        text=True,
        env=env,
        check=False,
        stdin=subprocess.DEVNULL,
    )
    assert result.returncode == 0, result.stderr
    assert "could not resolve installer helpers" not in result.stderr
    assert "codex_tui" in result.stdout
    print(None)


def test_default_install_installs_claude_core_and_default_segments(tmp_path):
    result = run_install(tmp_path, "--default")
    assert result.returncode == 0, result.stderr
    claude = tmp_path / ".claude"
    assert (claude / "claude-status-bar").exists()
    for module in (
        "status_bar_render.py",
        "status_bar_format.py",
        "status_bar_logging.py",
        "status_bar_config.py",
        "status_bar_install.py",
    ):
        assert (claude / module).exists(), module
    settings = json.loads((claude / "settings.json").read_text())
    assert settings["statusLine"]["type"] == "command"
    assert "claude-status-bar" in settings["statusLine"]["command"]
    # The 5-hour and weekly rate-limit segments are intentionally off by
    # default; they now have a dedicated taskbar bar. Still selectable.
    assert read_segments(tmp_path) == [
        "model", "project", "context", "diff", "tokens", "cost",
    ]


def test_select_installs_only_chosen_claude_segments(tmp_path):
    selection = tmp_path / ".config/claude_code_status_bar/field-selections.json"
    selection.parent.mkdir(parents=True)
    selection.write_text(
        json.dumps({"claude": ["model", "cost"]}) + "\n",
        encoding="utf-8",
    )
    result = run_install(tmp_path, "--select", "claude_tui")
    assert result.returncode == 0, result.stderr
    assert (tmp_path / ".claude" / "claude-status-bar").exists()
    assert read_segments(tmp_path) == ["model", "cost"]


def test_reinstall_is_idempotent_and_preserves_unrelated_settings(tmp_path):
    settings_file = tmp_path / ".claude" / "settings.json"
    settings_file.parent.mkdir(parents=True)
    settings_file.write_text(json.dumps({"theme": "dark"}) + "\n", encoding="utf-8")

    first = run_install(tmp_path, "--default")
    assert first.returncode == 0, first.stderr
    after_first = settings_file.read_text()

    second = run_install(tmp_path, "--default")
    assert second.returncode == 0, second.stderr
    after_second = settings_file.read_text()

    assert after_first == after_second
    settings = json.loads(after_second)
    assert settings["theme"] == "dark"
    assert "statusLine" in settings


def test_reselect_replaces_previous_segment_choice(tmp_path):
    run_install(tmp_path, "--default")
    assert read_segments(tmp_path) == [
        "model", "project", "context", "diff", "tokens", "cost",
    ]
    selection = tmp_path / ".config/claude_code_status_bar/field-selections.json"
    selection.parent.mkdir(parents=True, exist_ok=True)
    selection.write_text(
        json.dumps({"claude": ["context"]}) + "\n",
        encoding="utf-8",
    )
    run_install(tmp_path, "--select", "claude_tui")
    assert read_segments(tmp_path) == ["context"]

def test_every_component_declares_an_uninstall_function(tmp_path):
    """No component may be install-only: each entry names an uninstall hook.

    A component the user can deselect must also be removable, otherwise
    "optional" only means "optional on a fresh machine".
    """
    manifest = (REPO_ROOT / "installer" / "components.sh").read_text(encoding="utf-8")
    lib = (REPO_ROOT / "lib" / "status_bar_install_lib.sh").read_text(encoding="utf-8")
    entries = [
        line.strip().strip('"')
        for line in manifest.splitlines()
        if line.strip().startswith('"') and "|" in line
    ]
    assert entries, "no manifest entries parsed"
    for entry in entries:
        fields = entry.split("|")
        component_id, uninstall_fn = fields[0], fields[5]
        assert uninstall_fn, f"{component_id} declares no uninstall function"
        assert f"{uninstall_fn}()" in lib, f"{uninstall_fn} is not defined in the lib"


def test_uninstall_codex_removes_status_line_and_keeps_other_keys(tmp_path):
    """Uninstalling the Codex bar clears status_line but preserves the config."""
    config = tmp_path / ".codex" / "config.toml"
    config.parent.mkdir(parents=True)
    config.write_text('approval_policy = "never"\n', encoding="utf-8")
    assert run_install(tmp_path, "--select", "codex_tui").returncode == 0
    assert "status_line" in config.read_text(encoding="utf-8")

    result = run_install(tmp_path, "--uninstall", "codex_tui")
    assert result.returncode == 0, result.stderr
    text = config.read_text(encoding="utf-8")
    assert "status_line" not in text
    assert 'approval_policy = "never"' in text


def test_uninstall_claude_removes_status_line_wiring(tmp_path):
    """Uninstalling the Claude bar unwires statusLine and removes the script."""
    claude = tmp_path / ".claude"
    claude.mkdir(parents=True)
    (claude / "settings.json").write_text(json.dumps({"theme": "dark"}) + "\n", encoding="utf-8")
    assert run_install(tmp_path, "--select", "claude_tui").returncode == 0
    assert (claude / "claude-status-bar").exists()

    result = run_install(tmp_path, "--uninstall", "claude_tui")
    assert result.returncode == 0, result.stderr
    settings = json.loads((claude / "settings.json").read_text(encoding="utf-8"))
    assert "statusLine" not in settings
    assert settings["theme"] == "dark", "unrelated Claude settings must survive"
    assert not (claude / "claude-status-bar").exists()
    assert not (claude / "status_bar_render.py").exists()


def test_uninstall_is_idempotent_on_a_clean_home(tmp_path):
    """Uninstalling something that was never installed is a safe no-op."""
    result = run_install(tmp_path, "--uninstall", "codex_tui")
    assert result.returncode == 0, result.stderr
    assert not (tmp_path / ".codex").exists()
