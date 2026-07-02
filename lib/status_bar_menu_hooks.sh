#!/usr/bin/env bash
# status_bar_menu_hooks.sh - shared preview hooks for component menus.
#
# Registers wrappers around cm_render_submenu and cm_render_aggregate so the
# claude_code_status_bar repository shows a simulated status-bar preview above
# the help/footer line (help remains the absolute bottom line, matching
# agent_field_configurator.py). Safe to call from the standalone installer or
# the master aggregate menu.

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

# Return preview text (no prefix) for one highlighted submenu component row.
status_bar_preview_text_for_submenu_row() {
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
  python3 "$repo_dir/status_bar_preview.py" component "$id" "$target_home" 2>/dev/null || true
}

# Return combined preview text for the aggregate-menu repo highlight.
status_bar_preview_text_for_aggregate_repo() {
  local repo="$1"
  local repo_dir target_home
  [[ "$repo" == "claude_code_status_bar" ]] || return 0
  repo_dir="$(status_bar_repo_dir)" || return 0
  target_home="${TARGET_HOME:-${HOME}}"
  python3 "$repo_dir/status_bar_preview.py" aggregate "$target_home" 2>/dev/null || true
}

# Print preview then help, keeping help as the last screen line.
status_bar_render_aggregate_with_preview() {
  local sel="$1" repo preview out help_line
  repo="${CM_REPOS[$sel]:-}"
  out="$(_SB_CM_RENDER_AGGREGATE_ORIG "$sel")"
  preview="$(status_bar_preview_text_for_aggregate_repo "$repo")"
  if [[ -z "$preview" ]]; then
    printf '%s' "$out"
    return 0
  fi
  help_line="$(printf '%s' "$out" | awk 'NF { line = $0 } END { print line }')"
  printf '%s' "$out" | awk -v help="$help_line" -v preview="$preview" '
    NF && $0 != help { print }
    END {
      if (help != "") {
        printf "  \033[2mPreview: %s\033[0m\n", preview
        print help
      }
    }
  '
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
      local repo="$1" sel="$2" title="$3" footer="$4" preview
      if [[ "$repo" == "claude_code_status_bar" ]]; then
        preview="$(status_bar_preview_text_for_submenu_row "$repo" "$sel")"
        if [[ -n "$preview" ]]; then
          footer=$'Preview: '"$preview"$'\n'"$footer"
        fi
      fi
      _SB_CM_RENDER_SUBMENU_ORIG "$repo" "$sel" "$title" "$footer"
    }
  fi

  if declare -F cm_render_aggregate >/dev/null 2>&1 \
      && [[ -z "${_SB_CM_RENDER_AGGREGATE_ORIG:-}" ]]; then
    eval "$(declare -f cm_render_aggregate | sed '1s/^cm_render_aggregate/_SB_CM_RENDER_AGGREGATE_ORIG/')"
    cm_render_aggregate() {
      status_bar_render_aggregate_with_preview "$1"
    }
  fi
}