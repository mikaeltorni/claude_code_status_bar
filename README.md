# claude_code_status_bar

> Part of [installation_scripts](https://github.com/mikaeltorni/installation_scripts) — the master installer that orchestrates a productivity-focused Ubuntu 24.04 desktop setup (workspaces, hotkeys, window tiling, programming tools, and more). Tested on Ubuntu 24.04.4 LTS.

A custom bottom **status bar** for [Claude Code](https://claude.com/claude-code).
Claude Code invokes a status-line command with a JSON payload on stdin and
renders the first line printed to stdout in the bottom bar (next to
"bypass permissions on"). This repository provides that command, plus an
idempotent, **component-based** installer that wires it into
`~/.claude/settings.json` and lets you pick exactly which segments appear.

## Repository dependencies

This repository installs and runs **standalone** — it has **no** dependency on
any other setup repository. It is *consumed by*
`linux_programming_setup`, which wires this status-line command into Claude
Code; that is a one-way relationship and does not create a dependency in this
direction.

See the full cross-repository map in
[installation_scripts/DEPENDENCIES.md](https://github.com/mikaeltorni/installation_scripts/blob/master/DEPENDENCIES.md).

## Bar layout

```
Opus · low | claude_code_status_bar | 63.2k/200.0k (31%) | 5h:90% (~2h13m) | wk:60% (Sat 22:22) | +120/-8 | $1.42
```

| Segment            | Component id | Source field                         | Example                    |
| ------------------ | ------------ | ------------------------------------ | -------------------------- |
| Model + effort     | `model`      | `model.display_name`, `effort.level` | `Opus · low`               |
| Repository name    | `project`    | `workspace.project_dir` / `cwd`      | `claude_code_status_bar`   |
| Context window     | `context`    | `context_window.*`                   | `63.2k/200.0k (31%)`       |
| 5-hour rate limit  | `five_hour`  | `rate_limits.five_hour`              | `5h:90% (~2h13m)`          |
| Weekly rate limit  | `weekly`     | `rate_limits.seven_day`              | `wk:60% (Sat 22:22)`       |
| Diff line count    | `diff`       | `cost.total_lines_added/removed`     | `+120/-8`                  |
| Total session cost | `cost`       | `cost.total_cost_usd`                | `$1.42`                    |

Each segment is an independently selectable installer **component** (the
`core` component installs the script, modules, and `settings.json` wiring and is
always on). See [Installation](#installation) for how to choose them.

The rate-limit percentages are **remaining** capacity (`100 - used_percentage`),
rounded to whole numbers. The project segment shows only the **basename** of the
workspace directory, not the full path.

### Weekly reset day

The weekly rate-limit segment shows the reset weekday and clock time
(`Sat 22:22`), derived from the `resets_at` unix timestamp rendered in the
machine's **local** timezone via `time.localtime`, so it always reflects the
current system clock. The 5-hour segment instead shows the remaining duration
(`~2h13m`).

## Installation

The installer copies `claude-status-bar` and its Python modules into
`~/.claude/`, sets the `statusLine` key in `~/.claude/settings.json`, and writes
your segment selection to `~/.claude/claude-status-bar.conf`. It is
**idempotent** and preserves every unrelated setting.

It uses the shared
[`linux_installation_scripts_functions`](https://github.com/mikaeltorni/linux_installation_scripts_functions)
component framework, so it exposes the same selection contract as the rest of
the setup family:

```bash
# Interactive component menu on a terminal; default-on components otherwise
bash install.sh

# Install the core plus every default-on segment, no prompts
bash install.sh --default

# Install every component
bash install.sh --all

# Install exactly these components (core is required for a working bar)
bash install.sh --select core,model,context,cost

# List components as: id<TAB>label<TAB>default
bash install.sh --list-components

# Install for another user (used by the clean-install chain under sudo)
sudo bash install.sh --default
```

Every segment is **default-on**, so a default install reproduces the full bar
shown above. The `core` component (script + modules + `settings.json` wiring) is
always on — the bar mechanism works no matter which segments you pick.

### Customizing which segments appear

Segment selection is decided at **install time**: re-run the installer with a
different `--select` to change the bar. The installer regenerates
`~/.claude/claude-status-bar.conf` (one enabled segment id per line) on every
run. If that config file is absent — e.g. a manual install that only copies the
script — the renderer shows **every** segment, so nothing is lost.

Environment overrides:

| Variable      | Default                   | Purpose                          |
| ------------- | ------------------------- | -------------------------------- |
| `TARGET_USER` | `$SUDO_USER` or `$USER`   | User whose `~/.claude` is set up |

## How it fits the setup chain

This repository is cloned and configured automatically as part of the
`linux_programming_setup` installer, which runs
`claude_code_status_bar/install.sh` after the editor setup. See that
repository's `install.sh` for the integration point.

## Manual configuration

If you prefer to wire it up by hand, add this to `~/.claude/settings.json`:

```json
{
  "statusLine": {
    "type": "command",
    "command": "python3 /home/<you>/.claude/claude-status-bar"
  }
}
```

## Development

The status bar is dependency-free Python 3 code:

```text
claude-status-bar       JSON input, diagnostics, and stdout
status_bar_render.py    Per-segment registry + status-line assembly
status_bar_format.py    Token and reset-time formatting
status_bar_config.py    Segment selection (reads/writes claude-status-bar.conf)
status_bar_logging.py   Centralized, file-only logging (on by default)
status_bar_install.py   Idempotent settings.json wiring (used by install.sh)
```

The installer shell lives in `install.sh` (a thin delegator),
`scripts/install_standalone.sh` (framework bootstrap), `lib/` (install steps),
and `installer/components.sh` (the component manifest).

The executable imports `build_status_line` from `status_bar_render`, which in
turn imports the formatting helpers from `status_bar_format`. Runtime modules
log through the shared `status_bar_logging` utility (see Debugging below). Run
the full regression suite with:

```bash
python3 -m pytest -q
```

Test the complete command by piping a sample status-line payload through it:

```bash
echo '{"model":{"display_name":"Opus"},"rate_limits":{"seven_day":{"used_percentage":40,"resets_at":1700000000}}}' \
  | python3 claude-status-bar
```

### Debugging

The bar must emit exactly one stdout line, so diagnostics never touch stdout or
stderr — they are routed to a file. File logging is **on by default**, recording
events (such as malformed input) under `<script-dir>/.log/status-bar.log`:

```bash
echo 'not json' | python3 claude-status-bar
cat .log/status-bar.log
```

Set `CLAUDE_STATUS_BAR_DEBUG` to a falsy value (`0`, `false`, `no`, or empty) to
opt out and silence file logging:

```bash
echo 'not json' | CLAUDE_STATUS_BAR_DEBUG=0 python3 claude-status-bar
```

The `.log/` directory is git-ignored — log files are runtime artifacts.

## License

See [LICENSE.md](LICENSE.md).

## Disclaimer

This software is provided under the MIT License on an **“as is”** basis, without warranties of any kind. To the maximum extent permitted by applicable law, the authors and copyright holders shall not be liable for any claims, damages, losses, or other liability arising from the use of this software.

You are solely responsible for determining whether this software is suitable, safe, lawful, and appropriate for your intended use. Unless explicitly stated otherwise, this project is general-purpose software and is not designed, tested, certified, or approved for safety-critical, medical, automotive, aviation, industrial-control, life-support, cybersecurity-critical, financial-critical, or other high-risk use cases.

The authors and copyright holders make no guarantees regarding security, reliability, availability, correctness, compliance, non-infringement, or fitness for any particular purpose.

This notice is intended to clarify the nature of the project and does not impose additional restrictions beyond the MIT License.
