#!/bin/bash
# ---------------------------------------------------------------------------
# scripts/remote_update.sh
# ---------------------------------------------------------------------------
# Purpose: Run this on your SSH server after pushing changes from local.
# It pulls the latest code from GitHub and restarts the dashboard.

# Move to project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT" || exit 1

echo "🔍 Detecting current environment..."
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
echo "📍 Current Branch: $CURRENT_BRANCH"

echo "📥 Syncing with GitHub..."
# Fetch all branches
git fetch origin

# Reset to the remote version of the current branch 
# (This ensures the code perfectly matches what you just pushed from local)
git reset --hard origin/"$CURRENT_BRANCH"

echo "🧹 Cleaning up old dashboard processes..."
# Kill existing dashboard.py instances
pkill -f "dashboard.py"

echo "🚀 Restarting Dashboard..."
# Trigger the watchdog immediately to start the process with correct logs
# This ensures it starts in the background via nohup
bash "$PROJECT_ROOT/scripts/dashboard_watchdog.sh"

echo "------------------------------------------------------------"
echo "✅ UPDATE SUCCESSFUL"
echo "📍 Branch: $CURRENT_BRANCH"
echo "📊 Dashboard is restarting. Logs: logs/dashboard.log"
echo "🛡️ Watchdog is monitoring stability."
echo "------------------------------------------------------------"
