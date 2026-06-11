# claude_code_status_bar

A custom bottom **status bar** for [Claude Code](https://claude.com/claude-code).
Claude Code invokes a status-line command with a JSON payload on stdin and
renders the first line printed to stdout in the bottom bar (next to
"bypass permissions on"). This repository provides that command, plus an
idempotent installer that wires it into `~/.claude/settings.json`.

## Bar layout

```
Opus · low | claude_code_status_bar | 63.2k/200.0k (31%) | 5h:90% (~2h13m) | wk:60% (Sat 22:22) | +120/-8 | $1.42
```

| Segment            | Source field                         | Example                    |
| ------------------ | ------------------------------------ | -------------------------- |
| Model + effort     | `model.display_name`, `effort.level` | `Opus · low`               |
| Repository name    | `workspace.project_dir` / `cwd`      | `claude_code_status_bar`   |
| Context window     | `context_window.*`                   | `63.2k/200.0k (31%)`       |
| 5-hour rate limit  | `rate_limits.five_hour`              | `5h:90% (~2h13m)`          |
| Weekly rate limit  | `rate_limits.seven_day`              | `wk:60% (Sat 22:22)`       |
| Diff line count    | `cost.total_lines_added/removed`     | `+120/-8`                  |
| Total session cost | `cost.total_cost_usd`                | `$1.42`                    |

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

The installer copies `claude-status-bar` into `~/.claude/` and sets the
`statusLine` key in `~/.claude/settings.json`. It is **idempotent** and
preserves every unrelated setting.

```bash
# Install for the current user
bash install.sh

# Install for another user (used by the clean-install chain under sudo)
sudo bash install.sh
```

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

The status bar is a single, dependency-free Python 3 script. Test it by piping
a sample status-line payload through it:

```bash
echo '{"model":{"display_name":"Opus"},"rate_limits":{"seven_day":{"used_percentage":40,"resets_at":1700000000}}}' \
  | python3 claude-status-bar
```

### Debugging

The bar must emit exactly one stdout line, so diagnostics are opt-in and routed
to a file. Set `CLAUDE_STATUS_BAR_DEBUG=1` to record events (such as malformed
input) under `<script-dir>/.log/status-bar.log`:

```bash
echo 'not json' | CLAUDE_STATUS_BAR_DEBUG=1 python3 claude-status-bar
cat .log/status-bar.log
```

The `.log/` directory is git-ignored — log files are runtime artifacts.

## License

See [LICENSE.md](LICENSE.md).

## Disclaimer

This software is provided under the MIT License on an **“as is”** basis, without warranties of any kind. To the maximum extent permitted by applicable law, the authors and copyright holders shall not be liable for any claims, damages, losses, or other liability arising from the use of this software.

You are solely responsible for determining whether this software is suitable, safe, lawful, and appropriate for your intended use. Unless explicitly stated otherwise, this project is general-purpose software and is not designed, tested, certified, or approved for safety-critical, medical, automotive, aviation, industrial-control, life-support, cybersecurity-critical, financial-critical, or other high-risk use cases.

The authors and copyright holders make no guarantees regarding security, reliability, availability, correctness, compliance, non-infringement, or fitness for any particular purpose.

This notice is intended to clarify the nature of the project and does not impose additional restrictions beyond the MIT License.
