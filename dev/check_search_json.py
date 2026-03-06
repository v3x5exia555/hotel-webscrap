from playwright.sync_api import sync_playwright
import time
import json
import re

def check():
    url = "https://www.airbnb.com/s/Kuantan--Malaysia/homes"
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        page.goto(url, wait_until="networkidle")
        
        content = page.content()
        # Look for host names or operator names in the source
        # Usually it's in a script tag with data-state or similar
        items = re.findall(r'"hostName":"([^"]+)"', content)
        print(f"Found {len(items)} hostNames in JSON/Source:")
        print(items[:10])
        
        browser.close()

if __name__ == "__main__":
    check()
