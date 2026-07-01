#!/usr/bin/env bash
# components.sh - Component manifest for claude_code_status_bar.
#
# Entry format: "id|label|default(on/off)|function". The functions are defined
# in lib/status_bar_install_lib.sh, sourced by scripts/install_standalone.sh.
#
# "core" is the always-on base component: it installs the executable, the Python
# modules, the settings.json wiring, and resets the segment-selection config. It
# is listed first so the per-segment components append into a clean file. Every
# segment is default-on, so a default (or non-interactive) install reproduces the
# full bar exactly as before component selection existed. Deselecting a segment
# simply omits it from the installed bar.

ISC_REPO_NAME="claude_code_status_bar"
ISC_REPO_LABEL="Claude Code status bar"

ISC_COMPONENTS=(
  "codex_tui|Codex rich native TUI status bar|on|status_bar_configure_codex_tui"
  "cline_tui|Cline rich native TUI display|on|status_bar_configure_cline_tui"
  "core|Status bar script, modules, and settings.json wiring|on|status_bar_install_core"
  "model|Model name + reasoning effort segment|on|status_bar_enable_model"
  "project|Repository / workspace name segment|on|status_bar_enable_project"
  "context|Context-window usage segment|on|status_bar_enable_context"
  "five_hour|5-hour rate-limit segment|on|status_bar_enable_five_hour"
  "weekly|Weekly rate-limit segment|on|status_bar_enable_weekly"
  "diff|Diff line-count segment|on|status_bar_enable_diff"
  "cost|Total session cost segment|on|status_bar_enable_cost"
)
