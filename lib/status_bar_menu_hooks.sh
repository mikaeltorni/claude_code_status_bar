#!/usr/bin/env bash
# status_bar_menu_hooks.sh - shared preview hooks for component menus.
#
# Registers wrappers around cm_render_submenu and cm_render_aggregate so the
# claude_code_status_bar repository shows a simulated status-bar preview as the
# last screen line (after the footer). Safe to call from the standalone
# installer or the master aggregate menu.

STATUS_BAR_MENU_HOOKS_REGISTERED="${STATUS_BAR_MENU_HOOKS_REGISTERED:-0}"

# Resolve the status-bar repository root for preview helpers.
status_bar_repo_dir() {
  if [[ -n "${STATUS_BAR_REPO_DIR:-}" && -f "${STATUS_BAR_REPO_DIR}/status_bar_preview.py" ]]; then
    printf '%s' "$STATUS_BAR_REPO_DIR"
    return 0
  fi
  if [[ -n "${REPO_DIR:-}" && -f "${REPO_DIR}/status_bar_preview.py" ]]; then
    printf '%s' "$REPO_DIR"
    return 0
  fi
  local candidate
  for candidate in \
      "${PROJECTS_DIR:-}/claude_code_status_bar" \
      "$HOME/projects/claude_code_status_bar"; do
    [[ -n "$candidate" && -f "$candidate/status_bar_preview.py" ]] || continue
    printf '%s' "$candidate"
    return 0
  done
  return 1
}

# Print the dimmed preview line used by both menu render hooks.
status_bar_print_preview_line() {
  local preview="$1"
  [[ -n "$preview" ]] || return 0
  printf '  \033[2mPreview: %s\033[0m\n' "$preview"
}

# Build a preview string for one highlighted submenu row.
status_bar_preview_for_submenu_row() {
  local repo="$1" sel="$2"
  local repo_dir target_home preview
  [[ "$repo" == "claude_code_status_bar" ]] || return 0
  repo_dir="$(status_bar_repo_dir)" || return 0
  target_home="${TARGET_HOME:-${HOME}}"
  local -a ids=()
  local id
  cm_comp_ids_for_repo "$repo" ids
  id="${ids[$sel]:-}"
  [[ -n "$id" ]] || return 0
  preview="$(python3 "$repo_dir/status_bar_preview.py" component "$id" "$target_home" 2>/dev/null || true)"
  status_bar_print_preview_line "$preview"
}

# Build a combined preview when the aggregate menu highlights this repository.
status_bar_preview_for_aggregate_repo() {
  local repo="$1"
  local repo_dir target_home preview
  [[ "$repo" == "claude_code_status_bar" ]] || return 0
  repo_dir="$(status_bar_repo_dir)" || return 0
  target_home="${TARGET_HOME:-${HOME}}"
  preview="$(python3 "$repo_dir/status_bar_preview.py" aggregate "$target_home" 2>/dev/null || true)"
  status_bar_print_preview_line "$preview"
}

# status_bar_register_menu_preview_hooks - monkey-patch shared menu renderers once.
status_bar_register_menu_preview_hooks() {
  [[ "$STATUS_BAR_MENU_HOOKS_REGISTERED" == "1" ]] && return 0
  status_bar_repo_dir >/dev/null || return 0
  STATUS_BAR_MENU_HOOKS_REGISTERED=1

  if declare -F cm_render_submenu >/dev/null 2>&1 \
      && [[ -z "${_SB_CM_RENDER_SUBMENU_ORIG:-}" ]]; then
    eval "$(declare -f cm_render_submenu | sed '1s/^cm_render_submenu/_SB_CM_RENDER_SUBMENU_ORIG/')"
    cm_render_submenu() {
      _SB_CM_RENDER_SUBMENU_ORIG "$@"
      status_bar_preview_for_submenu_row "$1" "$2"
    }
  fi

  if declare -F cm_render_aggregate >/dev/null 2>&1 \
      && [[ -z "${_SB_CM_RENDER_AGGREGATE_ORIG:-}" ]]; then
    eval "$(declare -f cm_render_aggregate | sed '1s/^cm_render_aggregate/_SB_CM_RENDER_AGGREGATE_ORIG/')"
    cm_render_aggregate() {
      _SB_CM_RENDER_AGGREGATE_ORIG "$@"
      local repo="${CM_REPOS[$1]:-}"
      [[ -n "$repo" ]] && status_bar_preview_for_aggregate_repo "$repo"
    }
  fi
}