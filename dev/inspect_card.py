import sys
import os
sys.path.append(os.getcwd())
from utils.helpers import logger
from playwright.sync_api import sync_playwright
import time

def test():
    logger.info("INSPECT CARD START")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("https://www.airbnb.com/s/Kuantan--Malaysia/homes")
        time.sleep(5)
        card = page.locator('[data-testid="card-container"]').first
        if card:
            html = card.inner_html()
            logger.info("FIRST CARD HTML DUMP:")
            logger.info(html)
            text = card.inner_text()
            logger.info("FIRST CARD TEXT DUMP:")
            logger.info(text)
        else:
            logger.info("NO CARD FOUND")
        browser.close()
    logger.info("INSPECT CARD END")

if __name__ == "__main__":
    test()
