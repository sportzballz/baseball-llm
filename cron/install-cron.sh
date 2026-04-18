#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
RUNNER="$REPO_ROOT/cron/run-local.sh"

# Default schedules: every day at 3:00 AM and 3:30 AM ET
if [[ "$#" -gt 0 ]]; then
  SCHEDULES=("$@")
else
  SCHEDULES=("0 3 * * *" "30 3 * * *")
fi

TMP_FILE="$(mktemp)"
crontab -l 2>/dev/null > "$TMP_FILE" || true

# Remove existing entry for this runner
grep -v "$RUNNER" "$TMP_FILE" > "${TMP_FILE}.new" || true
mv "${TMP_FILE}.new" "$TMP_FILE"

for SCHEDULE in "${SCHEDULES[@]}"; do
  echo "$SCHEDULE $RUNNER" >> "$TMP_FILE"
done

crontab "$TMP_FILE"
rm -f "$TMP_FILE"

echo "✅ Installed cron entries:"
for SCHEDULE in "${SCHEDULES[@]}"; do
  echo "$SCHEDULE $RUNNER"
done
echo
echo "Current crontab:"
crontab -l
