#!/usr/bin/env bash
# set -euo pipefail

# Resolve repo root from this script location
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SRC_DIR="$REPO_ROOT/src"
LOG_DIR="$REPO_ROOT/logs"
LOCK_DIR="$REPO_ROOT/.run-lock"
LOCK_PID_FILE="$LOCK_DIR/pid"
LOCK_TS_FILE="$LOCK_DIR/started_at_epoch"
STALE_LOCK_SECONDS="${STALE_LOCK_SECONDS:-10800}"  # 3 hours default

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

# Prevent overlapping runs with stale-lock auto-recovery
acquire_lock() {
  if mkdir "$LOCK_DIR" 2>/dev/null; then
    echo "$$" > "$LOCK_PID_FILE"
    date +%s > "$LOCK_TS_FILE"
    return 0
  fi

  local now pid start age
  now="$(date +%s)"
  pid="$(cat "$LOCK_PID_FILE" 2>/dev/null || true)"
  start="$(cat "$LOCK_TS_FILE" 2>/dev/null || true)"
  age=0
  if [[ -n "$start" && "$start" =~ ^[0-9]+$ ]]; then
    age=$((now - start))
  fi

  # If pid is missing/dead OR lock age exceeds threshold, clear stale lock.
  if [[ -z "$pid" ]] || ! ps -p "$pid" >/dev/null 2>&1 || (( age > STALE_LOCK_SECONDS )); then
    rm -rf "$LOCK_DIR" >/dev/null 2>&1 || true
    if mkdir "$LOCK_DIR" 2>/dev/null; then
      echo "$$" > "$LOCK_PID_FILE"
      date +%s > "$LOCK_TS_FILE"
      echo "[$(date '+%Y-%m-%d %H:%M:%S')] Cleared stale lock (old_pid=${pid:-none}, age_seconds=$age)." >> "$LOG_DIR/cron-runner.log"
      return 0
    fi
  fi

  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Another run is already in progress (pid=${pid:-unknown}, age_seconds=$age). Exiting." >> "$LOG_DIR/cron-runner.log"
  return 1
}

if ! acquire_lock; then
  exit 0
fi
trap 'rm -rf "$LOCK_DIR" >/dev/null 2>&1 || true' EXIT

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
FORCE_LOCAL_MARKDOWN_REFRESH="${FORCE_LOCAL_MARKDOWN_REFRESH:-true}"
RUN_LOG="$LOG_DIR/dutch-$(date '+%Y-%m-%d').log"

if [[ -z "$PYTHON_BIN" ]]; then
  if [[ -x "$REPO_ROOT/.venv/bin/python" ]]; then
    PYTHON_BIN="$REPO_ROOT/.venv/bin/python"
  else
    PYTHON_BIN="$(command -v python3)"
  fi
fi
## BASEBALL LLM #####################################
MODEL_ENTRY="$SRC_DIR/${MODEL}.py"
if [[ ! -f "$MODEL_ENTRY" ]]; then
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Unknown MODEL='$MODEL'. Expected one of: ashburn, bowa, carlton, dutch, ennis." >> "$LOG_DIR/cron-runner.log"
  exit 1
fi

TIMESTAMP="$(date '+%Y-%m-%d %H:%M:%S')"


echo "[$TIMESTAMP] Starting model '$MODEL' with $PYTHON_BIN" >> "$RUN_LOG"
cd "$SRC_DIR"
# Local runs never push directly; OpenClaw polish/publish job owns final publish.
export AUTO_PUBLISH_SITE=false
export FORCE_LOCAL_MARKDOWN_REFRESH="$FORCE_LOCAL_MARKDOWN_REFRESH"

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
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Completed successfully" >> "$RUN_LOG"

# Refresh older date pages that still show PENDING results (markdown-driven where available).
"$PYTHON_BIN" "$SRC_DIR/scripts/refresh_pending_dates.py" >> "$RUN_LOG" 2>&1 \
  || echo "[$(date '+%Y-%m-%d %H:%M:%S')] Pending-date markdown refresh failed (continuing)" >> "$RUN_LOG"

# Directly resolve remaining pending statuses in historical HTML pages and refresh dashboard counts.
"$PYTHON_BIN" "$SRC_DIR/scripts/update_pending_results_html.py" >> "$RUN_LOG" 2>&1 \
  || echo "[$(date '+%Y-%m-%d %H:%M:%S')] Pending-result HTML resolver failed (continuing)" >> "$RUN_LOG"

