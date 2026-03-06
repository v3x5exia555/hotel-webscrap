from playwright.sync_api import sync_playwright
import time

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
        print(f"Content length: {len(content)}")
        if "Low" in content:
            print("Found 'Low' in content!")
        else:
            print("'Low' not found in content")
        
        # Print all matches of "Hosted by"
        import re
        matches = re.findall(r'Hosted by [^<]+', content)
        print(f"Hosted by matches: {matches}")
        
        browser.close()

if __name__ == "__main__":
    check()
