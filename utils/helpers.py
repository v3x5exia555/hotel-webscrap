from datetime import datetime, timedelta
import pandas as pd
import os
import logging
import sys

# Configure logging
log_dir = "logs"
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

log_file = os.path.join(log_dir, "scraper.log")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

def get_future_date(days_ahead):
    """Returns a date string for N days in the future."""
    return (datetime.now() + timedelta(days=days_ahead)).strftime("%Y-%m-%d")

def save_to_csv(data, platform="Unknown", days_ahead=0, nights=1, location="Unknown", output_dir="data"):
    """Saves a list of dictionaries to a CSV file in a platform-specific and date-specific folder."""
    # Create platform subdirectory
    platform_folder = platform.lower().replace(" ", "_").replace(".", "")
    date_folder = datetime.now().strftime("%Y%m%d")
    timestamp = datetime.now().strftime("%H%M%S")
    
    # target_dir: platform/YYYYMMDD/
    target_dir = os.path.join(output_dir, platform_folder, date_folder)
    
    if not os.path.exists(target_dir):
        os.makedirs(target_dir, exist_ok=True)
    
    # filename: {timestamp}_{pid}_{micro}___{location}__day_ahead{value}__night{value}.csv
    loc_clean = location.lower().replace(" ", "_").replace(",", "")
    pid = os.getpid()
    micro = datetime.now().strftime("%f")[:3]
    filename = f"{timestamp}_{pid}_{micro}__{loc_clean}__day_ahead{days_ahead}__night{nights}.csv"
    filepath = os.path.join(target_dir, filename)
    
    df = pd.DataFrame(data)
    df.to_csv(filepath, index=False)
    logger.info(f"Successfully saved {len(data)} items to {filepath}")
    return filepath

def clean_price(price_str):
    """Extracts numeric value from currency string."""
    if not price_str or price_str == "N/A":
        return 0.0
    # Remove currency symbols and commas
    clean = "".join(c for i, c in enumerate(price_str) if c.isdigit() or c == "." or (c == "," and i > 0))
    clean = clean.replace(",", "")
    try:
        return float(clean)
    except:
        return 0.0

def get_month_name():
    """Returns the current month name."""
    return datetime.now().strftime("%B")

def get_proxy_config():
    """Reads proxy settings from environment variables or returns None."""
    # Placeholder: In a real scenario, you'd use os.getenv or a config file
    # Example format: {"server": "http://myproxy.com:3128", "username": "user", "password": "pwd"}
    proxy_server = os.getenv("PROXY_SERVER")
    if proxy_server:
        return {
            "server": proxy_server,
            "username": os.getenv("PROXY_USER"),
            "password": os.getenv("PROXY_PASS")
        }
    return None

def get_browser_config(use_proxy=False):
    """Returns common browser configuration, including optional proxy."""
    config = {
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "viewport": {'width': 1920, 'height': 1080}
    }
    
    if use_proxy:
        proxy = get_proxy_config()
        if proxy:
            config["proxy"] = proxy
            logger.info(f"Using proxy: {proxy['server']}")
        else:
            logger.warning("Proxy requested but PROXY_SERVER not set.")
            
    return config
