from playwright.sync_api import sync_playwright
import time

def check():
    url = "https://www.airbnb.com/rooms/1245960687804529443"
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        print(f"Navigating to {url}")
        page.goto(url, timeout=60000)
        time.sleep(5)
        
        # Try to find "Hosted by"
        # The user's snippet: <div class="...">Hosted by Low</div>
        host_elements = page.get_by_text("Hosted by").all()
        for i, el in enumerate(host_elements):
            print(f"Match {i}: {el.inner_text()}")
            # Get parent or surrounding text
        
        # Another common one is h2 or specialized host section
        try:
            host_header = page.locator('h2:has-text("Hosted by")').inner_text()
            print(f"H2 Host: {host_header}")
        except:
            pass
            
        browser.close()

if __name__ == "__main__":
    check()
