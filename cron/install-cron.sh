#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
RUNNER="$REPO_ROOT/cron/run-local.sh"

# Default schedule: every day at 12:00 PM ET
SCHEDULE="${1:-0 12 * * *}"
CRON_LINE="$SCHEDULE $RUNNER"

TMP_FILE="$(mktemp)"
crontab -l 2>/dev/null > "$TMP_FILE" || true

# Remove existing entry for this runner
grep -v "$RUNNER" "$TMP_FILE" > "${TMP_FILE}.new" || true
mv "${TMP_FILE}.new" "$TMP_FILE"

echo "$CRON_LINE" >> "$TMP_FILE"
crontab "$TMP_FILE"
rm -f "$TMP_FILE"

echo "✅ Installed cron entry:"
echo "$CRON_LINE"
echo
echo "Current crontab:"
crontab -l
