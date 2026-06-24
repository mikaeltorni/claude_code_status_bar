"""End-to-end tests for the component-based install.sh into a clean home.

These run the real installer against a temporary ``TARGET_HOME`` (no sudo, no
touching the developer's ~/.claude) and assert the standard component contract:
listing is side-effect free, selection installs exactly the chosen segments, the
core files land in place, and re-running is idempotent. They are skipped when the
shared component framework is not resolvable as a sibling checkout.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

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
    assert ids == ["core", "model", "project", "context", "five_hour", "weekly", "diff", "cost"]
    # Listing must not create the installed directory.
    assert not (tmp_path / ".claude").exists()


def test_default_install_installs_core_and_all_segments(tmp_path):
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
    assert read_segments(tmp_path) == [
        "model", "project", "context", "five_hour", "weekly", "diff", "cost",
    ]


def test_select_installs_only_chosen_segments(tmp_path):
    result = run_install(tmp_path, "--select", "core,model,cost")
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
    assert settings["theme"] == "dark"  # unrelated key preserved
    assert "statusLine" in settings


def test_reselect_replaces_previous_segment_choice(tmp_path):
    run_install(tmp_path, "--default")
    assert len(read_segments(tmp_path)) == 7
    # Re-running with a narrower selection regenerates the config cleanly.
    run_install(tmp_path, "--select", "core,context")
    assert read_segments(tmp_path) == ["context"]
