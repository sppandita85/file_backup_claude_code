#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
VENV_PYTHON="$PROJECT_DIR/.venv/bin/python"

if [ ! -f "$VENV_PYTHON" ]; then
  echo "ERROR: Virtual environment not found. Run: bash scripts/install.sh"
  exit 1
fi

echo "Starting Microsoft OneDrive authentication..."
echo "You will be shown a URL and a code to enter in your browser."
echo ""

cd "$PROJECT_DIR"
"$VENV_PYTHON" -m mover.auth
