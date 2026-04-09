#!/usr/bin/env bash
set -euo pipefail

# Resolve repo root from this script location
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SRC_DIR="$REPO_ROOT/src"
LOG_DIR="$REPO_ROOT/logs"
LOCK_DIR="$REPO_ROOT/.run-lock"

mkdir -p "$LOG_DIR"

# If both cron and LaunchAgent are configured, prefer LaunchAgent.
# We currently ignore cron-triggered invocations to avoid duplicate runs.
is_invoked_by_cron() {
  local p="$PPID"
  local i=0
  while [[ -n "$p" && "$p" != "1" && $i -lt 8 ]]; do
    local comm
    comm="$(ps -p "$p" -o comm= 2>/dev/null | xargs || true)"
    if [[ "$comm" == "cron" || "$comm" == "/usr/sbin/cron" ]]; then
      return 0
    fi
    p="$(ps -p "$p" -o ppid= 2>/dev/null | xargs || true)"
    i=$((i+1))
  done
  return 1
}

if is_invoked_by_cron; then
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Ignoring cron invocation; LaunchAgent is the active scheduler." >> "$LOG_DIR/cron-runner.log"
  exit 0
fi

# Prevent overlapping runs
if ! mkdir "$LOCK_DIR" 2>/dev/null; then
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Another run is already in progress. Exiting." >> "$LOG_DIR/cron-runner.log"
  exit 0
fi
trap 'rmdir "$LOCK_DIR" >/dev/null 2>&1 || true' EXIT

# Load local env if present (.env first, then .env.local override)
# set -a auto-exports sourced variables to subprocess environment.
set -a
if [[ -f "$REPO_ROOT/.env" ]]; then
  # shellcheck disable=SC1090
  source "$REPO_ROOT/.env"
fi
if [[ -f "$REPO_ROOT/.env.local" ]]; then
  # shellcheck disable=SC1090
  source "$REPO_ROOT/.env.local"
fi
set +a

MODEL="${MODEL:-dutch}"
PYTHON_BIN="${PYTHON_BIN:-}"
COMMENTARY_POLISH_JOB="${COMMENTARY_POLISH_JOB:-true}"
BASEBALL_POLISH_CRON_ID="${BASEBALL_POLISH_CRON_ID:-5a28aa6c-8486-469c-93a2-e7628e4138a6}"
LOCAL_USE_LLM_FOR_INITIAL="${LOCAL_USE_LLM_FOR_INITIAL:-false}"
REFRESH_MATCHUP_METRICS="${REFRESH_MATCHUP_METRICS:-true}"

if [[ -z "$PYTHON_BIN" ]]; then
  if [[ -x "$REPO_ROOT/.venv/bin/python" ]]; then
    PYTHON_BIN="$REPO_ROOT/.venv/bin/python"
  else
    PYTHON_BIN="$(command -v python3)"
  fi
fi

MODEL_ENTRY="$SRC_DIR/${MODEL}.py"
if [[ ! -f "$MODEL_ENTRY" ]]; then
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Unknown MODEL='$MODEL'. Expected one of: ashburn, bowa, carlton, dutch, ennis." >> "$LOG_DIR/cron-runner.log"
  exit 1
fi

TIMESTAMP="$(date '+%Y-%m-%d %H:%M:%S')"
RUN_LOG="$LOG_DIR/${MODEL}-$(date '+%Y-%m-%d').log"

echo "[$TIMESTAMP] Starting model '$MODEL' with $PYTHON_BIN" >> "$RUN_LOG"
(
  cd "$SRC_DIR"
  # Local runs never push directly; OpenClaw polish/publish job owns final publish.
  export AUTO_PUBLISH_SITE=false

  if [[ "$REFRESH_MATCHUP_METRICS" =~ ^(1|true|yes|on)$ ]]; then
    "$PYTHON_BIN" "$SRC_DIR/scripts/build_matchup_metrics.py" >> "$RUN_LOG" 2>&1 \
      || echo "[$(date '+%Y-%m-%d %H:%M:%S')] Matchup metrics refresh failed (continuing)" >> "$RUN_LOG"
  fi
  if [[ ! "$LOCAL_USE_LLM_FOR_INITIAL" =~ ^(1|true|yes|on)$ ]]; then
    # Force fallback commentary for local generation pass.
    export OPENAI_API_KEY=""
    export OPENROUTER_API_KEY=""
  fi
  "$PYTHON_BIN" "$MODEL_ENTRY"
) >> "$RUN_LOG" 2>&1

EXIT_CODE=$?
if [[ $EXIT_CODE -eq 0 ]]; then
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Completed successfully" >> "$RUN_LOG"

  # Refresh older date pages that still show PENDING results (markdown-driven where available).
  "$PYTHON_BIN" "$SRC_DIR/scripts/refresh_pending_dates.py" >> "$RUN_LOG" 2>&1 \
    || echo "[$(date '+%Y-%m-%d %H:%M:%S')] Pending-date markdown refresh failed (continuing)" >> "$RUN_LOG"

  # Directly resolve remaining pending statuses in historical HTML pages and refresh dashboard counts.
  "$PYTHON_BIN" "$SRC_DIR/scripts/update_pending_results_html.py" >> "$RUN_LOG" 2>&1 \
    || echo "[$(date '+%Y-%m-%d %H:%M:%S')] Pending-result HTML resolver failed (continuing)" >> "$RUN_LOG"

  if [[ "$COMMENTARY_POLISH_JOB" =~ ^(1|true|yes|on)$ ]]; then
    if [[ -z "$BASEBALL_POLISH_CRON_ID" ]]; then
      echo "[$(date '+%Y-%m-%d %H:%M:%S')] Commentary polish cron id missing (BASEBALL_POLISH_CRON_ID). Skipping polish trigger." >> "$RUN_LOG"
    else
      echo "[$(date '+%Y-%m-%d %H:%M:%S')] Triggering OpenClaw polish cron job: $BASEBALL_POLISH_CRON_ID" >> "$RUN_LOG"
      openclaw cron run "$BASEBALL_POLISH_CRON_ID" --expect-final >> "$RUN_LOG" 2>&1 \
        || echo "[$(date '+%Y-%m-%d %H:%M:%S')] Commentary polish cron trigger failed" >> "$RUN_LOG"
    fi
  fi
else
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Failed with exit code $EXIT_CODE" >> "$RUN_LOG"
fi

exit $EXIT_CODE
