#!/usr/bin/env bash
# status_bar_install_lib.sh - install-step functions for the five-agent status bar.

_sb_claude_dir()   { printf '%s/.claude' "$TARGET_HOME"; }
_sb_config_path()  { printf '%s/.claude/claude-status-bar.conf' "$TARGET_HOME"; }
_sb_config_module(){ printf '%s/status_bar_config.py' "$REPO_DIR"; }
_sb_selection_path() {
  python3 "$REPO_DIR/agent_field_selection.py" path "$TARGET_HOME"
}

# Materialize default field selections so ACC and later re-runs share one file.
_sb_ensure_selection_defaults() {
  local path
  path="$(_sb_selection_path)"
  if ! run_as_target test -f "$path"; then
    run_as_target mkdir -p "$(dirname "$path")"
    run_as_target python3 "$REPO_DIR/agent_field_selection.py" init "$TARGET_HOME"
  fi
}

# status_bar_configure_*_fields - nested configurators (configure_fn).
status_bar_configure_codex_fields() {
  run_as_target env TARGET_HOME="$TARGET_HOME" \
    python3 "$REPO_DIR/agent_field_configurator.py" codex "$TARGET_HOME"
}
status_bar_configure_qwen_fields() {
  run_as_target env TARGET_HOME="$TARGET_HOME" \
    python3 "$REPO_DIR/agent_field_configurator.py" qwen "$TARGET_HOME"
}
status_bar_configure_openrouter_fields() {
  run_as_target env TARGET_HOME="$TARGET_HOME" \
    python3 "$REPO_DIR/agent_field_configurator.py" openrouter "$TARGET_HOME"
}
status_bar_configure_nvidia_fields() {
  run_as_target env TARGET_HOME="$TARGET_HOME" \
    python3 "$REPO_DIR/agent_field_configurator.py" nvidia "$TARGET_HOME"
}
status_bar_configure_claude_fields() {
  run_as_target env TARGET_HOME="$TARGET_HOME" \
    python3 "$REPO_DIR/agent_field_configurator.py" claude "$TARGET_HOME"
}
status_bar_configure_grok_fields() {
  run_as_target env TARGET_HOME="$TARGET_HOME" \
    python3 "$REPO_DIR/agent_field_configurator.py" grok "$TARGET_HOME"
}
status_bar_configure_cline_fields() {
  run_as_target env TARGET_HOME="$TARGET_HOME" \
    python3 "$REPO_DIR/agent_field_configurator.py" cline "$TARGET_HOME"
}

# config_status_fn previews for the main component menu.
status_bar_codex_preview_status() {
  python3 "$REPO_DIR/status_bar_preview.py" component codex_tui "$TARGET_HOME" 2>/dev/null || true
}
status_bar_qwen_preview_status() {
  python3 "$REPO_DIR/status_bar_preview.py" component qwen_tui "$TARGET_HOME" 2>/dev/null || true
}
status_bar_openrouter_preview_status() {
  python3 "$REPO_DIR/status_bar_preview.py" component openrouter_tui "$TARGET_HOME" 2>/dev/null || true
}
status_bar_nvidia_preview_status() {
  python3 "$REPO_DIR/status_bar_preview.py" component nvidia_tui "$TARGET_HOME" 2>/dev/null || true
}
status_bar_claude_preview_status() {
  python3 "$REPO_DIR/status_bar_preview.py" component claude_tui "$TARGET_HOME" 2>/dev/null || true
}
status_bar_grok_preview_status() {
  python3 "$REPO_DIR/status_bar_preview.py" component grok_tui "$TARGET_HOME" 2>/dev/null || true
}
status_bar_cline_preview_status() {
  python3 "$REPO_DIR/status_bar_preview.py" component cline_tui "$TARGET_HOME" 2>/dev/null || true
}

_sb_write_codex_tokens() {
  local config="$1" agent="${2:-codex}"
  local tokens
  # Existing installs keep their field selections, so migrate only the
  # Codex-style defaults that predate the project-name/worktree item. Keep this
  # in the shared write path so a single-client install repairs that client too.
  run_as_target python3 "$REPO_DIR/agent_field_selection.py" migrate "$(_sb_selection_path)"
  tokens="$(python3 "$REPO_DIR/agent_field_selection.py" get "$agent" "$(_sb_selection_path)")"
  run_as_target python3 "$REPO_DIR/agent_tui_install.py" write "$config" "$tokens"
}

