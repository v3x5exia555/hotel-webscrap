#!/usr/bin/env bash
# revised: local startup script for Pahang Hotel Intelligence Dashboard
# usage: ./run_local.sh

# configuration
# port=8050
# log_dir="logs"

# get the script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# project root should be the parent directory of scripts/
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# move to project root
cd "$PROJECT_ROOT" || { echo "❌ failed to enter project root at $PROJECT_ROOT"; exit 1; }

# determine virtual environment and python path
VENV_PYTHON="./venv/bin/python3"

# ensure venv exists
if [ ! -f "$VENV_PYTHON" ]; then
    echo "❌ virtual environment python not found at $PROJECT_ROOT/venv/bin/python3"
    exit 1
fi

# ensure dashboard.py exists
if [ ! -f "dashboard.py" ]; then
    echo "❌ dashboard.py not found at $PROJECT_ROOT/dashboard.py"
    exit 1
fi

# ensure logs directory exists
mkdir -p "logs"

# stop any existing dashboard instance
echo "🛑 stopping any existing dashboard instances..."
pkill -f "dashboard.py" || true

# start the dashboard (listening on all interfaces)
echo "🚀 starting dashboard from $PROJECT_ROOT..."
echo "📊 log directed to: $PROJECT_ROOT/logs/dashboard_local.log"
nohup "$VENV_PYTHON" dashboard.py > "logs/dashboard_local.log" 2>&1 &

# allow a moment for initialization
sleep 3

# check if it's running
if pgrep -f "dashboard.py" > /dev/null; then
    echo "✅ dashboard successfully started!"
    echo "🔗 local access: http://localhost:8050"
    IP_ADDR=$(hostname -I | awk '{print $1}')
    if [ -n "$IP_ADDR" ]; then
        echo "🌐 network access: http://$IP_ADDR:8050"
    fi
else
    echo "❌ failed to start dashboard. check logs/dashboard_local.log"
    cat logs/dashboard_local.log
fi
