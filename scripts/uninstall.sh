#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
PLIST="$HOME/Library/LaunchAgents/com.user.downloadsbackup.plist"
DATA_DIR="$HOME/.local/share/downloadsbackup"

echo "=================================================="
echo "  Downloads Backup — Uninstall"
echo "=================================================="
echo ""

# Unload and remove plist
if [ -f "$PLIST" ]; then
  launchctl unload "$PLIST" 2>/dev/null || true
  rm "$PLIST"
  echo "Removed launchd plist."
else
  echo "No launchd plist found (already removed)."
fi

# Data directory
if [ -d "$DATA_DIR" ]; then
  read -r -p "Remove data directory ($DATA_DIR)? This deletes all history. [y/N] " ans
  if [[ "$ans" =~ ^[Yy]$ ]]; then
    rm -rf "$DATA_DIR"
    echo "Removed $DATA_DIR"
  else
    echo "Kept $DATA_DIR"
  fi
fi

# Virtualenv
if [ -d "$PROJECT_DIR/.venv" ]; then
  read -r -p "Remove virtualenv ($PROJECT_DIR/.venv)? [y/N] " ans
  if [[ "$ans" =~ ^[Yy]$ ]]; then
    rm -rf "$PROJECT_DIR/.venv"
    echo "Removed .venv"
  else
    echo "Kept .venv"
  fi
fi

echo ""
echo "Uninstall complete. config.json is retained in $PROJECT_DIR."
