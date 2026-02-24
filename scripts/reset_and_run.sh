#!/bin/bash

# Port for the dashboard (if you want to restart it too)
PORT=8050
VENV_PYTHON="/home/v3/Desktop/hotel/venv/bin/python3"
PROJECT_ROOT="/home/v3/Desktop/hotel"

# Move to the project root
cd "$PROJECT_ROOT" || exit

echo "--- Full Reset & Restart Started ---"

# 1. Kill existing scraper processes
echo "🧹 Stopping existing scrapers..."
pkill -f "main.py"
pkill -f "run_weekly_pipeline.sh"
sleep 2

# 2. Clear Database and CSV files
echo "🗑️ Wiping existing data..."
if [ -f "$VENV_PYTHON" ]; then
    $VENV_PYTHON "$PROJECT_ROOT/scripts/clear_data.py"
else
    python3 "$PROJECT_ROOT/scripts/clear_data.py"
fi

# 3. Start Fresh Scrape in background
echo "🚀 Starting fresh weekly audit..."
nohup bash "$PROJECT_ROOT/scripts/run_weekly_pipeline.sh" > "$PROJECT_ROOT/logs/pipeline.log" 2>&1 &

echo "=============================================="
echo "✅ RESET COMPLETE"
echo "=============================================="
echo "Old data is deleted."
echo "New scan is running in the background."
echo "You can check progress with: tail -f logs/pipeline.log"
echo "=============================================="
