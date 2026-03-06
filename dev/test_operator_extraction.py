from playwright.sync_api import sync_playwright
import time
import os
import sys

# Add parent dir for utils
sys.path.append(os.getcwd())
from utils.helpers import get_browser_config, logger

def test_url(url):
    with sync_playwright() as p:
        browser_cfg = get_browser_config(use_proxy=False)
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(**browser_cfg)
        page = context.new_page()
        
        print(f"Opening {url}...")
        page.goto(url, timeout=60000)
        time.sleep(5)
        
        # Method 1: Host section
        try:
            # Look for "Hosted by" text
            host_text = page.locator('div:has-text("Hosted by"), h2:has-text("Hosted by")').first.inner_text()
            print(f"Found text: {host_text}")
        except Exception as e:
            print(f"Error M1: {e}")
            
        # Method 2: Specific class from user snippet
        try:
            # User snippet: <div class="t1k2dv0f ...">Hosted by Low</div>
            # Let's try to find text directly
            operator = page.evaluate("""() => {
                const el = Array.from(document.querySelectorAll('div, h2, h3')).find(e => e.innerText.includes('Hosted by'));
                return el ? el.innerText : 'Not Found';
            }""")
            print(f"Operator via JS: {operator}")
        except Exception as e:
            print(f"Error M2: {e}")

        browser.close()

if __name__ == "__main__":
    test_url("https://www.airbnb.com/rooms/1245960687804529443")
