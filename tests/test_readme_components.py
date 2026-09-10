"""README must name every selectable TUI component id."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _manifest_ids() -> list[str]:
    ids: list[str] = []
    for line in (ROOT / "installer" / "components.sh").read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith('"') and "|" in stripped:
            ids.append(stripped.strip('"').split("|", 1)[0])
    return ids


def test_readme_names_every_manifest_component() -> None:
    """User-facing README must not drop an ISC_COMPONENTS row."""
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    ids = _manifest_ids()
    assert ids == [
        "codex_tui",
        "qwen_tui",
        "openrouter_tui",
        "nvidia_tui",
        "claude_tui",
        "grok_tui",
        "cline_tui",
    ]
    for component_id in ids:
        assert f"`{component_id}`" in readme, f"README omits {component_id}"
    assert "OpenRouter (`oa`)" in agents
    assert "NVIDIA (`na`/`nvi`)" in agents
    assert "Five-agent" not in readme
    assert "five-agent" not in (ROOT / "installer" / "components.sh").read_text(encoding="utf-8")
    assert "five-agent" not in (ROOT / "lib" / "status_bar_install_lib.sh").read_text(encoding="utf-8")
