#!/bin/bash
# ============================================================
#  run_parallel_monthly.sh
#  Launches Booking + Agoda + Traveloka scrapers IN PARALLEL.
#  Each platform gets its own OS process and worker pool.
#
#  Usage:
#    ./scripts/run_parallel_monthly.sh          # monthly, 3 workers/platform
#    ./scripts/run_parallel_monthly.sh --week   # weekly mode
#    ./scripts/run_parallel_monthly.sh --no-sync # skip Supabase push
# ============================================================

set -euo pipefail

# Move to project root
cd "$(dirname "$0")/.." || exit 1

# Activate venv if it exists
if [ -f "./venv/bin/activate" ]; then
    source ./venv/bin/activate
fi

PYTHON="${VIRTUAL_ENV:-}/bin/python3"
[ -x "$PYTHON" ] || PYTHON="python3"

echo ""
echo "============================================================"
echo "  🏨  Hotel Intelligence — Parallel Platform Scraper"
echo "  Started : $(date '+%Y-%m-%d %H:%M:%S')"
echo "============================================================"
echo ""

# Pass all arguments straight through to the Python launcher
"$PYTHON" scripts/run_parallel_platforms.py --monthly --workers 3 "$@"

EXIT_CODE=$?

echo ""
echo "============================================================"
echo "  Finished : $(date '+%Y-%m-%d %H:%M:%S')  |  Exit: $EXIT_CODE"
echo "============================================================"

exit $EXIT_CODE
