from playwright.sync_api import sync_playwright
import time

def dump():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        print("Navigating...")
        page.goto("https://www.airbnb.com/s/Kuala-Lumpur--Malaysia/homes", timeout=60000)
        time.sleep(5) # Wait for cards
        
        cards = page.locator('[data-testid="card-container"]').all()
        if cards:
            print(f"Found {len(cards)} cards.")
            print("Dumping HTML of the first card bundle...")
            # Let's see the parent or container that might have more info
            print(cards[0].inner_html())
            print("--- TEXT ---")
            print(cards[0].inner_text())
        else:
            print("No cards found.")
        
        browser.close()

if __name__ == "__main__":
    dump()
