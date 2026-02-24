# #!/bin/bash

# # Port for the dashboard
# PORT=8050

# # Move to the project root
# cd "$(dirname "$0")/.." || exit


# echo "Checking if port $PORT is in use..."
# if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null ; then
#     echo "Port $PORT is being used. Killing process..."
#     fuser -k $PORT/tcp || lsof -ti:$PORT | xargs kill -9
#     sleep 2
# else
#     echo "Port $PORT is free."
# fi

# # Run scraper (Example: daily 1 day)
# echo "Starting Scraper..."
# ./venv/bin/python3 main.py --mode daily --days 1

# # Run Dashboard
# echo "Starting Dashboard on port $PORT..."
# ./venv/bin/python3 dashboard.py
