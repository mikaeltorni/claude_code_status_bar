# claude_code_status_bar

> Part of [installation_scripts](https://github.com/mikaeltorni/installation_scripts) — the master installer that orchestrates a productivity-focused Ubuntu 24.04 desktop setup (workspaces, hotkeys, window tiling, programming tools, and more). Tested on Ubuntu 24.04.4 LTS.

A shared **agent TUI display** repository for the coding-agent CLIs used in this setup chain. Despite the repository name, it owns status-bar and rich-TUI configuration for **Codex**, **Qwen (local Codex)**, **OpenRouter Codex**, **NVIDIA Codex**, **Claude Code**, **Grok**, and **Cline** — not Claude Code alone.

The master installer runs this repository immediately after the CLI installer. Its component menu lists the agents in this order:

1. **Codex** (`codex_tui`) — `ca`
2. **Qwen (local Codex)** (`qwen_tui`) — `qa`
3. **OpenRouter (Codex)** (`openrouter_tui`) — `oa`
4. **NVIDIA (Codex)** (`nvidia_tui`) — `na` / `nvi`
5. **Claude Code** (`claude_tui`) — `cca`
6. **Grok** (`grok_tui`) — `ga`
7. **Cline** (`cline_tui`) — `cla`

Press **RIGHT** on any row to open a nested field checklist. A **simulated status-bar preview** appears at the bottom of that screen and on the main component menu while a row is highlighted.

## Launcher and config-path mapping

| Agent | ACC / launcher | Status/TUI config written by this repo |
| ----- | -------------- | ---------------------------------------- |
| Codex | `ca` | `~/.codex/config.toml` **and** `~/.codex-api/config.toml` (`[tui] status_line`) |
| Qwen (local Codex) | `qa` | `~/.codex-qwen/config.toml` (`[tui] status_line`) |
| OpenRouter (Codex) | `oa` | `~/.codex-openrouter/config.toml` (`[tui] status_line`) |
| NVIDIA (Codex) | `na` / `nvi` | `~/.codex-nvidia/config.toml` (`[tui] status_line`) |
| Claude Code | `cca` | `~/.claude/claude-status-bar.conf` + `statusLine` in `~/.claude/settings.json` |
| Grok | `ga` | Native rich TUI only — **no** writable `status_line` key in `~/.grok/config.toml` |
| Cline | `cla` | Native rich TUI only — **no** external status-line settings API |

Field selections are staged in `~/.config/claude_code_status_bar/field-selections.json` and applied on install/reconfigure.

### Setup-chain ordering and ACC coordination

The master installer runs **`claude_code_status_bar` before `agent_command_center`**. ACC’s Local Codex (`qa`) refresh regenerates `~/.codex-qwen/config.toml`; it now reads `[tui] status_line` from `field-selections.json` when that file exists (via `agent_field_selection.py toml-array qwen`). ACC **postflight** also re-runs `claude_code_status_bar/install.sh --select codex_tui,qwen_tui` so `ca` (`~/.codex-api`) and `qa` homes stay aligned after ACC creates or refreshes them.

If you change field selections after an ACC install, re-apply with:

```bash
bash ~/projects/claude_code_status_bar/install.sh --select codex_tui,qwen_tui
```

—or re-run `agent_command_center/install.sh` (postflight performs the same re-apply).

`ca` and the default `~/.codex` home intentionally share the **same** Codex `status_line` selection; `~/.codex-api` receives only the `[tui]` upsert (other keys are owned by ACC/plugin setup).

Codex and Qwen share one Codex-style token catalog and TOML writer (`agent_tui_catalog.py`). Claude Code keeps its custom `claude-status-bar` renderer.

## Codex / Qwen field tokens

These map to `[tui] status_line` in Codex-style `config.toml` files (documented in the [Codex config reference](https://developers.openai.com/codex/config-reference)):

| Token | Label |
| ----- | ----- |
| `model-with-reasoning` | Model + reasoning effort |
| `current-dir` | Current directory (active worktree) |
| `context-remaining` | Context remaining |
| `five-hour-limit` | 5-hour rate limit |
| `weekly-limit` | Weekly rate limit |
| `run-state` | Run state |
| `context-used` | Context used |
| `codex-version` | Codex version |
| `pull-request-number` | Pull request number |
| `branch-changes` | Branch changes |
| `used-tokens` | Used tokens |
| `total-input-tokens` | Total input tokens |
| `total-output-tokens` | Total output tokens |

> **Removed from the Codex status line:** the project-root basename
> (`project-name`) and the Git branch (`git-branch`) are no longer part of the
> Codex TUI status line — neither token is selectable anymore — so the active
> worktree identity (`current-dir`) stays uncluttered. This affects only the
> Codex-style instances (Codex, Qwen, OpenRouter, NVIDIA). Claude Code's
> `project` segment is unchanged.

**Default Codex selection:** `model-with-reasoning`, `current-dir`,
`context-remaining`, `branch-changes`, `used-tokens`, `total-input-tokens`, and
`total-output-tokens`. The active worktree is shown by `current-dir` (the
worktree directory path), which distinguishes linked worktrees from one
another. The project-root basename (`project-name`) and the Git branch
(`git-branch`) are no longer part of the status line (neither is selectable), so
the worktree identity stays uncluttered. The rate-limit, run-state, context-used,
version, and pull-request fields remain selectable but are off by default.

**Default Qwen selection:** the same rich default as Codex, with the active
worktree shown via `current-dir`; no inline project-root basename or branch.

## Claude Code segments

Claude Code invokes a status-line command with a JSON payload on stdin and renders the first stdout line in the bottom bar. This repository provides that command plus segment selection.

```
Opus · low | claude_code_status_bar | 63.2k/200.0k (31%) | 5h:90% (~2h13m) | wk:60% (Sat 22:22) | +120/-8 | $1.42
```

| Segment | Component id | Source field | Example |
| ------- | ------------ | ------------ | ------- |
| Model + effort | `model` | `model.display_name`, `effort.level` | `Opus · low` |
| Repository name | `project` | `workspace.project_dir` / `cwd` | `claude_code_status_bar` |
| Context window | `context` | `context_window.*` | `63.2k/200.0k (31%)` |
| 5-hour rate limit | `five_hour` | `rate_limits.five_hour` | `5h:90% (~2h13m)` |
| Weekly rate limit | `weekly` | `rate_limits.seven_day` | `wk:60% (Sat 22:22)` |
| Diff line count | `diff` | `cost.total_lines_added/removed` | `+120/-8` |
| Total session cost | `cost` | `cost.total_cost_usd` | `$1.42` |

All seven segments are default-on.

## Grok and Cline (native display)

Grok and Cline ship rich native terminal displays. This installer **verifies** the CLI is present and documents the native elements in the nested checklist (preview-only toggles — nothing is written to unsupported upstream keys):

**Grok reference fields:** model, working-directory, session-state, context-usage, tool-activity.

**Cline reference fields:** model, workspace, context-window, session-cost, diff-stats.

## Installation

```bash
# Interactive component menu with live previews
bash install.sh

# Install every default-on agent display
bash install.sh --default

# Install every component
bash install.sh --all

# Install or reconfigure specific agents
bash install.sh --select codex_tui,claude_tui

# Open one nested field screen non-interactively (TTY required for toggles)
bash install.sh --configure-component codex_tui

# List components (id<TAB>label<TAB>default[<TAB>section])
bash install.sh --list-components

# List nested configurators
bash install.sh --list-configurable-components

# Install for another user (clean-install chain under sudo)
sudo bash install.sh --default
```

### Uninstalling

Every component is individually removable — nothing here is a one-way install:

```bash
# Remove one or more agent displays
bash install.sh --uninstall codex_tui,claude_tui
```

Each uninstall removes **only** what this repo added: the `[tui] status_line`
assignment in the Codex-style `config.toml` (all other keys, comments and
tables are preserved byte-for-byte, and a `[tui]` table left empty is dropped),
or Claude Code's `statusLine` key plus the installed `claude-status-bar` script
and its Python modules under `~/.claude`. Your own segment configuration
(`~/.claude/claude-status-bar.conf`) and every unrelated setting are left in
place. Grok and Cline render natively from their own CLIs, so their uninstall is
a reported no-op. Uninstalling a component that was never installed is safe.

| Variable | Default | Purpose |
| -------- | ------- | ------- |
| `TARGET_USER` | `$SUDO_USER` or `$USER` | User whose agent homes are configured |
| `TARGET_HOME` | target user's home | Override for clean-home tests |

After editing the Claude renderer, sync the installed copy:

```bash
bash install.sh --select claude_tui
```

### Troubleshooting: blank Claude status line

Claude Code **does not run** the `statusLine` command when workspace trust has
not been accepted for that project's git root (parent-folder trust does not
cross into a separate repository). The installed script never gets stdin, so the
bottom bar only shows `bypass permissions on`.

The installer marks every existing path under `~/.claude.json` → `projects` as
trusted (`hasTrustDialogAccepted: true`) when you install/reconfigure
`claude_tui`. For a single new repo without reinstalling:

```bash
python3 ~/.claude/status_bar_install.py --ensure-trust ~/.claude.json /path/to/repo
```

Then continue the session (or start a new one) so the bar refreshes. Smoke-test
the installed entry point:

```bash
printf '%s' '{"model":{"display_name":"Opus"},"context_window":{"total_input_tokens":1000,"context_window_size":200000,"used_percentage":1}}' \
  | python3 ~/.claude/claude-status-bar
```

## Repository dependencies

This repository installs and runs **standalone**. It is consumed by `linux_programming_setup` in the master chain; that is a one-way relationship.

See [installation_scripts/DEPENDENCIES.md](https://github.com/mikaeltorni/installation_scripts/blob/master/DEPENDENCIES.md).

## Development layout

```text
claude-status-bar              Claude JSON stdin → stdout command
status_bar_render.py           Per-segment registry + assembly
status_bar_format.py           Token and reset-time formatting
status_bar_config.py           Claude segment selection
status_bar_preview.py          Simulated previews for every agent TUI
agent_tui_catalog.py           Shared Codex/Qwen token catalog + TOML writer
agent_field_selection.py       Per-agent field-selection persistence
agent_field_configurator.py    Nested checklist TUI with live preview
agent_tui_install.py           Codex/Qwen TOML install helper
status_bar_segment_install.py  Claude segment config writer
installer/components.sh        Agent TUI component manifest
lib/status_bar_install_lib.sh  Install/configure/detect functions
```

Run tests:

```bash
python3 -m pytest -q
```

Pipe a sample Claude payload:

```bash
echo '{"model":{"display_name":"Opus"},"workspace":{"project_dir":"/work/claude_code_status_bar"}}' \
  | python3 claude-status-bar
```

## License

See [LICENSE.md](LICENSE.md).