# 7AM ET backfill: explicitly republish yesterday to finalize outcomes + dashboard row.
RUN_HOUR_ET="$(TZ=America/New_York date +%H)"
if [[ "$RUN_HOUR_ET" == "07" ]]; then
  YDAY_ET="$(TZ=America/New_York date -v-1d +%F)"
  YDAY_PICK="$SRC_DIR/picks/${YDAY_ET}-pick.md"
  if [[ -f "$YDAY_PICK" ]]; then
    "$PYTHON_BIN" - <<PY >> "$RUN_LOG" 2>&1 || echo "[$(date '+%Y-%m-%d %H:%M:%S')] 7AM yesterday backfill failed (continuing)" >> "$RUN_LOG"
import sys
sys.path.append("$SRC_DIR")
from connector.pick_site_publish import publish_daily_site
publish_daily_site("$YDAY_PICK", "$REPO_ROOT/../sportzballz.io")
PY
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] 7AM ET backfill complete for ${YDAY_ET}" >> "$RUN_LOG"
  else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] 7AM ET backfill skipped; missing ${YDAY_PICK}" >> "$RUN_LOG"
  fi
fi

# Ensure homepage latest tabs stay on *today* after any historical backfill refreshes.
TODAY_ET="$(TZ=America/New_York date +%F)"
TODAY_PICK="$SRC_DIR/picks/${TODAY_ET}-pick.md"
if [[ -f "$TODAY_PICK" ]]; then
  "$PYTHON_BIN" - <<PY >> "$RUN_LOG" 2>&1 || echo "[$(date '+%Y-%m-%d %H:%M:%S')] Latest-index republish failed (continuing)" >> "$RUN_LOG"
import sys
sys.path.append("$SRC_DIR")
from connector.pick_site_publish import publish_daily_site
publish_daily_site("$TODAY_PICK", "$REPO_ROOT/../sportzballz.io")
PY
fi

# POLISH ############################
if [[ "$COMMENTARY_POLISH_JOB" =~ ^(1|true|yes|on)$ ]]; then
  if [[ -z "$BASEBALL_POLISH_CRON_ID" ]]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Commentary polish cron id missing (BASEBALL_POLISH_CRON_ID). Skipping polish trigger." >> "$RUN_LOG"
  else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Triggering OpenClaw polish cron job: $BASEBALL_POLISH_CRON_ID" >> "$RUN_LOG"
    openclaw cron run "$BASEBALL_POLISH_CRON_ID" --expect-final >> "$RUN_LOG" 2>&1 
    # while true; do
    #   lastRunTime=$(jq -r '.jobs[]| select(.id == "5a28aa6c-8486-469c-93a2-e7628e4138a6")| .state | .lastRunAtMs' /Users/asmith/.openclaw/cron/jobs.json)
    #   currentTime=$(jq -n 'now * 1000 | floor')
    #   if (( lastRunTime >= currentTime - 60000 )); then
    #     echo "Polishing Complete!"
    #     break;
    #   else 
    #     echo "$currentTime current time Polishing..."
    #     echo "$lastRunTime last run tume Polishing..."
    #     sleep 5
    #   fi
    # done
    sleep 180
  fi
fi

# PUBLISH ############################
echo "AGS AGS AGS " >> "$RUN_LOG" 2>&1 \
  # Commit + push site updates from run-local (single owner for publish action).
SITE_REPO="$REPO_ROOT/../sportzballz.io"
TODAY_ET="$(TZ=America/New_York date +%F)"
cd "$SITE_REPO"
# Stage all published site artifacts explicitly so polished pages are never skipped.
git add *.html *.xml robots.txt apple-touch-icon.png data >> "$RUN_LOG" 2>&1 || true
if ! git diff --cached --quiet; then
  git commit -m "Publish daily picks + OpenClaw publish $TODAY_ET" >> "$RUN_LOG" 2>&1 || true
  git push origin main >> "$RUN_LOG" 2>&1
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Site commit/push complete for $TODAY_ET" >> "$RUN_LOG"
else
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] No site changes to commit for $TODAY_ET" >> "$RUN_LOG"
fi
