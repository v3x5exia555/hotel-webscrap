import sys
import os
import yaml
import argparse
import inspect
import random
import time
from concurrent.futures import ProcessPoolExecutor, as_completed

# Add the current directory to path so we can import from scrapers and utils
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from scrapers.booking import scrape_booking
from scrapers.agoda import scrape_agoda
from scrapers.traveloka import scrape_traveloka
from scrapers.airbnb import scrape_airbnb
from utils.helpers import logger
from utils.database import init_db

def scrape_platform_task(platform, loc, d_ahead, n_duration, use_proxy, base_date=None):
    """Worker function for a single platform, location and date."""
    name = loc.get('name')
    district = loc.get('district')
    agoda_id = loc.get('agoda_city_id')
    
    # Random delay between tasks to avoid rate-limiting
    delay = random.uniform(3, 8)
    time.sleep(delay)
    
    logger.info(f"--- [Task] Platform: {platform.upper()} | Area: {name} | Day Ahead: {d_ahead} | Nights: {n_duration} | Start: {base_date or 'Today'} ---")
    
    if platform.lower() == "booking":
        try:
            scrape_booking(location=name, district=district, days_ahead=d_ahead, nights=n_duration, use_proxy=use_proxy, base_date=base_date)
        except Exception as e:
            logger.error(f"Booking.com scraper failed for {name}: {e}")
            return f"Failed: Booking.com @ {name}"

    elif platform.lower() == "agoda":
        try:
            scrape_agoda(location=name, district=district, city_id=agoda_id, days_ahead=d_ahead, nights=n_duration, use_proxy=use_proxy, base_date=base_date)
        except Exception as e:
            logger.error(f"Agoda scraper failed for {name}: {e}")
            return f"Failed: Agoda @ {name}"

    elif platform.lower() == "traveloka":
        try:
            scrape_traveloka(location=name, district=district, days_ahead=d_ahead, nights=n_duration, use_proxy=use_proxy, base_date=base_date)
        except Exception as e:
            logger.error(f"Traveloka scraper failed for {name}: {e}")
            return f"Failed: Traveloka @ {name}"

    elif platform.lower() == "airbnb":
        try:
            scrape_airbnb(location=name, district=district, days_ahead=d_ahead, nights=n_duration, use_proxy=use_proxy, base_date=base_date)
        except Exception as e:
            logger.error(f"Airbnb scraper failed for {name}: {e}")
            return f"Failed: Airbnb @ {name}"
    
    return f"Completed: {platform} @ {name} (Day {d_ahead}, Night {n_duration})"

def run_scrapers_from_config(config_path="configs/locations.yaml", use_proxy=False, days=1, nights=1, start_date=None, location_name=None, max_workers=2, platforms=None):
    # Initialize Database
    init_db()
    
    if platforms is None:
        platforms = ["booking", "agoda", "traveloka", "airbnb"]

    if not os.path.exists(config_path):
        logger.error(f"Config file not found: {config_path}")
        return

    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
        
    districts = config.get('districts', [])
    processed_locations = []

    if location_name:
        for d in districts:
            for loc in d.get('areas', []):
                if loc['name'].lower() == location_name.lower():
                    processed_locations.append({
                        "district": d['name'],
                        "name": loc['name'],
                        "agoda_city_id": loc.get('agoda_city_id')
                    })
        
        if not processed_locations:
            logger.warning(f"Location '{location_name}' not found. Using generic search.")
            processed_locations.append({
                "district": "Unknown",
                "name": location_name,
                "agoda_city_id": "14524"
            })
    else:
        for d in districts:
            for loc in d.get('areas', []):
                processed_locations.append({
                    "district": d['name'],
                    "name": loc['name'],
                    "agoda_city_id": loc.get('agoda_city_id')
                })

    if not processed_locations:
        logger.warning("No locations found to process.")
        return

    tasks = []
    # Nested loops as requested by user
    for n_duration in range(1, nights + 1):
        # If nights=1, minimum days_ahead must be 2
        min_day = 2 if n_duration == 1 else 0
        for d_offset in range(min_day, days):
            for loc in processed_locations:
                for platform in platforms:
                    tasks.append((platform, loc, d_offset, n_duration, use_proxy, start_date))

    logger.info(f"Queueing {len(tasks)} parallel scraping tasks (Nights {nights} x Days {days}) using {max_workers} processes...")
    
    # Using ProcessPoolExecutor for true multi-processing
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        future_to_task = {executor.submit(scrape_platform_task, *task): task for task in tasks}
        for future in as_completed(future_to_task):
            try:
                result = future.result()
                logger.info(result)
            except Exception as e:
                logger.error(f"Task generated an unexpected exception: {e}")


    logger.info("--- All Tasks Completed ---")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("location", nargs="?", default=None, help="Specific location to scrape (optional)")
    parser.add_argument("--proxy", action="store_true", help="Use proxy server")
    parser.add_argument("--days", type=int, default=1, help="Number of check-in date offsets to scan")
    parser.add_argument("--nights", type=int, default=1, help="Max number of nights for the stay")
    parser.add_argument("--start-date", type=str, default=None, help="Base check-in date (YYYY-MM-DD)")
    parser.add_argument("--week", action="store_true", help="Run for a full week (7 days)")
    parser.add_argument("--monthly", action="store_true", help="Run for a full month (30 days)")
    parser.add_argument("--workers", type=int, default=2, help="Number of parallel scraper processes")
    parser.add_argument("--platform", type=str, default=None, help="Specific platform to scrape (booking, agoda, traveloka, airbnb)")
    args = parser.parse_args()
    
    if args.week:
        args.days = 7
    if args.monthly:
        args.days = 30
    
    # Filter platforms if requested
    target_platforms = ["booking", "agoda", "traveloka", "airbnb"]
    if args.platform:
        p_filter = args.platform.lower()
        if p_filter in target_platforms:
            target_platforms = [p_filter]
        else:
            logger.error(f"Invalid platform: {args.platform}. Must be one of {target_platforms}")
            sys.exit(1)

    # Pass target_platforms to run_scrapers_from_config
    run_scrapers_from_config(
        use_proxy=args.proxy, 
        days=args.days, 
        nights=args.nights, 
        start_date=args.start_date, 
        location_name=args.location, 
        max_workers=args.workers,
        platforms=target_platforms
    )
