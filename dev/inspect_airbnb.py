from playwright.sync_api import sync_playwright
import time

def inspect():
    url = "https://www.airbnb.com/s/Kuala-Lumpur--Malaysia/homes"
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        print(f"Navigating to {url}")
        page.goto(url, timeout=60000)
        time.sleep(10)
        
        cards = page.locator('[data-testid="card-container"]').all()
        print(f"Found {len(cards)} cards")
        for i, card in enumerate(cards[:5]):
            print(f"--- Card {i} ---")
            print(card.inner_text())
            # Check for hidden links or spans
            links = card.locator('a').all()
            for link in links:
                print(f"Link: {link.get_attribute('href')}")
            
        browser.close()

if __name__ == "__main__":
    inspect()
