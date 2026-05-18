#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
VENV_PYTHON="$PROJECT_DIR/.venv/bin/python"

if [ ! -f "$VENV_PYTHON" ]; then
  echo "ERROR: Virtual environment not found. Run: bash scripts/install.sh"
  exit 1
fi

PORT=$("$VENV_PYTHON" -c "
import json
with open('$PROJECT_DIR/config.json') as f:
    c = json.load(f)
print(c.get('dashboard_port', 7474))
" 2>/dev/null || echo "7474")

echo "Starting dashboard at http://localhost:$PORT"
echo "Press Ctrl+C to stop."
echo ""

cd "$PROJECT_DIR"
"$VENV_PYTHON" -m dashboard.app
