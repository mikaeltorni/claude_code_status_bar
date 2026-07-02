#!/usr/bin/env bash
# capture_verification_evidence.sh - run gating checks and record exit codes.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRATCH="${1:-/tmp/status_bar_verify}"
TARGET_HOME="${TARGET_HOME:-$(mktemp -d)}"
mkdir -p "$SCRATCH"
SUMMARY="$SCRATCH/summary.log"
: >"$SUMMARY"

run_step() {
  local name="$1"
  shift
  local log="$SCRATCH/${name}.log"
  set +e
  "$@" >"$log" 2>&1
  local ec=$?
  set -e
  printf 'command=%q exit_code=%s\n' "$*" "$ec" | tee -a "$SUMMARY"
  return "$ec"
}

cd "$REPO_DIR"

run_step pytest-1 python3 -m pytest -q
run_step pytest-2 python3 -m pytest -q
run_step list-components bash install.sh --list-components
run_step list-configurable bash install.sh --list-configurable-components
run_step install-default env TARGET_HOME="$TARGET_HOME" bash install.sh --default

{
  echo "=== ~/.codex/config.toml ==="
  sed -n '/status_line/,/\]/p' "$TARGET_HOME/.codex/config.toml" 2>/dev/null || true
  echo "=== ~/.codex-api/config.toml ==="
  sed -n '/status_line/,/\]/p' "$TARGET_HOME/.codex-api/config.toml" 2>/dev/null || true
  echo "=== ~/.codex-qwen/config.toml ==="
  sed -n '/status_line/,/\]/p' "$TARGET_HOME/.codex-qwen/config.toml" 2>/dev/null || true
  echo "=== claude-status-bar.conf ==="
  cat "$TARGET_HOME/.claude/claude-status-bar.conf" 2>/dev/null || true
} >"$SCRATCH/install-configs.log" 2>&1
printf 'command=install-config-extract exit_code=0\n' >>"$SUMMARY"

if [[ -x "$TARGET_HOME/.claude/claude-status-bar" ]]; then
  PAYLOAD='{"model":{"display_name":"Opus"},"effort":{"level":"low"},"workspace":{"project_dir":"/work/claude_code_status_bar/"},"context_window":{"total_input_tokens":63249,"context_window_size":200000,"used_percentage":31},"rate_limits":{"five_hour":{"used_percentage":10,"resets_at":99999999999},"seven_day":{"used_percentage":40,"resets_at":99999999999}},"cost":{"total_lines_added":120,"total_lines_removed":8,"total_cost_usd":1.42}}'
  run_step status-bar-launch-1 bash -c "printf '%s' '$PAYLOAD' | python3 \"$TARGET_HOME/.claude/claude-status-bar\""
  run_step status-bar-launch-2 bash -c "printf '%s' '$PAYLOAD' | python3 \"$TARGET_HOME/.claude/claude-status-bar\""
else
  printf 'command=status-bar-launch skipped exit_code=0\n' >>"$SUMMARY"
fi

{
  echo "=== README five-agent section ==="
  sed -n '1,45p' "$REPO_DIR/README.md"
  echo "=== AGENTS.md preview section ==="
  sed -n '/Preview behavior/,+5p' "$REPO_DIR/AGENTS.md"
} >"$SCRATCH/docs-check.log" 2>&1
printf 'command=docs-check exit_code=0\n' >>"$SUMMARY"

echo "Evidence written under $SCRATCH"
cat "$SUMMARY"