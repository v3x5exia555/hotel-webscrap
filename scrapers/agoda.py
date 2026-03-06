import time
import sys
from playwright.sync_api import sync_playwright
from datetime import datetime
from utils.helpers import get_future_date, save_to_csv, get_browser_config, logger, clean_price, get_month_name, SCRAPER_CONFIG
from utils.database import save_snapshot

def scrape_agoda(location="Kuala Lumpur", district="Unknown", city_id="14524", days_ahead=9, nights=1, target_count=100, use_proxy=False, base_date=None):
    checkin_date = get_future_date(days_ahead, base_date=base_date)
    checkout_date = get_future_date(days_ahead + nights, base_date=base_date)
    month_name = get_month_name()
    
    url = f"https://www.agoda.com/en-gb/search?city={city_id}&checkIn={checkin_date}&checkOut={checkout_date}&rooms=1&adults=2&children=0&priceCur=MYR&textToSearch={location}"
    
    logger.info(f"[Agoda] Scraping {location} ({checkin_date} to {checkout_date}, {nights} nights). Target: {target_count} hotels. Proxy: {use_proxy}")
    
    with sync_playwright() as p:
        browser_cfg = get_browser_config(use_proxy=use_proxy)
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(**browser_cfg)
        page = context.new_page()
        
        hotels_data = []
        seen_names = set()
        
        try:
            # Retry logic for navigation (from configs/config.yaml)
            max_retries = SCRAPER_CONFIG['retry']
            nav_timeout = SCRAPER_CONFIG['timeout'] * 1000  # convert seconds to ms
            for attempt in range(max_retries):
                try:
                    # Using networkidle might be slower but for Agoda's SPA it's more reliable
                    page.goto(url, timeout=nav_timeout, wait_until="networkidle")
                    break
                except Exception as e:
                    if attempt == max_retries - 1: raise e
                    logger.warning(f"[Agoda] Retry {attempt+1} for {location} due to: {e}")
                    time.sleep(5)
            
            # Verification: Check if body exists
            body_exists = page.evaluate("document.body !== null")
            if not body_exists:
                logger.error(f"[Agoda] Page body is null for {location} at {url}. Skipping.")
                return
 
            # Detect total properties from the page if possible
            try:
                # Agoda often has this text in h1, h3 or specialized data elements
                total_text_selector = 'h1, h3, [data-element-name="properties-available-text"], .SrpHeader__TotalProperties'
                page.wait_for_selector(total_text_selector, timeout=SCRAPER_CONFIG['selector_timeout'] * 1000)
                total_text = page.locator(total_text_selector).first.inner_text()
                
                import re
                match = re.search(r'([\d,]+)\s+properties', total_text)
                if match:
                    detected_total = int(match.group(1).replace(',', ''))
                    target_count = detected_total
                    logger.info(f"[Agoda] Detected {detected_total} total properties. Target: {target_count}")
            except Exception as e:
                logger.warning(f"[Agoda] Could not detect total properties count: {e}. Defaulting to: {target_count}")

            # Give SPA a moment to start rendering
            page.wait_for_timeout(5000)
            
            logger.info(f"[Agoda] Loading more results...")
            while len(hotels_data) < target_count:
                # Confirmed working selectors from live site inspection
                card_sel = '[data-selenium="hotel-item"], [aria-label="Property Card"], .PropertyCard'
                try:
                    page.wait_for_selector(card_sel, timeout=SCRAPER_CONFIG['selector_timeout'] * 1000)
                except:
                    # If we already have some data, don't break yet, try one more scroll
                    if not hotels_data:
                        break
                    else:
                        break # For now keep it as break

                # Scroll slowly to trigger lazy loading (Agoda loads data-selenium attrs on scroll)
                for _ in range(8):
                    page.keyboard.press("PageDown")
                    time.sleep(1.5)
                
                # Scroll to bottom
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                time.sleep(3)  # Extra wait for lazy-loaded attributes to populate

                cards = page.locator(card_sel).all()
                logger.info(f"[Agoda] Found {len(cards)} hotel cards on page")
                for card in cards:
                    if len(hotels_data) >= target_count:
                        break
                    try:
                        name_selectors = ['[data-selenium="hotel-name"]', 'h3', '.PropertyCard__HotelName']
                        title = "N/A"
                        for sel in name_selectors:
                            el = card.locator(sel)
                            if el.count() > 0:
                                title = el.first.inner_text().strip().replace('"', '')
                                # Ignore numeric-only names which are likely placeholders or IDs
                                if title and not title.isdigit(): break
                        
                        if title == "N/A" or not title or title.isdigit() or title in seen_names:
                            continue
                        
                        # Get room URL for operator scraping
                        room_url = ""
                        try:
                            # Agoda cards are often links themselves or have a nested link
                            href = card.get_attribute("href")
                            if not href:
                                link_el = card.locator('a').first
                                if link_el.count() > 0:
                                    href = link_el.get_attribute("href")
                            
                            if href:
                                if href.startswith('http'):
                                    room_url = href.split('?')[0]
                                else:
                                    room_url = f"https://www.agoda.com{href.split('?')[0]}"
                        except: pass

                        data_js = card.evaluate("""
                            (card) => {
                                let original = "N/A";
                                let current = "N/A";
                                let availability = "Available";
                                let bookings_today = "0";
                                let rooms_left = "N/A";
                                
                                const priceSelectors = ['[data-selenium="display-price"]', '.PropertyCard__Price', '.pd-price'];
                                for (let sel of priceSelectors) {
                                    let el = card.querySelector(sel);
                                    if (el && el.innerText.trim()) { current = el.innerText.trim(); break; }
                                }
                                
                                const strikeEl = card.querySelector('[data-selenium="strikeout-price"], .PropertyCard__OldPrice');
                                if (strikeEl) original = strikeEl.innerText.trim();

                                const allTexts = card.innerText;
                                const bookedMatch = allTexts.match(/Booked (\\d+) times today/i);
                                if (bookedMatch) bookings_today = bookedMatch[1];
                                const leftMatch = allTexts.match(/ONLY (\\d+) LEFT/i);
                                if (leftMatch) rooms_left = leftMatch[1];

                                // Detection of Type
                                let hotelType = "Hotel";
                                const cardText = card.innerText;
                                if (cardText.includes("Apartment") || cardText.includes("Flat")) hotelType = "Apartment";
                                else if (cardText.includes("Villa") || cardText.includes("Holiday Home")) hotelType = "Villa";
                                else if (cardText.includes("Guest house") || cardText.includes("Explore Entire")) hotelType = "Guest House";
                                else if (cardText.includes("Private home")) hotelType = "Airbnb/Home";

                                return { original, current, bookings_today, rooms_left, hotelType };
                            }
                        """)
                        
                        # Scrape Operator Name for home-like properties
                        operator = "N/A"
                        if data_js['hotelType'] != "Hotel" and room_url:
                            try:
                                room_page = context.new_page()
                                room_page.goto(room_url, timeout=SCRAPER_CONFIG['room_page_timeout'] * 1000, wait_until="domcontentloaded")
                                room_page.wait_for_timeout(2000)
                                
                                # Agoda host selectors
                                operator = room_page.evaluate("""() => {
                                    // Look for host name in specific sections
                                    const hostEl = document.querySelector('[data-selenium="host-name"], .HostInfo__Name');
                                    if (hostEl) return hostEl.innerText.trim();
                                    
                                    // Alternative: look for "Managed by"
                                    const allText = document.body.innerText;
                                    const managedMatch = allText.match(/Managed by\\s*([^\\n.]+)/i);
                                    return managedMatch ? managedMatch[1].trim() : 'N/A';
                                }""")
                                room_page.close()
                            except:
                                try: room_page.close()
                                except: pass

                        orig_val = clean_price(data_js['original'])
                        curr_val = clean_price(data_js['current'])
                        price_diff = orig_val - curr_val if (orig_val > 0 and curr_val > 0) else 0
                        
                        item = {
                            "Hotel Name": title,
                            "Location": location,
                            "District": district,
                            "Check-in Date": checkin_date,
                            "Check-out Date": checkout_date,
                            "Nights": nights,
                            "Stay Date": checkin_date, 
                            "Month": month_name,
                            "Original Price": data_js['original'],
                            "Discounted Price": data_js['current'],
                            "Price Value": curr_val,
                            "Price Difference": f"RM {price_diff:.2f}" if price_diff > 0 else "N/A",
                            "Availability": f"Only {data_js['rooms_left']} left" if data_js['rooms_left'] != "N/A" else "Available",
                            "Bookings Today": int(data_js['bookings_today']) if data_js['bookings_today'].isdigit() else 0,
                            "Rooms Left": data_js['rooms_left'] if data_js['rooms_left'] != "N/A" else "Unknown",
                            "Hotel Type": data_js['hotelType'],
                            "Operator": operator,
                            "Platform": "Agoda",
                            "Created At": datetime.now().strftime("%Y-%m-%d %H:%M")
                        }
                        hotels_data.append(item)
                        seen_names.add(title)
                    except:
                        continue
                
                if len(hotels_data) >= target_count:
                    break
                
                next_btn = page.locator('#paginationNext')
                if next_btn.is_visible(timeout=5000):
                    next_btn.click()
                    time.sleep(5)
                else:
                    break
                    
            if hotels_data:
                save_to_csv(hotels_data, platform="Agoda", days_ahead=days_ahead, nights=nights, location=location)
                save_snapshot(hotels_data)
                logger.info(f"[Agoda] ✅ Saved {len(hotels_data)} items for {location}")
            else:
                logger.warning(f"[Agoda] ⚠️ No data extracted for {location}")
                
        except Exception as e:
            logger.error(f"[Agoda] Error: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    loc = sys.argv[1] if len(sys.argv) > 1 else "Kuala Lumpur"
    cid = sys.argv[2] if len(sys.argv) > 2 else "14524"
    scrape_agoda(location=loc, city_id=cid)
