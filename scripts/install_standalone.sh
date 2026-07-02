#!/usr/bin/env bash
# install_standalone.sh - Component-based installer for the Claude Code status bar.
#
# Resolves the shared setup component framework (from a sibling
# linux_installation_scripts_functions checkout, or by download), loads the
# shared installer helpers, sources the status-bar install steps, and delegates
# component execution to the common component runtime. This gives the repository
# the standard contract every family installer exposes:
#
#   bash install.sh                 # interactive submenu on a TTY, else defaults
#   bash install.sh --default       # install every default-on component
#   bash install.sh --all           # install every component
#   bash install.sh --select a,b,c  # install exactly these component ids
#   bash install.sh --list-components  # print "id<TAB>label<TAB>default"
#
# Environment overrides:
#   TARGET_USER  - user to install for (defaults to $SUDO_USER or $USER)

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET_USER="${TARGET_USER:-${SUDO_USER:-$USER}}"
TARGET_UID="$(id -u "$TARGET_USER")"
# TARGET_HOME defaults to the user's real home, but may be overridden (e.g. for
# clean-home install tests) without changing ownership semantics.
TARGET_HOME="${TARGET_HOME:-$(getent passwd "$TARGET_USER" | cut -d: -f6)}"
RUNTIME_DIR="/run/user/${TARGET_UID}"
USER_BUS="unix:path=${RUNTIME_DIR}/bus"
DISPLAY_VAL="${DISPLAY:-:0}"
export REPO_DIR TARGET_USER TARGET_UID TARGET_HOME RUNTIME_DIR USER_BUS DISPLAY_VAL

# log - repo-level diagnostic hook used by shared helpers before their logger
# loads. Args: $1 level, $2 message.
log() { printf '[%s] %s\n' "$1" "$2" >&2; }

# Resolve and activate the shared component framework, then load the helpers.
for __isc_d in "${ISC_FUNCTIONS_DIR:-}" \
               "$REPO_DIR/../linux_installation_scripts_functions" \
               "$HOME/projects/linux_installation_scripts_functions"; do
  [ -n "$__isc_d" ] && [ -f "$__isc_d/component_loader.sh" ] && { source "$__isc_d/component_loader.sh"; break; }
done
declare -F isc_load_helpers >/dev/null 2>&1 || \
  source <(curl -fsSL "https://raw.githubusercontent.com/mikaeltorni/linux_installation_scripts_functions/${ISC_FUNCTIONS_REF:-master}/component_loader.sh")
isc_load_helpers

# Mirror msg() to a clearly prefixed line for this repository.
msg() { printf '\n[claude_code_status_bar] %s\n' "$*"; }

# shellcheck source=/dev/null
source "$REPO_DIR/lib/status_bar_install_lib.sh"

isc_activate_components
source "$REPO_DIR/installer/components.sh"
status_bar_wrap_component_menu_preview

# main - run the selected status-bar installer components.
main() {
  msg "Installing agent TUI status bars for $TARGET_USER"
  component_main "$@"
  msg "Status bar setup complete."
}

case "${1:-}" in
  --list-components|--list-configurable-components|--list-component-config-values|--configure-component|--configure-component=*|--detect|--help|-h) component_main "$@"; exit $? ;;
esac

main "$@"
