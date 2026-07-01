#!/usr/bin/env bash
# status_bar_install_lib.sh - install-step functions for the status bar.
#
# Sourced by scripts/install_standalone.sh, which provides the shared installer
# helpers (run_as_target, msg) and the resolved REPO_DIR / TARGET_HOME. Each
# function here installs one selectable component declared in
# installer/components.sh:
#
#   * status_bar_install_core enables the always-on "core" component: it copies
#     the executable and Python modules into ~/.claude, wires the statusLine
#     command into settings.json, and resets the segment-selection config to a
#     clean (empty) state. It is listed first in the manifest so the per-segment
#     components below append into a known-clean file.
#   * status_bar_enable_<segment> appends its segment id to the installed config
#     so the renderer shows it. They are idempotent and create the config if the
#     core component was not selected.
#
# The installed config lists exactly the selected segments. The renderer treats
# an absent config as "show everything", so manual installs are unaffected.

# Absolute path of the installed ~/.claude directory and its artifacts. These
# read TARGET_HOME, exported by the standalone bootstrap.
_sb_claude_dir()   { printf '%s/.claude' "$TARGET_HOME"; }
_sb_config_path()  { printf '%s/.claude/claude-status-bar.conf' "$TARGET_HOME"; }
# Run the config CLI from the repo copy, which is always present, so segment
# components work even when the core component (which installs the module into
# ~/.claude) was not selected. Only the config *path* lives under ~/.claude.
_sb_config_module(){ printf '%s/status_bar_config.py' "$REPO_DIR"; }

# status_bar_configure_codex_tui - preserve config.toml while setting Codex's
# supported native status-line fields. No external renderer is required.
status_bar_configure_codex_tui() {
  local config="$TARGET_HOME/.codex/config.toml"
  run_as_target python3 "$REPO_DIR/agent_tui_install.py" "$config"
  msg "Configured Codex native TUI status bar"
}

# status_bar_configure_cline_tui - document and verify Cline's built-in rich
# terminal display; current Cline exposes no external status-line settings API.
status_bar_configure_cline_tui() {
  if ! run_as_target bash -lc 'command -v cline >/dev/null'; then
    msg "Cline CLI is not installed; its native rich TUI will be available after CLI installation"
    return 0
  fi
  msg "Cline rich TUI is provided natively by the installed Cline CLI"
}

# status_bar_install_core - Install the core executable, modules, and wiring.
#
# Copies claude-status-bar plus every Python module into ~/.claude, wires the
# statusLine command into settings.json (idempotent, preserving unrelated keys),
# and (re)initializes the segment config to empty. Returns non-zero only when a
# required source file is missing.
status_bar_install_core() {
  local claude_dir status_script settings_file source_script
  claude_dir="$(_sb_claude_dir)"
  status_script="$claude_dir/claude-status-bar"
  settings_file="$claude_dir/settings.json"
  source_script="$REPO_DIR/claude-status-bar"

  local module modules=(
    status_bar_format.py
    status_bar_render.py
    status_bar_logging.py
    status_bar_config.py
    status_bar_install.py
  )

  if [[ ! -f "$source_script" ]]; then
    msg "ERROR: missing status bar source: $source_script"
    return 1
  fi
  for module in "${modules[@]}"; do
    if [[ ! -f "$REPO_DIR/$module" ]]; then
      msg "ERROR: missing status bar module: $REPO_DIR/$module"
      return 1
    fi
  done

  run_as_target mkdir -p "$claude_dir"
  run_as_target install -D -m 0755 "$source_script" "$status_script"
  for module in "${modules[@]}"; do
    run_as_target install -D -m 0644 "$REPO_DIR/$module" "$claude_dir/$module"
  done
  msg "Installed status bar script and modules to $claude_dir"

  run_as_target python3 "$claude_dir/status_bar_install.py" "$settings_file" "$status_script"
  msg "Wired statusLine into $settings_file"

  # Reset the segment selection to empty; segment components append themselves.
  run_as_target python3 "$(_sb_config_module)" init "$(_sb_config_path)"
  msg "Initialized segment selection at $(_sb_config_path)"
}

# _sb_enable_segment ID - Append segment ID to the installed config.
#
# Shared implementation behind the per-segment component functions. Idempotent
# and self-healing: if the core component was deselected and no config exists,
# status_bar_config.py creates it before appending.
_sb_enable_segment() {
  local segment="$1"
  run_as_target python3 "$(_sb_config_module)" enable "$segment" "$(_sb_config_path)"
  msg "Enabled '$segment' status-bar segment"
}

# Per-segment component entry points referenced by installer/components.sh. Each
# is a thin wrapper so the manifest maps an id to a named, greppable function.
status_bar_enable_model()     { _sb_enable_segment model; }
status_bar_enable_project()   { _sb_enable_segment project; }
status_bar_enable_context()   { _sb_enable_segment context; }
status_bar_enable_five_hour() { _sb_enable_segment five_hour; }
status_bar_enable_weekly()    { _sb_enable_segment weekly; }
status_bar_enable_diff()      { _sb_enable_segment diff; }
status_bar_enable_cost()      { _sb_enable_segment cost; }
