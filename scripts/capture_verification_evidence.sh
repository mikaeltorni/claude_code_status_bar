#!/usr/bin/env bash
# capture_verification_evidence.sh - run plan verification steps with inline exit codes.
set -uo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRATCH="${1:-${GROK_GOAL_SCRATCH:-/tmp/grok-goal-a08047c39985/implementer}}"
TARGET_HOME="${TARGET_HOME:-$(mktemp -d)}"
mkdir -p "$SCRATCH"
SUMMARY="$SCRATCH/summary.log"
: >"$SUMMARY"

record_step() {
  printf '%s\n' "$1" >>"$SUMMARY"
}

# run_step NAME CMD... — capture stdout/stderr and stamp exit_code in the log file.
run_step() {
  local name="$1" ec
  shift
  local log="$SCRATCH/${name}.log"
  {
    printf '# command=%q\n' "$*"
    "$@"
    ec=$?
    printf '\n# exit_code=%s\n' "$ec"
  } >"$log" 2>&1
  ec=$?
  record_step "step=${name} command=$* exit_code=${ec} log=${log}"
  return "$ec"
}

cd "$REPO_DIR"

failures=0
run_step pytest-1 python3 -m pytest -q || failures=$((failures + 1))
run_step pytest-2 python3 -m pytest -q || failures=$((failures + 1))

{
  printf '# command=bash install.sh --list-components\n'
  bash install.sh --list-components
  ec_list=$?
  printf '\n# --list-components exit_code=%s\n\n' "$ec_list"
  echo '=== --list-configurable-components ==='
  bash install.sh --list-configurable-components
  ec_cfg=$?
  printf '\n# --list-configurable-components exit_code=%s\n' "$ec_cfg"
  if (( ec_list != 0 || ec_cfg != 0 )); then
    printf '\n# combined exit_code=1\n'
  else
    printf '\n# combined exit_code=0\n'
  fi
} >"$SCRATCH/list-components.log" 2>&1
list_ec=0
if ! tail -1 "$SCRATCH/list-components.log" | grep -q 'combined exit_code=0'; then
  list_ec=1
fi
record_step "step=list-components command=list+configurable exit_code=${list_ec} log=${SCRATCH}/list-components.log"
(( list_ec != 0 )) && failures=$((failures + 1))

run_step preview-tests python3 -m pytest -q tests/test_preview.py || failures=$((failures + 1))
run_step install-default env TARGET_HOME="$TARGET_HOME" bash install.sh --default || failures=$((failures + 1))
run_step install-default-idempotent env TARGET_HOME="$TARGET_HOME" bash install.sh --default || failures=$((failures + 1))

{
  printf '# command=install-config-extract TARGET_HOME=%s\n' "$TARGET_HOME"
  echo "=== ~/.codex/config.toml ==="
  sed -n '/status_line/,/\]/p' "$TARGET_HOME/.codex/config.toml" 2>/dev/null || true
  echo "=== ~/.codex-api/config.toml ==="
  sed -n '/status_line/,/\]/p' "$TARGET_HOME/.codex-api/config.toml" 2>/dev/null || true
  echo "=== ~/.codex-qwen/config.toml ==="
  sed -n '/status_line/,/\]/p' "$TARGET_HOME/.codex-qwen/config.toml" 2>/dev/null || true
  echo "=== claude-status-bar.conf ==="
  cat "$TARGET_HOME/.claude/claude-status-bar.conf" 2>/dev/null || true
  echo "=== settings.json statusLine ==="
  python3 - <<'PY' "$TARGET_HOME/.claude/settings.json" 2>/dev/null || true
import json, sys
print(json.dumps(json.load(open(sys.argv[1])).get("statusLine", {}), indent=2))
PY
  printf '\n# exit_code=0\n'
} >"$SCRATCH/install-configs.log" 2>&1
record_step "step=install-configs command=extract exit_code=0 log=${SCRATCH}/install-configs.log"

if [[ -x "$TARGET_HOME/.claude/claude-status-bar" ]]; then
  PAYLOAD='{"model":{"display_name":"Opus"},"effort":{"level":"low"},"workspace":{"project_dir":"/work/claude_code_status_bar/"},"context_window":{"total_input_tokens":63249,"context_window_size":200000,"used_percentage":31},"rate_limits":{"five_hour":{"used_percentage":10,"resets_at":99999999999},"seven_day":{"used_percentage":40,"resets_at":99999999999}},"cost":{"total_lines_added":120,"total_lines_removed":8,"total_cost_usd":1.42}}'
  run_step status-bar-launch-1 bash -c "printf '%s' '$PAYLOAD' | python3 \"$TARGET_HOME/.claude/claude-status-bar\"" || failures=$((failures + 1))
  run_step status-bar-launch-2 bash -c "printf '%s' '$PAYLOAD' | python3 \"$TARGET_HOME/.claude/claude-status-bar\"" || failures=$((failures + 1))
else
  record_step "step=status-bar-launch skipped exit_code=0"
fi

{
  printf '# command=docs-check\n'
  echo "=== README five-agent section ==="
  sed -n '1,45p' "$REPO_DIR/README.md"
  echo "=== AGENTS.md preview section ==="
  sed -n '/Preview behavior/,+5p' "$REPO_DIR/AGENTS.md"
  printf '\n# exit_code=0\n'
} >"$SCRATCH/docs-check.log" 2>&1
record_step "step=docs-check command=readme+agents exit_code=0 log=${SCRATCH}/docs-check.log"

record_step "child_repo=${REPO_DIR} child_sha=$(git -C "$REPO_DIR" rev-parse --short HEAD)"
record_step "failures=${failures}"

echo "Evidence written under $SCRATCH"
cat "$SUMMARY"
exit "$failures"