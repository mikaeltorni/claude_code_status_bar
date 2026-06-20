#!/usr/bin/env bash
# install.sh — Install the Claude Code status bar for the target user.
#
# Copies claude-status-bar and its Python modules into ~/.claude/ and wires the
# executable into the target's ~/.claude/settings.json as the `statusLine`
# command. The settings merge is idempotent and preserves every unrelated key,
# so re-running this installer is always safe.
#
# Usage:
#   bash install.sh            # install for the current user
#   sudo bash install.sh       # install for $SUDO_USER (clean-install chain)
#
# Environment overrides:
#   TARGET_USER  — user to install for (defaults to $SUDO_USER or $USER)

set -euo pipefail

# ── Target resolution ────────────────────────────────────────────────────────
TARGET_USER="${TARGET_USER:-${SUDO_USER:-$USER}}"
TARGET_HOME="$(getent passwd "$TARGET_USER" | cut -d: -f6)"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

msg() { printf '[claude_code_status_bar] %s\n' "$*"; }

# run_as_target CMD... — Run a command as the target user when invoked via sudo,
# otherwise run it directly. Keeps installed file ownership correct.
run_as_target() {
  if [[ "$(id -u)" -eq 0 && "$TARGET_USER" != "root" ]]; then
    sudo -u "$TARGET_USER" "$@"
  else
    "$@"
  fi
}

# ── Installation ─────────────────────────────────────────────────────────────
install_status_bar() {
  local claude_dir="$TARGET_HOME/.claude"
  local status_script="$claude_dir/claude-status-bar"
  local settings_file="$claude_dir/settings.json"
  local source_script="$SCRIPT_DIR/claude-status-bar"
  local format_module="$SCRIPT_DIR/status_bar_format.py"
  local render_module="$SCRIPT_DIR/status_bar_render.py"
  local logging_module="$SCRIPT_DIR/status_bar_logging.py"
  local install_module="$SCRIPT_DIR/status_bar_install.py"

  if [[ ! -f "$source_script" || ! -f "$format_module" || ! -f "$render_module" || ! -f "$logging_module" || ! -f "$install_module" ]]; then
    msg "ERROR: missing status bar source files"
    return 1
  fi

  run_as_target mkdir -p "$claude_dir"
  run_as_target install -D -m 0755 "$source_script" "$status_script"
  run_as_target install -D -m 0644 "$format_module" "$claude_dir/status_bar_format.py"
  run_as_target install -D -m 0644 "$render_module" "$claude_dir/status_bar_render.py"
  run_as_target install -D -m 0644 "$logging_module" "$claude_dir/status_bar_logging.py"
  msg "Installed status bar script to $status_script"

  run_as_target python3 "$install_module" "$settings_file" "$status_script"
  msg "Wired statusLine into $settings_file"
}

main() {
  install_status_bar
  msg "Done."
}

# Only run when executed directly, not sourced.
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  main "$@"
fi
