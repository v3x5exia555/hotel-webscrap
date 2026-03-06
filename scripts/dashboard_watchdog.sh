#!/bin/bash
# ---------------------------------------------------------------------------
# Pahang Hotel Intelligence - Dashboard Stability Watchdog
# ---------------------------------------------------------------------------

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
VENV_PYTHON="$PROJECT_ROOT/venv/bin/python3"
DASH_SCRIPT="$PROJECT_ROOT/dashboard.py"
WATCHDOG_LOG="$PROJECT_ROOT/logs/watchdog.log"
DASHBOARD_LOG="$PROJECT_ROOT/logs/dashboard.log"
PORT=8050
REFRESH_LOCK="/tmp/hotel_refresh.lock"

# Ensure logs directory exists
mkdir -p "$PROJECT_ROOT/logs"

# 1. Skip if data refresh is in progress
if [ -f "$REFRESH_LOCK" ]; then
    PID_REFRESH=$(cat "$REFRESH_LOCK")
    if ps -p "$PID_REFRESH" > /dev/null; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] ⏳ Data refresh in progress (PID: $PID_REFRESH). Watchdog suspended." >> "$WATCHDOG_LOG"
        exit 0
    fi
fi

# 2. Check if process is running
DASH_PID=$(pgrep -f "dashboard.py")

# 3. Check if HTTP port is responding
# We wait 2 seconds for a response. If it fails or returns non-200, we consider it unhealthy.
HTTP_CODE=$(curl -s -L -o /dev/null -w "%{http_code}" --connect-timeout 2 --max-time 5 http://localhost:$PORT || echo "000")

TIMESTAMP=$(date "+%Y-%m-%d %H:%M:%S")

# 4. Recovery Logic
if [ -z "$DASH_PID" ] || [ "$HTTP_CODE" != "200" ]; then
    echo "[$TIMESTAMP] 🛑 STABILITY ALERT: Dashboard found down or unhealthy." >> "$WATCHDOG_LOG"
    echo "    - Status: PID=[${DASH_PID:-DOWN}], HTTP=[$HTTP_CODE]" >> "$WATCHDOG_LOG"
    
    # Clean up old processes if they exist but are unresponsive
    if [ -n "$DASH_PID" ]; then
        echo "    - Action: Terminating unresponsive process $DASH_PID..." >> "$WATCHDOG_LOG"
        kill -9 $DASH_PID
        sleep 2
    fi
    
    # Start fresh
    echo "    - Action: Launching new dashboard instance..." >> "$WATCHDOG_LOG"
    cd "$PROJECT_ROOT" || exit
    
    # Start with nohup and redirect to dashboard log
    # We use 'exec' to ensure the process starts correctly
    nohup "$VENV_PYTHON" "$DASH_SCRIPT" >> "$DASHBOARD_LOG" 2>&1 &
    
    # Give it a moment to bind to the port
    sleep 5
    NEW_PID=$(pgrep -f "dashboard.py")
    echo "    - Result: Dashboard recovered at PID $NEW_PID" >> "$WATCHDOG_LOG"
    echo "------------------------------------------------------------" >> "$WATCHDOG_LOG"
else
    # Silent success - Dashboard is healthy
    exit 0
fi
