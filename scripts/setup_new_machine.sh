#!/bin/bash
# ============================================================
#  setup_new_machine.sh
#  One-shot deployment script for the Hotel Intelligence
#  scraper on a brand-new Ubuntu/Debian server.
#
#  Run on the remote server:
#    bash scripts/setup_new_machine.sh
#
#  What it does:
#    1. Installs system packages (Python 3.11+, git, sqlite3, etc.)
#    2. Creates Python virtual environment
#    3. Installs all pip dependencies (including supabase, dotenv)
#    4. Installs Playwright + Chromium browser
#    5. Creates required directories (data/, logs/, cache-directory/)
#    6. Sets up .env from template if missing
#    7. Makes shell scripts executable
#    8. Validates the setup with a dry-run import test
# ============================================================

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
RESET='\033[0m'

log()   { echo -e "${CYAN}[SETUP]${RESET} $1"; }
ok()    { echo -e "${GREEN}  ✅ $1${RESET}"; }
warn()  { echo -e "${YELLOW}  ⚠️  $1${RESET}"; }
fail()  { echo -e "${RED}  ❌ $1${RESET}"; exit 1; }

echo ""
echo -e "${BOLD}${CYAN}============================================================${RESET}"
echo -e "${BOLD}${CYAN}  🏨 Hotel Intelligence — New Machine Setup${RESET}"
echo -e "${BOLD}${CYAN}  $(date '+%Y-%m-%d %H:%M:%S')${RESET}"
echo -e "${BOLD}${CYAN}============================================================${RESET}"
echo ""

# ---- Detect project root ----
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
log "Project root: $PROJECT_ROOT"

cd "$PROJECT_ROOT"

# ============================================================
# STEP 1: System Dependencies
# ============================================================
log "Step 1/8 — Installing system dependencies..."

export DEBIAN_FRONTEND=noninteractive

if command -v apt-get &> /dev/null; then
    apt-get update -qq
    apt-get install -y -qq \
        python3 \
        python3-venv \
        python3-pip \
        python3-dev \
        git \
        sqlite3 \
        wget \
        curl \
        gnupg \
        libnss3 \
        libnspr4 \
        libatk1.0-0 \
        libatk-bridge2.0-0 \
        libcups2 \
        libdrm2 \
        libdbus-1-3 \
        libxkbcommon0 \
        libxcomposite1 \
        libxdamage1 \
        libxext6 \
        libxfixes3 \
        libxrandr2 \
        libgbm1 \
        libasound2t64 \
        libpango-1.0-0 \
        libpangocairo-1.0-0 \
        libxshmfence1 \
        libxml2-dev \
        libxslt1-dev \
        build-essential \
        2>/dev/null || true
    ok "System packages installed"
else
    warn "Not a Debian/Ubuntu system — skipping apt-get. Install dependencies manually."
fi

# ============================================================
# STEP 2: Python Virtual Environment
# ============================================================
log "Step 2/8 — Setting up Python virtual environment..."

PYTHON_CMD="python3"
if ! command -v python3 &> /dev/null; then
    fail "python3 not found. Install Python 3.11+ first."
fi

PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | grep -oP '\d+\.\d+')
log "  Python version: $PYTHON_VERSION"

if [ ! -d "venv" ]; then
    $PYTHON_CMD -m venv venv
    ok "Virtual environment created at ./venv"
else
    ok "Virtual environment already exists"
fi

# Activate venv
source venv/bin/activate
ok "Virtual environment activated"

# Upgrade pip
pip install --upgrade pip --quiet
ok "pip upgraded"

# ============================================================
# STEP 3: Install Python Dependencies
# ============================================================
log "Step 3/8 — Installing Python dependencies..."

pip install --quiet -r requirements.txt
ok "Core requirements installed"

# Install additional packages that might be missing from requirements.txt
pip install --quiet \
    supabase \
    python-dotenv \
    2>/dev/null || true
ok "Supabase + dotenv extras installed"

# ============================================================
# STEP 4: Install Playwright Browsers
# ============================================================
log "Step 4/8 — Installing Playwright browsers..."

playwright install --with-deps chromium
ok "Playwright Chromium browser installed"

# ============================================================
# STEP 5: Create Required Directories
# ============================================================
log "Step 5/8 — Creating required directories..."

mkdir -p data
mkdir -p logs
mkdir -p scripts/logs
mkdir -p cache-directory
mkdir -p data/agoda
mkdir -p data/bookingcom
ok "Directories created (data/, logs/, scripts/logs/, cache-directory/)"

