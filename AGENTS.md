# Agent guide

## Status bar: apply edits to the installed copy too

The source of truth is `claude-status-bar` (and its `status_bar_*.py` modules)
in this repo, but Claude Code runs the **installed copy** under `~/.claude/`.
Editing only the repo files will not change what shows in the status bar.

After editing the script or any module, sync the installed copy by running the
installer from the repo root:

```bash
bash install.sh --default
```

This copies the script and modules to `~/.claude/`, (idempotently) wires the
`statusLine` into `~/.claude/settings.json`, and regenerates
`~/.claude/claude-status-bar.conf`. The bar re-renders on the next prompt.

## Component-based installer

This repo uses the shared `linux_installation_scripts_functions` component
framework. Each bar segment is a selectable component; the `core` component is
the always-on base (script + modules + `settings.json` wiring + config reset).

- `install.sh` — thin delegator to `scripts/install_standalone.sh`.
- `scripts/install_standalone.sh` — resolves the framework, loads helpers,
  sources the install steps, and calls `component_main "$@"`.
- `lib/status_bar_install_lib.sh` — the per-component install functions.
- `installer/components.sh` — the `ISC_COMPONENTS` manifest (`id|label|default|fn`).

To add or rename a segment, keep three places in sync: `SEGMENT_IDS` in
`status_bar_config.py`, the `_SEGMENTS` registry in `status_bar_render.py`, and
the manifest in `installer/components.sh` (plus its wrapper in the install lib).
Keep `--list-components` side-effect free — the master installer parses it.
