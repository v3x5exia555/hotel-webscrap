#!/bin/bash

# Port for the dashboard
PORT=8050

# Move to the project root
cd "$(dirname "$0")/.." || exit


echo "--- Weekly Pipeline Started ---"

# Kill existing dashboard if running
if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null ; then
    echo "Port $PORT is being used. Killing process..."
    fuser -k $PORT/tcp || lsof -ti:$PORT | xargs kill -9
    sleep 2
fi

# Run the 7-day pickup sequence
echo "Running Weekly Scrape..."
./venv/bin/python3 main.py --week --workers 4

# Run Dashboard
# echo "Launching Dashboard..."
# ./venv/bin/python3 dashboard.py
