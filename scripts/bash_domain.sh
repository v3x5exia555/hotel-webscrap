#!/bin/bash
# Restart Hotel Dashboard & Bring scapper.abai.my Online
# Usage: bash bash_domain.sh

set -e

PROJECT_DIR="/root/.openclaw/workspace/hotel-webscrap-v2"
DOMAIN="scapper.abai.my"
LOCAL_PORT=8050

echo "🚀 Starting domain restoration for $DOMAIN..."
cd "$PROJECT_DIR"

# Step 1: Kill old processes
echo "🧹 Cleaning up old processes..."
pkill -f "dashboard.py" || true
pkill -f "cloudflared" || true
sleep 2

# Step 2: Start dashboard
echo "📊 Starting dashboard on port $LOCAL_PORT..."
nohup ./venv/bin/python3 dashboard.py > logs/dashboard.log 2>&1 &
sleep 3

# Step 3: Verify dashboard is responding locally
echo "⏳ Waiting for dashboard to respond..."
MAX_ATTEMPTS=10
ATTEMPT=0
while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
    if curl -s -I http://localhost:$LOCAL_PORT | grep -q "200\|302"; then
        echo "✅ Dashboard is responding on localhost:$LOCAL_PORT"
        break
    fi
    ATTEMPT=$((ATTEMPT + 1))
    echo "   Attempt $ATTEMPT/$MAX_ATTEMPTS... waiting"
    sleep 1
done

# Step 4: Start SSH Tunnel
echo "🔒 Starting SSH Tunnel..."
nohup ./bin/cloudflared tunnel --url ssh://localhost:22 > logs/tunnel.log 2>&1 &

# Step 5: Start Dashboard Tunnel
echo "🌐 Starting Dashboard Tunnel..."
nohup ./bin/cloudflared tunnel --url http://localhost:$LOCAL_PORT > logs/dashboard_tunnel.log 2>&1 &

sleep 5

# Step 6: Extract and display tunnel URL
DASH_URL=$(grep -oE "https://[a-zA-Z0-9-]+\.trycloudflare\.com" logs/dashboard_tunnel.log | head -n 1 || echo "URL not found")

# Step 7: Test domain accessibility via nginx proxy
echo "🌐 Testing $DOMAIN accessibility..."
sleep 2
if curl -s -I https://$DOMAIN | grep -q "200"; then
    echo "✅ Domain $DOMAIN is ONLINE"
else
    echo "⚠️  Domain returned error. Check nginx logs: tail -20 /var/log/nginx/error.log"
fi

echo ""
echo "=============================================="
echo "✅ SERVICES RESTORED"
echo "=============================================="
echo "🔗 Local Dashboard:    http://localhost:$LOCAL_PORT"
echo "🔗 Tunnel URL:         $DASH_URL"
echo "🔗 Domain:             https://$DOMAIN"
echo "=============================================="
