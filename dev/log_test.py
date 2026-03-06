import sys
import os
sys.path.append(os.getcwd())
from utils.helpers import logger
from playwright.sync_api import sync_playwright
import time

def test():
    logger.info("LOG TEST START")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("https://www.airbnb.com/s/Kuantan--Malaysia/homes")
        time.sleep(5)
        cards = page.locator('[data-testid="card-container"]').count()
        logger.info(f"Cards found: {cards}")
        browser.close()
    logger.info("LOG TEST END")

if __name__ == "__main__":
    test()
