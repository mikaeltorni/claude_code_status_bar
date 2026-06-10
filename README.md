# claude_code_status_bar

A custom bottom **status bar** for [Claude Code](https://claude.com/claude-code).
Claude Code invokes a status-line command with a JSON payload on stdin and
renders the first line printed to stdout in the bottom bar (next to
"bypass permissions on"). This repository provides that command, plus an
idempotent installer that wires it into `~/.claude/settings.json`.

## Bar layout

```
model · effort | /full/project/path | ctx 63.2k/200.0k (31%) | 5h:90% left (~2h13m) | wk:60% left (resets Sat 01:48, ~55h33m) | +120/-8 | $1.42
```

| Segment            | Source field                         | Example                                   |
| ------------------ | ------------------------------------ | ----------------------------------------- |
| Model + effort     | `model.display_name`, `effort.level` | `Opus · low`                              |
| Project path       | `workspace.project_dir` / `cwd`      | `/home/mk/projects/...`                   |
| Context window     | `context_window.*`                   | `ctx 63.2k/200.0k (31%)`                  |
| 5-hour rate limit  | `rate_limits.five_hour`              | `5h:90% left (~2h13m)`                    |
| Weekly rate limit  | `rate_limits.seven_day`              | `wk:60% left (resets Sat 01:48, ~55h33m)` |
| Diff line count    | `cost.total_lines_added/removed`     | `+120/-8`                                 |
| Total session cost | `cost.total_cost_usd`                | `$1.42`                                   |

### Weekly reset day

The weekly rate-limit segment shows **both** the reset weekday and clock time
(`resets Sat 01:48`) and the remaining duration (`~55h33m`). The weekday and
time are derived from the `resets_at` unix timestamp rendered in the machine's
**local** timezone via `time.localtime`, so it always reflects the current
system clock.

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

## License

See [LICENSE.md](LICENSE.md).

## Disclaimer

This software is provided under the MIT License on an **“as is”** basis, without warranties of any kind. To the maximum extent permitted by applicable law, the authors and copyright holders shall not be liable for any claims, damages, losses, or other liability arising from the use of this software.

You are solely responsible for determining whether this software is suitable, safe, lawful, and appropriate for your intended use. Unless explicitly stated otherwise, this project is general-purpose software and is not designed, tested, certified, or approved for safety-critical, medical, automotive, aviation, industrial-control, life-support, cybersecurity-critical, financial-critical, or other high-risk use cases.

The authors and copyright holders make no guarantees regarding security, reliability, availability, correctness, compliance, non-infringement, or fitness for any particular purpose.

This notice is intended to clarify the nature of the project and does not impose additional restrictions beyond the MIT License.
