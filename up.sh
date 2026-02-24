#!/bin/bash
# Pahang Hotel Intelligence - Unified Startup & Watchdog
# Use: ./up.sh (automatic check & start) or ./up.sh --force (reset everything)

# Configuration
PORT=8050
LOG_DIR="logs"
DASHBOARD_LOG="$LOG_DIR/dashboard.log"
SSH_TUNNEL_LOG="$LOG_DIR/tunnel.log"
DASH_TUNNEL_LOG="$LOG_DIR/dashboard_tunnel.log"
BOOT_LOCK="/tmp/hotel_booting.lock"
REFRESH_LOCK="/tmp/hotel_refresh.lock"

# 0. Environment Setup
cd "$(dirname "$0")" || exit
mkdir -p "$LOG_DIR"

# 1. Check for Force Flag
FORCE=0
if [[ "$*" == *"--force"* ]]; then FORCE=1; fi

# 2. Watchdog Logic (Skip if everything is already UP and NO force flag)
DASH_UP=$(pgrep -f "dashboard.py")
CF_COUNT=$(pgrep -f "cloudflared" | wc -l)

if [ $FORCE -eq 0 ] && [ -n "$DASH_UP" ] && [ "$CF_COUNT" -ge 2 ]; then
    # If run manually in a terminal, provide feedback
    if [ -t 1 ]; then
        echo "✅ Services are already healthy and running in the background."
        echo "💡 Use 'bash up.sh --force' to reset and generate new URLs."
    fi
    exit 0
fi

# 3. Prevent race conditions (Allow --force to bypass refresh lock)
if [ -f "$BOOT_LOCK" ]; then
    echo "⏳ System is already booting. Waiting..."
    exit 0
fi

if [ $FORCE -eq 0 ] && [ -f "$REFRESH_LOCK" ]; then
    echo "⏳ System is currently refreshing data. Watchdog suspended."
    exit 0
fi

# 4. Start Sequence
echo $$ > "$BOOT_LOCK"
trap "rm -f $BOOT_LOCK" EXIT

echo "🚀 [$(date)] Starting/Recovering Hotel Intelligence Services..."
if [ $FORCE -eq 1 ]; then echo "🧹 Force reset requested. Cleaning up old processes..."; fi

# Cleanup
pkill -f "dashboard.py"
pkill -f "cloudflared"
sleep 2

# Start Dashboard
echo "📊 Launching Dashboard on port $PORT..."
nohup ./venv/bin/python3 dashboard.py > "$DASHBOARD_LOG" 2>&1 &

# Start SSH Tunnel
echo "🔒 Starting SSH Tunnel..."
nohup ./bin/cloudflared tunnel --url ssh://localhost:22 > "$SSH_TUNNEL_LOG" 2>&1 &

# Start Dashboard Tunnel
echo "🌐 Starting Dashboard Tunnel..."
nohup ./bin/cloudflared tunnel --url http://localhost:$PORT > "$DASH_TUNNEL_LOG" 2>&1 &

echo "⏳ Initializing tunnels (15s)..."
sleep 15

# 5. Result Reporting
echo -e "\n=============================================="
echo -e "✅ SERVICES ARE UP AND RUNNING"
echo -e "=============================================="

DASH_URL=$(grep -oE "https://[a-zA-Z0-9-]+\.trycloudflare\.com" "$DASH_TUNNEL_LOG" | head -n 1)
if [ -n "$DASH_URL" ]; then
    echo -e "🔗 DASHBOARD: $DASH_URL"
else
    echo -e "❌ Dashboard URL capture failed. Check $DASH_TUNNEL_LOG"
fi

SSH_URL=$(grep -oE "https://[a-zA-Z0-9-]+\.trycloudflare\.com" "$SSH_TUNNEL_LOG" | head -n 1)
if [ -n "$SSH_URL" ]; then
    SSH_HOST=$(echo "$SSH_URL" | sed 's|https://||')
    echo -e "� SSH HOST: $SSH_HOST"
fi
echo -e "=============================================="
