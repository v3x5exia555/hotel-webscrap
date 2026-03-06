import sys
import os
sys.path.append(os.getcwd())
from scrapers.airbnb import scrape_airbnb
from utils.helpers import logger

def verify():
    logger.info("VERIFY AIRBNB OPERATOR START")
    # Scrape 2 hotels for Kuantan
    scrape_airbnb(location="Kuantan", target_count=2)
    logger.info("VERIFY AIRBNB OPERATOR END")

if __name__ == "__main__":
    verify()
