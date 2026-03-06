import time
import sys
import os
from playwright.sync_api import sync_playwright
from datetime import datetime

# Add the parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.helpers import get_future_date, save_to_csv, get_browser_config, logger, clean_price, get_month_name, SCRAPER_CONFIG
from utils.database import save_snapshot

def scrape_airbnb(location="Kuala Lumpur", district="Unknown", days_ahead=28, nights=1, target_count=100, use_proxy=False, base_date=None):
    checkin_date = get_future_date(days_ahead, base_date=base_date)
    checkout_date = get_future_date(days_ahead + nights, base_date=base_date)
    month_name = get_month_name()
    
    # Airbnb URL structure
    search_location = f"{location}, Malaysia"
    url = f"https://www.airbnb.com/s/{search_location.replace(' ', '-')}/homes?checkin={checkin_date}&checkout={checkout_date}&adults=2"
    
    logger.info(f"[Airbnb] Initializing search for {search_location} ({checkin_date} to {checkout_date})")
    
    with sync_playwright() as p:
        browser_cfg = get_browser_config(use_proxy=use_proxy)
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(**browser_cfg)
        page = context.new_page()
        
        try:
            # Retry logic for navigation (from configs/config.yaml)
            max_retries = SCRAPER_CONFIG['retry']
            nav_timeout = SCRAPER_CONFIG['timeout'] * 1000  # convert seconds to ms
            for attempt in range(max_retries):
                try:
                    page.goto(url, timeout=nav_timeout, wait_until="domcontentloaded")
                    break
                except Exception as e:
                    if attempt == max_retries - 1: raise e
                    logger.warning(f"[Airbnb] Retry {attempt+1} for {location} due to: {e}")
                    time.sleep(5)

            # Handle cookie banner / translation dialogs
            try:
                page.locator('button:has-text("Accept"), button:has-text("OK")').first.click(timeout=5000)
            except:
                pass
            
            # Close translation dialog if it appears
            try:
                page.locator('button[aria-label="Close"]').first.click(timeout=3000)
            except:
                pass

            logger.info(f"[Airbnb] Loading results for {location}...")
            
            # Airbnb often uses lazy loading or pagination. 
            # We'll scroll and then look for the "Next" button if needed.
            hotels_data = []
            seen_names = set()
            
            for page_num in range(5): # Limit to 5 pages of results
                # Scroll to load all cards on the current page
                for _ in range(5):
                    page.evaluate("window.scrollBy(0, 1000)")
                    time.sleep(0.5)
                
                # Extract cards
                cards = page.locator('[data-testid="card-container"]').all()
                logger.info(f"[Airbnb] Found {len(cards)} property cards on page {page_num + 1}")
                
                for card in cards:
                    if len(hotels_data) >= target_count:
                        break
                    try:
                        # Extract Name
                        title_el = card.locator('[id^="title_"]')
                        title = title_el.inner_text().strip().replace('"', '') if title_el.count() > 0 else "N/A"
                        
                        if title == "N/A" or title in seen_names:
                            continue
                        
                        # Get room URL for operator scraping
                        room_link_el = card.locator('a[href*="/rooms/"]').first
                        room_url = ""
                        if room_link_el.count() > 0:
                            href = room_link_el.get_attribute("href")
                            if href:
                                room_url = f"https://www.airbnb.com{href.split('?')[0]}"
                            
                        # Extract Price and Type using JS for efficiency
                        data_js = card.evaluate("""
                            (card) => {
                                let price_str = "N/A";
                                let hotelType = "Airbnb";
                                let rating = "N/A";
                                
                                // Price - Look for common price class or data-testid
                                const priceEl = card.querySelector('[data-testid="price-item"] span, ._ty6370, ._1jo4hgw');
                                if (priceEl) price_str = priceEl.innerText;
                                
                                // Property Type - Usually a div with a specific class
                                const typeEl = card.querySelector('.t1jau9vc');
                                if (typeEl) hotelType = typeEl.innerText;
                                
                                // Rating
                                const ratingEl = card.querySelector('.r1dx987b');
                                if (ratingEl) rating = ratingEl.innerText;
                                
                                return { price_str, hotelType, rating };
                            }
                        """)

                        # Scrape Operator Name
                        operator = "N/A"
                        # Try to get from card first (some subtitles contain 'Stay with [Name]' or 'Hosted by')
                        try:
                            card_subtitles = card.locator('[data-testid="listing-card-subtitle"]').all_inner_texts()
                            for sub in card_subtitles:
                                if "Stay with" in sub:
                                    operator = sub.replace("Stay with", "").strip()
                                    break
                                if "Hosted by" in sub:
                                    operator = sub.replace("Hosted by", "").strip()
                                    break
                        except: pass

                        if operator == "N/A" and room_url:
                            try:
                                logger.info(f"[Airbnb] Visiting room page for operator: {title}")
                                room_page = context.new_page()
                                room_page.goto(room_url, timeout=SCRAPER_CONFIG['room_page_timeout'] * 1000, wait_until="domcontentloaded")
                                room_page.wait_for_timeout(3000)
                                # Search for host name in common elements
                                operator = room_page.evaluate("""() => {
                                    const hostEl = Array.from(document.querySelectorAll('div, h2, h3, span')).find(e => e.innerText && e.innerText.includes('Hosted by'));
                                    if (hostEl) {
                                        const text = hostEl.innerText;
                                        return text.split('Hosted by')[1].split('\\n')[0].trim();
                                    }
                                    return 'N/A';
                                }""")
                                room_page.close()
                            except Exception as e:
                                logger.warning(f"[Airbnb] Failed to get operator for {title}: {e}")
                                try: room_page.close() 
                                except: pass
                        
                        price_val = clean_price(data_js['price_str'])
                        
                        item = {
                            "Hotel Name": title,
                            "Location": location,
                            "District": district,
                            "Check-in Date": checkin_date,
                            "Check-out Date": checkout_date,
                            "Nights": nights,
                            "Stay Date": checkin_date,
                            "Month": month_name,
                            "Original Price": "N/A", 
                            "Discounted Price": data_js['price_str'],
                            "Price Value": price_val,
                            "Price Difference": "N/A",
                            "Availability": "Available",
                            "Bookings Recent": 0,
                            "Rooms Left": "Unknown",
                            "Hotel Type": data_js['hotelType'] if data_js['hotelType'] else "Home/Airbnb",
                            "Platform": "Airbnb",
                            "Operator": operator,
                            "Created At": datetime.now().strftime("%Y-%m-%d %H:%M"),
                            "Rating": data_js['rating']
                        }
                        
                        hotels_data.append(item)
                        seen_names.add(title)
                    except Exception as e:
                        logger.error(f"[Airbnb] Card error: {e}")
                        continue
                
                if len(hotels_data) >= target_count:
                    break
                    
                # Try to go to next page
                try:
                    next_btn = page.locator('a[aria-label="Next"]').first
                    if next_btn.is_visible(timeout=5000):
                        next_btn.click()
                        time.sleep(3)
                    else:
                        break
                except:
                    break
            
            if hotels_data:
                save_to_csv(hotels_data, platform="Airbnb", days_ahead=days_ahead, nights=nights, location=location)
                save_snapshot(hotels_data)
                
        except Exception as e:
            logger.error(f"[Airbnb] Scraper Error: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    loc = sys.argv[1] if len(sys.argv) > 1 else "Kuala Lumpur"
    scrape_airbnb(location=loc)
