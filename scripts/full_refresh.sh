#!/bin/bash

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
VENV_PYTHON="$PROJECT_ROOT/venv/bin/python3"
LOG_FILE="$PROJECT_ROOT/logs/full_refresh.log"
LOCK_FILE="/tmp/hotel_refresh.lock"
DASH_TUNNEL_LOG="$PROJECT_ROOT/logs/dashboard_tunnel.log"

# Move to the project root
cd "$PROJECT_ROOT" || exit

# 1. Check for active lock
if [ -f "$LOCK_FILE" ]; then
    PID=$(cat "$LOCK_FILE")
    if ps -p "$PID" > /dev/null; then
        echo "⚠️  Another refresh is already running (PID: $PID). Skipping."
        exit 1
    fi
fi

# Create lock
echo $$ > "$LOCK_FILE"
trap "rm -f $LOCK_FILE" EXIT

# Redirect all output to log file
exec > >(tee -a "$LOG_FILE") 2>&1

echo "===================================================="
echo "🚀 [$(date)] FULL END-TO-END REFRESH STARTED"
echo "===================================================="

# Step 3: Run Full Market Scrape (Daily)
echo "🔍 Step 3/5: Running daily market scrape (1 day ahead)..."
$VENV_PYTHON main.py --mode daily --days 7 --workers 3

# Step 4: Run Revenue & Pickup Analysis
echo "📊 Step 4/5: Analyzing pickups and revenue trends..."
export PYTHONPATH=$PYTHONPATH:.
$VENV_PYTHON scripts/analyze_pickup.py

# Step 5: Restart Unified Services
echo "🗑️ Cleaning up old processes before restart..."
# pkill -f "dashboard.py"
# pkill -f "cloudflared"
pkill -f "hotel_monitor.py"
sleep 5

# echo "🌐 Step 5/5: Restarting Dashboard and Tunnels..."
# bash up.sh --force

# # Give tunnels a moment to initialize
# sleep 20

# # Step 6: Extract New URL
# DASH_URL=$(grep -oE "https://[a-zA-Z0-9-]+\.trycloudflare\.com" "$DASH_TUNNEL_LOG" | head -n 1)

# if [ -n "$DASH_URL" ]; then
#     MSG="✅ Hotel Dashboard Refresh Complete!
# 📍 URL: $DASH_URL
# 📊 Status: Scraped & Analyzed
# ⏰ Next Refresh: In 30 mins"
    
#     echo "📱 Sending Telegram notification..."
#     $VENV_PYTHON scripts/send_telegram.py "$MSG"
# else
#     echo "❌ Failed to capture Dashboard URL for notification."
#     $VENV_PYTHON scripts/send_telegram.py "⚠️ Hotel Refresh finished but failed to capture a new Cloudflare URL. Check logs/full_refresh.log"
# fi

# # Step 7: Restart Real-Time Monitor in background
# echo "🚀 Starting Background Monitor..."
# nohup $VENV_PYTHON scripts/hotel_monitor.py --interval 30 > logs/monitor_bg.log 2>&1 &

# echo "===================================================="
# echo "✅ [$(date)] FULL REFRESH COMPLETED"
# echo "===================================================="
