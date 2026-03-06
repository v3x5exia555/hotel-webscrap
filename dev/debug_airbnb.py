from playwright.sync_api import sync_playwright
import time
import os
import sys

def debug():
    url = "https://www.airbnb.com/rooms/1245960687804529443"
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        print(f"Navigating to {url}")
        page.goto(url, wait_until="networkidle")
        print(f"Title: {page.title()}")
        page.screenshot(path="airbnb_debug.png")
        
        # Try to find "Hosted by"
        content = page.content()
        if "Hosted by" in content:
            print("Found 'Hosted by' in HTML content!")
            # Extract it
            import re
            match = re.search(r"Hosted by ([^<]+)", content)
            if match:
                print(f"Regex Match: {match.group(1)}")
        else:
            print("'Hosted by' NOT found in HTML content")
            # Maybe it's "Host" or something else?
            if "Host" in content:
                print("Found 'Host' in content")
        
        browser.close()

if __name__ == "__main__":
    debug()