# ============================================================
# STEP 6: Environment Variables (.env)
# ============================================================
log "Step 6/8 — Checking .env file..."

if [ ! -f ".env" ]; then
    cat > .env <<'ENVEOF'
# ---- Supabase Connection ----
SUPABASE_URL=https://kyygzzuygmcjoigpemfx.supabase.co
SUPABASE_KEY=sb_publishable_BLc8PKawPqXz8dZDDmeF4A_zzE5urfI
SUPABASE_SCHEMA=analysis_hotel

# ---- Optional: Anthropic API ----
# ANTHROPIC_API_KEY=your_key_here
ENVEOF
    warn ".env created from template — REVIEW and update credentials if needed!"
else
    ok ".env already exists"
fi

# ============================================================
# STEP 7: Make Scripts Executable
# ============================================================
log "Step 7/8 — Making scripts executable..."

chmod +x scripts/*.sh 2>/dev/null || true
ok "All shell scripts in scripts/ are now executable"

# ============================================================
# STEP 8: Validation — Dry Run Import Test
# ============================================================
log "Step 8/8 — Running validation tests..."

echo ""
log "  Test 1: Importing core Python modules..."
venv/bin/python3 -c "
import sys
modules_ok = True

tests = [
    ('pandas',            'import pandas'),
    ('playwright',        'from playwright.sync_api import sync_playwright'),
    ('yaml',              'import yaml'),
    ('supabase',          'from supabase import create_client'),
    ('dotenv',            'from dotenv import load_dotenv'),
    ('lxml',              'import lxml'),
    ('requests',          'import requests'),
    ('dash',              'import dash'),
    ('plotly',            'import plotly'),
]

for name, stmt in tests:
    try:
        exec(stmt)
        print(f'    ✅ {name}')
    except ImportError as e:
        print(f'    ❌ {name}: {e}')
        modules_ok = False

if not modules_ok:
    print()
    print('  ⚠️  Some modules failed. Run: pip install -r requirements.txt')
    sys.exit(1)
else:
    print('    All modules OK!')
"
IMPORT_STATUS=$?

echo ""
log "  Test 2: Checking Playwright browser..."
venv/bin/python3 -c "
from playwright.sync_api import sync_playwright
try:
    pw = sync_playwright().start()
    browser = pw.chromium.launch(headless=True)
    browser.close()
    pw.stop()
    print('    ✅ Playwright Chromium browser works')
except Exception as e:
    print(f'    ❌ Playwright error: {e}')
    print('    Run: playwright install --with-deps chromium')
"
PLAYWRIGHT_STATUS=$?

echo ""
log "  Test 3: Checking database init..."
venv/bin/python3 -c "
import sys, os
sys.path.insert(0, '.')
from utils.database import init_db, DB_PATH
init_db()
print(f'    ✅ SQLite database initialized at {DB_PATH}')
"
DB_STATUS=$?

echo ""
echo -e "${BOLD}${CYAN}============================================================${RESET}"
echo -e "${BOLD}${CYAN}  📊 Setup Summary${RESET}"
echo -e "${BOLD}${CYAN}============================================================${RESET}"

if [ $IMPORT_STATUS -eq 0 ] && [ $PLAYWRIGHT_STATUS -eq 0 ] && [ $DB_STATUS -eq 0 ]; then
    echo -e "${GREEN}  ✅ ALL CHECKS PASSED — Ready to scrape!${RESET}"
else
    echo -e "${YELLOW}  ⚠️  Some checks failed — review errors above${RESET}"
fi

echo ""
echo -e "  ${BOLD}Quick-start commands:${RESET}"
echo ""
echo -e "    ${CYAN}# Activate venv${RESET}"
echo -e "    source venv/bin/activate"
echo ""
echo -e "    ${CYAN}# Parallel scrape — all 3 platforms at once${RESET}"
echo -e "    python3 scripts/run_parallel_platforms.py --monthly --workers 3"
echo ""
echo -e "    ${CYAN}# Weekly scrape${RESET}"
echo -e "    python3 scripts/run_parallel_platforms.py --week --workers 2"
echo ""
echo -e "    ${CYAN}# Single platform only${RESET}"
echo -e "    python3 scripts/run_parallel_platforms.py --monthly --platforms booking"
echo ""
echo -e "    ${CYAN}# Shell shortcut (defaults to monthly)${RESET}"
echo -e "    ./scripts/run_parallel_monthly.sh"
echo ""
echo -e "${BOLD}${CYAN}============================================================${RESET}"
