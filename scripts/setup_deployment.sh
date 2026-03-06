#!/bin/bash
# ---------------------------------------------------------------------------
# scripts/setup_deployment.sh
# ---------------------------------------------------------------------------
# Purpose: Orchestrate all automation scripts (Scrapers + Watchdog + Sync)
# on the current machine and set up the Crontab for autonomous operation.

set -euo pipefail

# Colors for pretty output
GREEN='\033[0;32m'
CYAN='\033[0;36m'
BOLD='\033[1m'
RESET='\033[0m'

log() { echo -e "${CYAN}[DEPLOY]${RESET} $1"; }
ok()  { echo -e "${GREEN} ✅ $1${RESET}"; }

# Detect project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT" || exit 1

log "Starting deployment sequence at $PROJECT_ROOT"

# 1. Make all scripts executable
log "Step 1: Setting permissions..."
chmod +x scripts/*.sh
ok "Permissions updated."

# 2. Ensure logs directory and initial log files exist
log "Step 2: Preparing log infrastructure..."
mkdir -p logs
touch logs/cron_summary.log
touch logs/cron.log
touch logs/watchdog.log
ok "Logs initialized."

# 3. Setup Crontab
log "Step 3: Configuring crontab tasks..."

# Define your jobs
# Job 1: Stability Watchdog (Runs every minute - keeps dashboard alive)
JOB_WATCHDOG="* * * * * $PROJECT_ROOT/scripts/dashboard_watchdog.sh >> $PROJECT_ROOT/logs/cron_summary.log 2>&1"

# Job 2: Parallel 30-min Scraper (Pahang Market Intelligence)
JOB_SCRAPER="*/30 * * * * $PROJECT_ROOT/scripts/cron_30min_scraper.sh >> $PROJECT_ROOT/logs/cron_summary.log 2>&1"

# Job 3: Daily Full Refresh (Syncs and stays comprehensive)
JOB_REFRESH="*/30 * * * * $PROJECT_ROOT/scripts/full_refresh.sh >> $PROJECT_ROOT/logs/cron.log 2>&1"

# Create a temporary file for the new crontab
TMP_CRON=$(mktemp)

# Clean existing jobs related to this project to avoid duplicates
crontab -l 2>/dev/null | grep -v "$PROJECT_ROOT" > "$TMP_CRON" || true

# Append new jobs
echo "$JOB_WATCHDOG" >> "$TMP_CRON"
echo "$JOB_SCRAPER" >> "$TMP_CRON"
echo "$JOB_REFRESH" >> "$TMP_CRON"

# Load new crontab
crontab "$TMP_CRON"
rm "$TMP_CRON"
ok "Crontab updated with Scraper + Refresh + Watchdog."

# 4. Trigger initial startup
log "Step 4: Launching services..."
bash scripts/dashboard_watchdog.sh
ok "Dashboard stability check triggered."

echo -e "\n${BOLD}${GREEN}==============================================${RESET}"
echo -e "🚀 DEPLOYMENT COMPLETE"
echo -e "=============================================="
echo -e "📍 Location: $PROJECT_ROOT"
echo -e "🛡️  Watchdog: ACTIVE (1m check)"
echo -e "🔍 Scraper : ACTIVE (30m cycle)"
echo -e "📊 Dash Log: logs/dashboard.log"
echo -e "📋 Cron Log: logs/cron_summary.log"
echo -e "${BOLD}${GREEN}==============================================${RESET}\n"
