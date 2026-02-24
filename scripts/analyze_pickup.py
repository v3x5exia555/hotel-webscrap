import sqlite3
import pandas as pd
from datetime import datetime
from utils.helpers import logger
from utils.database import DB_PATH

def analyze_pickup():
    """Compares snapshots to identify inventory drops (pickups)."""
    conn = sqlite3.connect(DB_PATH)
    
    # query string without backslashes to avoid parse errors
    query = """
        SELECT hotel_name, platform, stay_date, nights, rooms_left, price, scraped_at
        FROM snapshots
        ORDER BY hotel_name, platform, stay_date, nights, scraped_at DESC
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    if df.empty:
        logger.warning("No data found in snapshots for analysis.")
        return

    pickup_results = []
    
    # Group by hotel, platform, stay_date, and nights
    grouped = df.groupby(['hotel_name', 'platform', 'stay_date', 'nights'])
    
    for (hotel, platform, stay_date, nights), group in grouped:
        if len(group) < 2:
            continue
        
        # Latest snapshot (T)
        latest = group.iloc[0]
        # Previous snapshot (T-n)
        previous = group.iloc[1]
        
        # Calculate pickup: Inventory drop
        pickup = previous['rooms_left'] - latest['rooms_left']
        
        if pickup > 0:
            # We cap it if it looks like an error (e.g. 99 -> 2)
            if previous['rooms_left'] == 99:
                pickup = 1 if latest['rooms_left'] < 5 else 0
            
            if pickup > 0:
                rev = pickup * latest['price']
                pickup_results.append({
                    "Hotel": hotel,
                    "Platform": platform,
                    "Stay Date": stay_date,
                    "Nights": nights,
                    "Pickup": pickup,
                    "Est. Revenue": rev,
                    "From": previous['scraped_at'],
                    "To": latest['scraped_at']
                })

    if pickup_results:
        res_df = pd.DataFrame(pickup_results)
        
        # Save to CSV
        output_file = f"data/pickup_analysis_{datetime.now().strftime('%Y%m%d')}.csv"
        res_df.to_csv(output_file, index=False)
        logger.info(f"Pickup analysis complete. Found {len(pickup_results)} pickups. Saved to {output_file}")
        
        # Save to Database Trends Table
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        calculation_date = datetime.now().strftime("%Y-%m-%d")
        
        save_count = 0
        for _, row in res_df.iterrows():
            try:
                # Get hotel_type from snapshots if possible
                cursor.execute("SELECT hotel_type FROM snapshots WHERE hotel_name = ? LIMIT 1", (row['Hotel'],))
                ht_res = cursor.fetchone()
                h_type = ht_res[0] if ht_res else 'Hotel'

                detected_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                cursor.execute('''
                    INSERT OR IGNORE INTO pickup_trends 
                    (hotel_name, stay_date, nights, platform, pickup_count, estimated_revenue, hotel_type, calculation_date, detected_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    row['Hotel'],
                    row['Stay Date'],
                    row['Nights'],
                    row['Platform'],
                    row['Pickup'],
                    row['Est. Revenue'],
                    h_type,
                    calculation_date,
                    detected_at
                ))
                save_count += 1
            except Exception as e:
                logger.error(f"Error saving pickup trend for {row['Hotel']}: {e}")
        
        conn.commit()
        conn.close()
        logger.info(f"Saved {save_count} pickup records to database trends.")
        
        total_rev = res_df['Est. Revenue'].sum()
        logger.info(f"Total Estimated Daily Pickup Revenue: RM {total_rev:.2f}")
    else:
        logger.info("No pickups detected in the latest snapshot comparison.")

if __name__ == "__main__":
    analyze_pickup()
