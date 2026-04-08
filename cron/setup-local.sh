#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$REPO_ROOT"

if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi

source .venv/bin/activate
pip install --upgrade pip
pip install -r src/requirements.txt

echo "✅ Local environment ready"
echo "Next steps:"
echo "1) cp .env.local.example .env.local"
echo "2) Edit .env.local with real keys"
echo "3) Test run: ./cron/run-local.sh"
echo "4) Install cron entry using ./cron/install-cron.sh"
