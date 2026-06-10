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

## Reloading GNOME Shell

When a change needs GNOME Shell to reload (extensions, themes, shell-side
configuration), reload it in place — never log the user out or terminate the
session.

- X11 session: run
  `busctl --user call org.gnome.Shell /org/gnome/Shell org.gnome.Shell Eval s 'Meta.restart("Restarting…")'`
  (equivalent to pressing Alt+F2 → `r`). This restarts gnome-shell while
  preserving the user's open windows and applications.
- Wayland session: there is no in-place reload. Ask the user to log out and
  back in themselves. Do NOT initiate it.

Never use any of the following to force changes through, regardless of session
type:

- `gnome-session-quit` / `--logout` / `--force`
- `loginctl terminate-session …` / `loginctl kill-user …`
- `systemctl --user stop gnome-session*` or similar unit stops
- `pkill -HUP gnome-shell`, `killall gnome-shell`, or any signal that ends the
  shell process on Wayland

Losing the user's open work is a worse outcome than waiting for them to reload
manually.
