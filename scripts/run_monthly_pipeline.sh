#!/bin/bash

# Port for the dashboard
PORT=8050

# Move to the project root
cd "$(dirname "$0")/.." || exit

echo "--- Monthly Pipeline Started ---"

# Kill existing dashboard if running (Optional: can be adjusted if you want it to keep running)
if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null ; then
    echo "Port $PORT is being used. Killing process..."
    fuser -k $PORT/tcp || lsof -ti:$PORT | xargs kill -9
    sleep 2
fi

# Run the 30-day sequence
# We use --monthly to loop 30 check-in dates
# We can also add --nights if we want more than just 1-night stays
echo "Running Monthly Scrape (30-day loop)..."
./venv/bin/python3 main.py --monthly --workers 5

echo "--- Monthly Pipeline Completed ---"
# You can uncomment the dashboard launch if you want it to restart automatically
# echo "Launching Dashboard..."
# ./venv/bin/python3 dashboard.py

