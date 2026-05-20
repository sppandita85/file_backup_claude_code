#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
VENV_DIR="$PROJECT_DIR/.venv"
DATA_DIR="$HOME/.local/share/downloadsbackup"
LAUNCH_AGENTS_DIR="$HOME/Library/LaunchAgents"
PLIST_NAME="com.user.downloadsbackup.plist"

echo "=================================================="
echo "  Downloads → OneDrive Backup — Setup"
echo "=================================================="
echo ""

# Check Python 3.9+
if ! command -v python3 &>/dev/null; then
  echo "ERROR: python3 not found. Install from https://python.org or via Homebrew."
  exit 1
fi

PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
PYTHON_MAJOR=$(echo "$PYTHON_VERSION" | cut -d. -f1)
PYTHON_MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)
if [ "$PYTHON_MAJOR" -lt 3 ] || { [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 9 ]; }; then
  echo "ERROR: Python 3.9+ required (found $PYTHON_VERSION)"
  exit 1
fi
echo "Python $PYTHON_VERSION found."

# Create virtualenv
if [ ! -d "$VENV_DIR" ]; then
  echo "Creating virtualenv at $VENV_DIR..."
  python3 -m venv "$VENV_DIR"
fi

VENV_PYTHON="$VENV_DIR/bin/python"
VENV_PIP="$VENV_DIR/bin/pip"

echo "Installing dependencies..."
"$VENV_PIP" install --quiet --upgrade pip
"$VENV_PIP" install --quiet -r "$PROJECT_DIR/requirements.txt"

# Create data directory
mkdir -p "$DATA_DIR"
echo "Data directory: $DATA_DIR"

# Download Chart.js (vendored for offline use)
CHART_JS="$PROJECT_DIR/dashboard/static/chart.min.js"
if [ ! -s "$CHART_JS" ] || [ "$(wc -c < "$CHART_JS")" -lt 10000 ]; then
  echo "Downloading Chart.js..."
  curl -sL "https://cdn.jsdelivr.net/npm/chart.js@4.4.3/dist/chart.umd.min.js" \
    -o "$CHART_JS" 2>/dev/null || echo "  (Chart.js download skipped — CDN fallback will be used)"
fi

# Create config.json from defaults if not exists
if [ ! -f "$PROJECT_DIR/config.json" ]; then
  cp "$PROJECT_DIR/config.default.json" "$PROJECT_DIR/config.json"
  echo "Created config.json"
fi

# Initialize database
"$VENV_PYTHON" -m mover.db --init

# Read schedule from config.json
HOUR=$("$VENV_PYTHON" -c "
import json
with open('$PROJECT_DIR/config.json') as f:
    c = json.load(f)
print(c.get('schedule_hour', 2))
")
MINUTE=$("$VENV_PYTHON" -c "
import json
with open('$PROJECT_DIR/config.json') as f:
    c = json.load(f)
print(c.get('schedule_minute', 0))
")

# Create LaunchAgents directory if needed
mkdir -p "$LAUNCH_AGENTS_DIR"

# Fill plist template
PLIST_SRC="$PROJECT_DIR/launchd/$PLIST_NAME"
PLIST_DEST="$LAUNCH_AGENTS_DIR/$PLIST_NAME"

sed \
  -e "s|__VENV_PYTHON__|$VENV_PYTHON|g" \
  -e "s|__PROJECT_DIR__|$PROJECT_DIR|g" \
  -e "s|__HOUR__|$HOUR|g" \
  -e "s|__MINUTE__|$MINUTE|g" \
  -e "s|__LOG_DIR__|$DATA_DIR|g" \
  "$PLIST_SRC" > "$PLIST_DEST"

# Load launchd plist
launchctl unload "$PLIST_DEST" 2>/dev/null || true
launchctl load "$PLIST_DEST"

echo ""
echo "=================================================="
echo "  Installation Complete!"
echo "=================================================="
echo ""
echo "  Schedule:   Daily at ${HOUR}:$(printf '%02d' $MINUTE)"
echo "  Data dir:   $DATA_DIR"
echo ""
echo "  Next steps:"
echo "  1. Edit config.json and add your Azure client_id"
echo "     (see README.md for the 5-minute Azure app setup)"
echo "  2. Run: bash scripts/login.sh"
echo "     (one-time Microsoft account login)"
echo "  3. Test: bash scripts/run_dashboard.sh"
echo "     then: curl -X POST http://localhost:7474/api/run-now"
echo ""
echo "  Verify schedule:"
echo "    launchctl list | grep downloadsbackup"
echo ""
