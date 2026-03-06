import time
import sys
from playwright.sync_api import sync_playwright
from datetime import datetime
from utils.helpers import get_future_date, save_to_csv, get_browser_config, logger, clean_price, get_month_name, SCRAPER_CONFIG
from utils.database import save_snapshot

def scrape_booking(location="Kuala Lumpur", district="Unknown", days_ahead=28, nights=1, target_count=100, use_proxy=False, base_date=None):
    checkin_date = get_future_date(days_ahead, base_date=base_date)
    checkout_date = get_future_date(days_ahead + nights, base_date=base_date)
    month_name = get_month_name()
    
    search_location = f"{location}, Pahang, Malaysia"
    url = f"https://www.booking.com/searchresults.en-gb.html?ss={search_location}&checkin={checkin_date}&checkout={checkout_date}&group_adults=2&no_rooms=1&group_children=0"
    logger.info(f"[Booking.com] Initializing search for {search_location} ({checkin_date} to {checkout_date})")
    
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
                    logger.warning(f"[Booking.com] Retry {attempt+1} for {location} due to: {e}")
                    time.sleep(5)

            # Verification: Check if body exists
            body_exists = page.evaluate("document.body !== null")
            if not body_exists:
                logger.error(f"[Booking.com] Page body is null for {location}. Skipping.")
                return

            # Handle cookie banner
            try:
                page.get_by_role("button", name="Accept").click(timeout=5000)
            except:
                pass
            
            # Detect total properties from the page
            try:
                # Based on user snippet: <h1 ...>Pahang: 3,007 properties found</h1>
                # or <h1 aria-live="assertive" ...>
                total_text_selector = 'h1[aria-live="assertive"], h1:has-text("properties found")'
                page.wait_for_selector(total_text_selector, timeout=SCRAPER_CONFIG['selector_timeout'] * 1000)
                total_text = page.locator(total_text_selector).first.inner_text()
                
                import re
                match = re.search(r'([\d,]+)\s+(?:properties|exact matches)\s+found', total_text)
                if match:
                    detected_total = int(match.group(1).replace(',', ''))
                    target_count = min(detected_total, 3050)
                    logger.info(f"[Booking.com] Detected {detected_total} total properties. Target: {target_count}")
            except Exception as e:
                logger.warning(f"[Booking.com] Could not detect total properties count: {e}. Using target: {target_count}")

            logger.info(f"[Booking.com] Loading additional results to reach {target_count}...")
            last_count = 0
            same_count_retries = 0
            
            for i in range(400):
                # ... increment scroll
                page.evaluate("window.scrollBy(0, 5000)")
                time.sleep(0.5)
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                time.sleep(2)
                
                # ... check current count
                current_count = int(page.locator('div[data-testid="property-card"]').count())
                
                if i % 2 == 0:
                    logger.info(f"[Booking.com] Currently loaded: {current_count}/{target_count}")
                
                if current_count >= target_count:
                    logger.info(f"[Booking.com] Reached target count: {current_count}")
                    break
                
                # Check for progress
                if current_count == last_count:
                    same_count_retries = same_count_retries + 1
                    if same_count_retries > 15: # More patient retries
                        logger.warning(f"[Booking.com] Stuck at {current_count} for multiple attempts. Final check...")
                        # One last deep scroll and wait
                        page.evaluate("window.scrollTo(0, 0);")
                        time.sleep(1)
                        page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
                        time.sleep(5)
                        final_check = page.locator('div[data-testid="property-card"]').count()
                        if final_check == current_count:
                            break
                        else:
                            same_count_retries = 0
                else:
                    same_count_retries = 0
                
                last_count = current_count

            cards = page.locator('div[data-testid="property-card"]').all()
            logger.info(f"[Booking.com] Extracting {len(cards)} items...")
            
            hotels_data = []
            seen_names = set()
            
            for card in cards:
                if len(hotels_data) >= target_count:
                    break
                try:
                    # Extract Name
                    title_el = card.locator('div[data-testid="title"]')
                    title = title_el.inner_text().strip().replace('"', '') if title_el.count() > 0 else "N/A"
                    if title == "N/A" or title.isdigit() or title in seen_names: continue

                    # Get room URL for operator scraping
                    room_link_el = card.locator('a[data-testid="title-link"]').first
                    room_url = ""
                    if room_link_el.count() > 0:
                        href = room_link_el.get_attribute("href")
                        if href:
                            room_url = href.split('?')[0] if '?' in href else href
                            if not room_url.startswith('http'):
                                room_url = f"https://www.booking.com{room_url}"

                    data_js = card.evaluate("""
                        (card) => {
                            let original = "N/A";
                            let current = "N/A";
                            let bookings_recent = "0";
                            let rooms_left = "N/A";
                            let availability = "Available";

                            const divs = Array.from(card.querySelectorAll('div'));
                            const hiddenDesc = divs.find(d => d.textContent.includes('Original price') && d.textContent.includes('Current price'));
                            if (hiddenDesc) {
                                const text = hiddenDesc.textContent;
                                const origMatch = text.match(/Original price\\s*([A-Z]{3}\\s*[\\d,.]+)/);
                                const currMatch = text.match(/Current price\\s*([A-Z]{3}\\s*[\\d,.]+)/);
                                if (origMatch) original = origMatch[1].trim();
                                if (currMatch) current = currMatch[1].trim();
                            }

                            if (current === "N/A") {
                                const discountedEl = card.querySelector('[data-testid="price-and-discounted-price"]');
                                if (discountedEl) current = discountedEl.innerText.trim();
                            }

                            const cardText = card.innerText;
                            const bookedMatch = cardText.match(/(\\d+) bookings in the last 24 hours/i) || cardText.match(/Booked (\\d+) times/i);
                            if (bookedMatch) bookings_recent = bookedMatch[1];

                            const leftMatch = cardText.match(/Only (\\d+) left/i);
                            if (leftMatch) {
                                rooms_left = leftMatch[1];
                                availability = `Only ${rooms_left} left`;
                            }

                            // Detection of Type
                            let hotelType = "Hotel";
                            // Check for specific labels in the card
                            if (cardText.includes("Apartment") || cardText.includes("Entire apartment")) hotelType = "Apartment";
                            else if (cardText.includes("Villa") || cardText.includes("Entire villa")) hotelType = "Villa";
                            else if (cardText.includes("Home") || cardText.includes("Holiday home")) hotelType = "Villa/Home";
                            else if (cardText.includes("Private host") || cardText.includes("Airbnb")) hotelType = "Airbnb/Home";
                            else if (cardText.includes("Guest house") || cardText.includes("Bed and breakfast")) hotelType = "Guest House";

                            return { original, current, bookings_recent, rooms_left, availability, hotelType };
                        }
                    """)

                    # Scrape Operator Name for non-traditional hotels
                    operator = "N/A"
                    if data_js['hotelType'] != "Hotel" and room_url:
                        try:
                            # Visiting individual hotel page for host info
                            # Note: To keep it fast, we only do this for suspicious types
                            room_page = context.new_page()
                            room_page.goto(room_url, timeout=SCRAPER_CONFIG['room_page_timeout'] * 1000, wait_until="domcontentloaded")
                            room_page.wait_for_timeout(2000)
                            
                            # Different selectors for host info on Booking.com
                            host_el = room_page.locator('[id="host_name"], [data-testid="host-profile-header-name"]').first
                            if host_el.count() > 0:
                                operator = host_el.inner_text().strip()
                            else:
                                # Fallback: search for "Managed by"
                                operator = room_page.evaluate("""() => {
                                    const els = Array.from(document.querySelectorAll('div, span, p'));
                                    const hostText = els.find(e => e.innerText && e.innerText.includes('Managed by'));
                                    return hostText ? hostText.innerText.replace('Managed by', '').trim() : 'N/A';
                                }""")
                            room_page.close()
                        except:
                            try: room_page.close()
                            except: pass

                    original_price = data_js['original'].replace('\xa0', ' ')
                    discounted_price = data_js['current'].replace('\xa0', ' ')
                    orig_val = clean_price(original_price)
                    curr_val = clean_price(discounted_price)
                    price_diff = orig_val - curr_val if orig_val > 0 else 0
                    
                    item = {
                        "Hotel Name": title,
                        "Location": location,
                        "District": district,
                        "Check-in Date": checkin_date,
                        "Check-out Date": checkout_date,
                        "Nights": nights,
                        "Stay Date": checkin_date, 
                        "Month": month_name,
                        "Original Price": original_price,
                        "Discounted Price": discounted_price,
                        "Price Value": curr_val,
                        "Price Difference": f"RM {price_diff:.2f}" if price_diff > 0 else "N/A",
                        "Availability": data_js['availability'],
                        "Bookings Recent": int(data_js['bookings_recent']) if data_js['bookings_recent'].isdigit() else 0,
                        "Rooms Left": data_js['rooms_left'] if data_js['rooms_left'] != "N/A" else "Unknown",
                        "Hotel Type": data_js.get('hotelType', 'Hotel'),
                        "Operator": operator,
                        "Platform": "Booking.com",
                        "Created At": datetime.now().strftime("%Y-%m-%d %H:%M")
                    }
                    hotels_data.append(item)
                    seen_names.add(title)
                except:
                    continue
                    
            if hotels_data:
                save_to_csv(hotels_data, platform="Booking.com", days_ahead=days_ahead, nights=nights, location=location)
                save_snapshot(hotels_data)
                logger.info(f"[Booking.com] ✅ Saved {len(hotels_data)} items for {location}")
            else:
                logger.warning(f"[Booking.com] ⚠️ No data extracted for {location}")
            
        except Exception as e:
            logger.error(f"[Booking.com] Error: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    loc = sys.argv[1] if len(sys.argv) > 1 else "Kuala Lumpur"
    scrape_booking(location=loc)
