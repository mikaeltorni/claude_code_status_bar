# Agent guide

## Status bar: apply edits to the installed copy too

The source of truth is `claude-status-bar` (and its `status_bar_*.py` modules) in this repo, but Claude Code runs the **installed copy** under `~/.claude/`. Editing only the repo files will not change what shows in the status bar.

**Always auto-apply**: after editing the script or any module, immediately sync the installed copy without waiting to be asked — changes are invisible in the live bar until installed. Also make sure any newly added segment id is enabled in `~/.claude/claude-status-bar.conf`, since an existing conf preserves the old segment selection.

```bash
bash install.sh --select claude_tui
```

Then smoke-test the installed copy by piping a sample JSON payload to `~/.claude/claude-status-bar`.

## Agent TUI ownership

This repository owns display setup for the agent TUIs in menu order: Codex (`ca`), Qwen (`qa`), OpenRouter (`oa`), NVIDIA (`na`/`nvi`), Claude Code (`cca`), Grok (`ga`), and Cline (`cla`). Each agent is one top-level component with a `configure_fn` nested field screen and a `config_status_fn` preview snippet.

- **Codex + Qwen + OpenRouter + NVIDIA** share `agent_tui_catalog.py` / `agent_tui_install.py` for `[tui] status_line` TOML upserts. Codex writes both `~/.codex` and `~/.codex-api`.
- **Claude Code** uses `status_bar_render.py` and `claude-status-bar`; segment ids live in `status_bar_config.SEGMENT_IDS`.
- **Grok + Cline** are verify/document-only: no unsupported `config.toml` keys are invented.

Keep these in sync when adding fields:

1. Catalog/labels in `agent_tui_catalog.py` or `agent_field_selection.py`
2. Preview fixtures in `status_bar_preview.py`
3. Manifest row in `installer/components.sh`
4. Install/detect function in `lib/status_bar_install_lib.sh`
5. README field tables

## Component-based installer

```text
install.sh                     thin delegator
scripts/install_standalone.sh  framework bootstrap + preview menu wrap
lib/status_bar_install_lib.sh  per-component install/configure/detect
installer/components.sh        ISC_COMPONENTS manifest
```

`--list-components` and `--list-configurable-components` must stay side-effect free.

## Preview behavior

`status_bar_preview.py` builds fixture-based preview strings. `lib/status_bar_menu_hooks.sh` registers preview hooks on `cm_render_submenu` and `cm_render_aggregate` (via `status_bar_wrap_component_menu_preview()` in standalone install, and the master sources the same registrar). Preview rows render immediately above the help/footer line so help stays the absolute bottom line (matching `agent_field_configurator.py`); the aggregate main-menu preview lists one agent per line. Nested configurators render the same preview while fields are toggled.
