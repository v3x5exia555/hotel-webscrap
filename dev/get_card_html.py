from playwright.sync_api import sync_playwright
import time

def get():
    url = "https://www.airbnb.com/s/Kuantan--Malaysia/homes"
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        page.goto(url, wait_until="networkidle")
        
        card = page.locator('[data-testid="card-container"]').first
        if card:
            print("FOUND CARD")
            print(f"Inner Text: {card.inner_text()}")
            print(f"HTML: {card.inner_html()}")
        else:
            print("NO CARD FOUND")
        
        browser.close()

if __name__ == "__main__":
    get()
