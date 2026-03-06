import sys
import os
import subprocess
import logging

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from datetime import datetime
from utils.database import get_supabase_client, get_supabase_table, DB_PATH
import sqlite3
import pandas as pd

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_command(command):
    """Runs a shell command and logs output."""
    try:
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        for line in process.stdout:
            print(line, end='')
        process.wait()
        return process.returncode
    except Exception as e:
        logger.error(f"Failed to run command: {e}")
        return 1

def sync_sqlite_to_supabase():
    """Calls the standalone sync script to migrate data to Supabase."""
    logger.info("🔄 Triggering full sync to Supabase...")
    returncode = run_command("python3 push_data_to_supabase.py")
    if returncode == 0:
        logger.info("✅ Supabase sync completed.")
    else:
        logger.warning("⚠️ Supabase sync returned non-zero exit code.")

def main():
    logger.info("🚀 Starting Hotel Intelligence Process Job")
    
    # 1. Sync existing data
    sync_sqlite_to_supabase()
    
    # Run the scraper pipeline
    logger.info("🎯 Launching Scraper Pipeline...")
    
    # Use 2 workers by default for resource efficiency
    workers = 2
    # Parse arguments
    is_monthly = "--monthly" in sys.argv
    platform = None
    for arg in sys.argv:
        if arg.startswith("--platform="):
            platform = arg.split("=")[1]
        elif arg == "--platform" and sys.argv.index(arg) + 1 < len(sys.argv):
            platform = sys.argv[sys.argv.index(arg) + 1]

    # Build command
    cmd = f"python3 main.py --workers {workers}"
    if is_monthly:
        cmd += " --monthly"
    else:
        cmd += " --week"
    
    if platform:
        cmd += f" --platform {platform}"
        
    exit_code = run_command(cmd)
    
    if exit_code == 0:
        logger.info("✅ Process job completed successfully!")
    else:
        logger.error(f"❌ Process job failed with exit code {exit_code}")

if __name__ == "__main__":
    main()
