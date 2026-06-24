#!/usr/bin/env bash
# install.sh - Claude Code status bar installer entry point.
#
# Thin delegator to the component-based installer in
# scripts/install_standalone.sh, matching the family installer layout. All
# arguments (e.g. --default, --all, --select id,..., --list-components) are
# forwarded unchanged.
#
# Usage:
#   bash install.sh                 # interactive submenu on a TTY, else defaults
#   sudo bash install.sh            # install for $SUDO_USER (clean-install chain)
#   bash install.sh --list-components
#
# Environment overrides:
#   TARGET_USER  - user to install for (defaults to $SUDO_USER or $USER)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ ! -f "$SCRIPT_DIR/scripts/install_standalone.sh" ]]; then
  echo "Error: scripts/install_standalone.sh not found in claude_code_status_bar" >&2
  exit 1
fi

exec bash "$SCRIPT_DIR/scripts/install_standalone.sh" "$@"
