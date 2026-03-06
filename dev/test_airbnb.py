from playwright.sync_api import sync_playwright

def test():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("https://www.airbnb.com/s/Kuala-Lumpur--Malaysia/homes")
        page.wait_for_timeout(3000)
        
        cards = page.locator('[data-testid="card-container"]').all()
        for i, card in enumerate(cards[:3]):
            print(f"Card {i}")
            print(card.inner_text())
            print("---")
        
        browser.close()

if __name__ == "__main__":
    test()
