# Agent guide

## Status bar: apply edits to the installed copy too

The source of truth is `claude-status-bar` in this repo, but Claude Code runs
the **installed copy** at `~/.claude/claude-status-bar`. Editing only the repo
file will not change what shows in the status bar.

After editing `claude-status-bar`, sync the installed copy by running the
installer from the repo root:

```bash
bash install.sh
```

This copies the script to `~/.claude/claude-status-bar` and (idempotently)
wires it into `~/.claude/settings.json`. The bar re-renders on the next prompt.
