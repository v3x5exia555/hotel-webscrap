import time
import sys
import os
from playwright.sync_api import sync_playwright
from datetime import datetime
from utils.helpers import get_future_date, save_to_csv, get_browser_config, logger, clean_price, get_month_name, SCRAPER_CONFIG
from utils.database import save_snapshot

def scrape_traveloka(location="Kuala Lumpur", district="Unknown", days_ahead=28, nights=1, target_count=100, use_proxy=False, base_date=None):
    """
    Scrapes hotel data from Traveloka Malaysia.
    Uses UI-based search for reliability across different areas.
    """
    checkin_date = get_future_date(days_ahead, base_date=base_date)
    checkout_date = get_future_date(days_ahead + nights, base_date=base_date)
    month_name = get_month_name()
    
    # We navigate to the hotel home page first to use the search bar for reliability
    base_url = "https://www.traveloka.com/en-my/hotel/"
    
    logger.info(f"[Traveloka] Starting search for {location} ({checkin_date} to {checkout_date})")
    
    with sync_playwright() as p:
        browser_cfg = get_browser_config(use_proxy=use_proxy)
        # Using a slightly different user agent or viewport if needed
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(**browser_cfg)
        page = context.new_page()
        
        try:
            # Retry logic for navigation (from configs/config.yaml)
            max_retries = SCRAPER_CONFIG['retry']
            nav_timeout = SCRAPER_CONFIG['timeout'] * 1000  # convert seconds to ms
            for attempt in range(max_retries):
                try:
                    page.goto(base_url, timeout=nav_timeout, wait_until="load")
                    break
                except Exception as e:
                    if attempt == max_retries - 1: raise e
                    logger.warning(f"[Traveloka] Retry {attempt+1} for {location} due to: {e}")
                    time.sleep(5)
            
            # Step 2: Handle search input
            # Destination - looking for the autocomplete field
            dest_input = page.locator('input[data-testid="autocomplete-field"]')
            if dest_input.count() == 0:
                 # Fallback to broader selector if testid fails
                 dest_input = page.locator('input[placeholder*="destination"], input[placeholder*="Kuala Lumpur"]')
            
            if dest_input.count() > 0:
                dest_input.first.click()
                # Clear and fill
                dest_input.first.fill("")
                dest_input.first.type(location, delay=100)
                time.sleep(2)
                # Select the first suggestion
                page.keyboard.press("ArrowDown")
                page.keyboard.press("Enter")
                time.sleep(1)
            else:
                logger.error("[Traveloka] Could not find destination input field.")
                return

            # Note: Handling the date picker on Traveloka is complex via UI.
            # We will try to click the search button and hope the default or 
            # recently used dates are acceptable, OR we can try to inject the date.
            # However, for a production scraper, we should ideally use the URL spec if known.
            
            # Click Search button
            search_btn = page.locator('div[role="button"]:has-text("Search"), button:has-text("Search")').first
            search_btn.click()
            
            # Wait for redirection and results
            time.sleep(5)
            
            # Check for results container
            card_selector = 'div.r-14lw9ot.r-1xfd6ze.r-1loqt21, div[data-testid="hotel-card"]'
            try:
                page.wait_for_selector(card_selector, timeout=20000)
            except:
                logger.warning(f"[Traveloka] No results cards found for {location} within timeout.")
                # Maybe try a reload or check if 'no results' message
                if "No hotels found" in page.content() or "Try changing" in page.content():
                    logger.info(f"[Traveloka] No hotels found for {location}")
                    return
            
            logger.info(f"[Traveloka] Extracting data from {page.url}")
            
            hotels_data = []
            seen_names = set()
            
            # Scrolling loop to load more
            for i in range(5): 
                cards = page.locator(card_selector).all()
                for card in cards:
                    if len(hotels_data) >= target_count:
                        break
                    try:
                        title_el = card.locator('h3[role="heading"]')
                        title = title_el.inner_text().strip() if title_el.count() > 0 else "N/A"
                        
                        if title == "N/A" or not title or title in seen_names:
                            continue
                        
                        # Extract data via JS for efficiency and color-based price detection
                        data_js = card.evaluate("""
                            (card) => {
                                let original = "N/A";
                                let current = "N/A";
                                let hotelType = "Hotel";
                                let availability = "Available";
                                
                                // Final Price (Orange text often rgb(255, 94, 31))
                                const allDivs = Array.from(card.querySelectorAll('div'));
                                const priceDiv = allDivs.find(d => 
                                    (d.innerText.includes('RM') || d.innerText.match(/\\d+/)) && 
                                    (window.getComputedStyle(d).color === 'rgb(255, 94, 31)' || d.className.includes('r-uh8wd5'))
                                );
                                if (priceDiv) current = priceDiv.innerText.replace('RM', '').trim();
                                
                                // Original Price (Struck through)
                                const strikeDiv = allDivs.find(d => 
                                    window.getComputedStyle(d).textDecoration.includes('line-through') ||
                                    d.className.includes('r-1q094n')
                                );
                                if (strikeDiv) original = strikeDiv.innerText.replace('RM', '').trim();
                                
                                // Hotel Type
                                if (card.innerText.includes('Apartment') || card.innerText.includes('Flat')) hotelType = "Apartment";
                                else if (card.innerText.includes('Villa')) hotelType = "Villa";
                                
                                // Availability
                                const leftMatch = card.innerText.match(/Only (\\d+) left/i);
                                if (leftMatch) availability = `Only ${leftMatch[1]} left`;
                                
                                return { original, current, hotelType, availability };
                            }
                        """)
                        
                        # Standardize prices
                        curr_str = data_js['current'].replace(',', '')
                        orig_str = data_js['original'].replace(',', '')
                        
                        curr_val = clean_price(curr_str)
                        orig_val = clean_price(orig_str)
                        price_diff = orig_val - curr_val if (orig_val > curr_val and curr_val > 0) else 0
                        
                        item = {
                            "Hotel Name": title,
                            "Location": location,
                            "District": district,
                            "Check-in Date": checkin_date,
                            "Check-out Date": checkout_date,
                            "Nights": nights,
                            "Stay Date": checkin_date,
                            "Month": month_name,
                            "Original Price": f"RM {orig_str}" if orig_val > 0 else "N/A",
                            "Discounted Price": f"RM {curr_str}" if curr_val > 0 else "N/A",
                            "Price Value": curr_val,
                            "Price Difference": f"RM {price_diff:.2f}" if price_diff > 0 else "N/A",
                            "Availability": data_js['availability'],
                            "Rooms Left": data_js['availability'],
                            "Hotel Type": data_js.get('hotelType', 'Hotel'),
                            "Platform": "Traveloka",
                            "Created At": datetime.now().strftime("%Y-%m-%d %H:%M")
                        }
                        hotels_data.append(item)
                        seen_names.add(title)
                    except Exception as e:
                        continue
                
                if len(hotels_data) >= target_count:
                    break
                
                # Scroll down
                page.evaluate("window.scrollBy(0, 1500)")
                time.sleep(2)

            if hotels_data:
                save_to_csv(hotels_data, platform="Traveloka", days_ahead=days_ahead, nights=nights, location=location)
                save_snapshot(hotels_data)
                logger.info(f"[Traveloka] Saved {len(hotels_data)} items for {location}")
            else:
                logger.warning(f"[Traveloka] No data extracted for {location}")
            
        except Exception as e:
            logger.error(f"[Traveloka] Error: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    loc = sys.argv[1] if len(sys.argv) > 1 else "Kuala Lumpur"
    scrape_traveloka(location=loc)