status_bar_install_codex() {
  local config
  _sb_ensure_selection_defaults
  for config in "$TARGET_HOME/.codex/config.toml" "$TARGET_HOME/.codex-api/config.toml"; do
    _sb_write_codex_tokens "$config" codex
  done
  msg "Configured Codex native TUI status bar (~/.codex and ~/.codex-api for ca)"
}

detect_codex_tui() {
  local config="$TARGET_HOME/.codex/config.toml"
  [[ -f "$config" ]] && grep -q 'status_line' "$config"
}

status_bar_install_qwen() {
  _sb_write_codex_tokens "$TARGET_HOME/.codex-qwen/config.toml" qwen
  msg "Configured Qwen (local Codex) native TUI status bar (~/.codex-qwen for qa)"
}

detect_qwen_tui() {
  local config="$TARGET_HOME/.codex-qwen/config.toml"
  [[ -f "$config" ]] && grep -q 'status_line' "$config"
}

status_bar_install_openrouter() {
  _sb_write_codex_tokens "$TARGET_HOME/.codex-openrouter/config.toml" openrouter
  msg "Configured OpenRouter (Codex) native TUI status bar (~/.codex-openrouter for oa)"
}

detect_openrouter_tui() {
  local config="$TARGET_HOME/.codex-openrouter/config.toml"
  [[ -f "$config" ]] && grep -q 'status_line' "$config"
}

status_bar_install_nvidia() {
  _sb_write_codex_tokens "$TARGET_HOME/.codex-nvidia/config.toml" nvidia
  msg "Configured NVIDIA (Codex) native TUI status bar (~/.codex-nvidia for na)"
}

detect_nvidia_tui() {
  local config="$TARGET_HOME/.codex-nvidia/config.toml"
  [[ -f "$config" ]] && grep -q 'status_line' "$config"
}

status_bar_install_claude_core() {
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
  msg "Wired statusLine into $settings_file (cca)"
}

status_bar_install_claude() {
  local segments config_path
  status_bar_install_claude_core || return $?
  segments="$(python3 "$REPO_DIR/agent_field_selection.py" get claude "$(_sb_selection_path)")"
  config_path="$(_sb_config_path)"
  run_as_target python3 "$(_sb_config_module)" init "$config_path"
  run_as_target python3 "$REPO_DIR/status_bar_segment_install.py" "$config_path" "$segments"
  msg "Enabled Claude Code status-bar segments at $config_path"
}

detect_claude_tui() {
  [[ -x "$(_sb_claude_dir)/claude-status-bar" ]] \
    && [[ -f "$(_sb_config_path)" ]]
}

status_bar_install_grok() {
  if ! run_as_target bash -lc 'command -v grok >/dev/null'; then
    msg "Grok CLI is not installed; native rich TUI will be available after CLI installation (ga)"
    return 0
  fi
  msg "Grok rich TUI is provided natively by the installed Grok CLI (~/.grok for ga)"
}

detect_grok_tui() {
  run_as_target bash -lc 'command -v grok >/dev/null'
}

status_bar_install_cline() {
  if ! run_as_target bash -lc 'command -v cline >/dev/null'; then
    msg "Cline CLI is not installed; native rich TUI will be available after CLI installation (cla)"
    return 0
  fi
  msg "Cline rich TUI is provided natively by the installed Cline CLI (cla)"
}

detect_cline_tui() {
  run_as_target bash -lc 'command -v cline >/dev/null'
}

# Register shared menu preview hooks (submenu + aggregate).
status_bar_wrap_component_menu_preview() {
  # shellcheck source=lib/status_bar_menu_hooks.sh
  source "$REPO_DIR/lib/status_bar_menu_hooks.sh"
  STATUS_BAR_REPO_DIR="$REPO_DIR"
  status_bar_register_menu_preview_hooks
}
