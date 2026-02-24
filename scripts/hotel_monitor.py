import time
import sys
import os
import argparse
from datetime import datetime

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import scrape_platform_task
from scripts.analyze_pickup import analyze_pickup
from utils.helpers import logger
from utils.database import init_db

def run_monitor(hotel_name=None, location_name=None, district=None, agoda_id="14524", interval_minutes=30):
    init_db()
    
    config_path = "configs/locations.yaml"
    
    if hotel_name and location_name:
        locations = [{
            "name": location_name,
            "district": district or "Unknown",
            "agoda_city_id": agoda_id
        }]
        logger.info(f"🚀 Starting Real-Time Monitor for: {hotel_name} (Single Area)")
    else:
        if not os.path.exists(config_path):
            logger.error(f"Config for all locations not found at {config_path}")
            return
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        locations = []
        for d in config.get('districts', []):
            for a in d.get('areas', []):
                locations.append({
                    "name": a['name'],
                    "district": d['name'],
                    "agoda_city_id": a.get('agoda_city_id', "14524")
                })
        logger.info(f"🚀 Starting FULL MARKET Monitor ({len(locations)} areas)")

    logger.info(f"📍 Interval: {interval_minutes} minutes")
    
    try:
        while True:
            logger.info(f"--- [ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ] Scraping Update Cycle ---")
            
            for loc_cfg in locations:
                logger.info(f"Targeting: {loc_cfg['name']}...")
                # Scrape Agoda & Booking
                scrape_platform_task("agoda", loc_cfg, 1, 1, False)
                scrape_platform_task("booking", loc_cfg, 1, 1, False)
            
            # Run pickup analysis
            logger.info("Comparing latest snapshots for ALL hotels...")
            analyze_pickup()
            
            logger.info(f"Cycle complete. Sleeping for {interval_minutes} minutes...")
            time.sleep(interval_minutes * 60)
            
    except KeyboardInterrupt:
        logger.info("Monitor stopped by user.")

if __name__ == "__main__":
    import yaml
    parser = argparse.ArgumentParser(description="Monitor hotel availability/pricing every 30 mins.")
    parser.add_argument("--hotel", help="Specific hotel name to track")
    parser.add_argument("--location", help="Location name for scraper")
    parser.add_argument("--district", help="District for metadata")
    parser.add_argument("--agoda_id", help="Agoda City ID")
    parser.add_argument("--interval", type=int, default=30, help="Interval in minutes")
    
    args = parser.parse_args()
    
    run_monitor(args.hotel, args.location, args.district, args.agoda_id, args.interval)
