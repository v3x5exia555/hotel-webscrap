#!/bin/bash
# ---------------------------------------------------------------------------
# Cron Script: Run all platform scrapers every 30 minutes
# ---------------------------------------------------------------------------

# Get current script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Navigate to project root
cd "$PROJECT_ROOT" || exit 1

LOCK_FILE="/tmp/hotel_refresh.lock"

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

# Ensure logs directory exists
mkdir -p logs

# Timestamp for log
echo "------------------------------------------------------------" >> logs/cron_scraper.log
echo "🚀 Cron run started at: $(date)" >> logs/cron_scraper.log

# Activate virtual environment if it exists
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
fi

# Run the parallel platforms scraper
# --week: 7 days ahead
# --platforms agoda airbnb: filter to specific platforms
python3 scripts/run_parallel_platforms.py --week --workers 4 --platforms agoda airbnb >> logs/cron_scraper.log 2>&1

echo "✅ Cron run finished at: $(date)" >> logs/cron_scraper.log
echo "------------------------------------------------------------" >> logs/cron_scraper.log
