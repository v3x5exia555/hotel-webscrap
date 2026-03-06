import sqlite3
import pandas as pd
from datetime import datetime
from utils.helpers import logger
from utils.database import DB_PATH, get_supabase_client, get_supabase_table, fetch_data_from_db

def analyze_pickup():
    """Compares snapshots to identify inventory drops (pickups)."""
    logger.info("Fetching snapshots for pickup analysis...")
    # Fetch snapshots from last 3 days to compare (pickup is usually quick)
    df = fetch_data_from_db("snapshots", days=3, limit=50000)
    
    if df is None or df.empty:
        logger.warning("No data found in snapshots for analysis.")
        return

    # Sort for temporal comparison: DESC scraped_at
    if 'scraped_at' in df.columns:
        df = df.sort_values(['hotel_name', 'platform', 'stay_date', 'nights', 'scraped_at'], ascending=[True, True, True, True, False])

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
        try:
            prev_rooms = int(previous['rooms_left']) if pd.notna(previous['rooms_left']) else 0
            curr_rooms = int(latest['rooms_left']) if pd.notna(latest['rooms_left']) else 0
            pickup = prev_rooms - curr_rooms
        except:
            pickup = 0
        
        if pickup > 0:
            # We cap it if it looks like an error (e.g. 99 -> 2)
            if prev_rooms == 99:
                pickup = 1 if curr_rooms < 5 else 0
            
            if pickup > 0:
                price_val = float(latest['price'] if pd.notna(latest['price']) else 0)
                rev = pickup * price_val
                pickup_results.append({
                    "Hotel": hotel,
                    "Platform": platform,
                    "Stay Date": stay_date,
                    "Nights": int(nights),
                    "Pickup": int(pickup),
                    "Est. Revenue": float(rev),
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
        detected_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        supabase_records = []
        save_count = 0
        
        for _, row in res_df.iterrows():
            try:
                h_type = 'Hotel'
                cursor.execute('''
                    INSERT OR IGNORE INTO pickup_trends 
                    (hotel_name, stay_date, nights, platform, pickup_count, estimated_revenue, hotel_type, calculation_date, detected_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    row['Hotel'],
                    row['Stay Date'],
                    int(row['Nights']),
                    row['Platform'],
                    int(row['Pickup']),
                    float(row['Est. Revenue']),
                    h_type,
                    calculation_date,
                    detected_at
                ))
                
                supabase_records.append({
                    "hotel_name": row['Hotel'],
                    "stay_date": row['Stay Date'],
                    "nights": int(row['Nights']),
                    "platform": row['Platform'],
                    "pickup_count": int(row['Pickup']),
                    "estimated_revenue": float(row['Est. Revenue']),
                    "hotel_type": h_type,
                    "calculation_date": calculation_date,
                    "detected_at": detected_at
                })
                save_count += 1
            except Exception as e:
                logger.error(f"Error saving pickup trend for {row['Hotel']}: {e}")
        
        conn.commit()
        conn.close()
        logger.info(f"Saved {save_count} pickup records to SQLite.")

        # Sync to Supabase
        table = get_supabase_table("pickup_trends")
        if table and supabase_records:
            try:
                # Upload in chunks
                for i in range(0, len(supabase_records), 100):
                    chunk = supabase_records[i:i+100]
                    table.upsert(chunk).execute()
                logger.info(f"✅ Successfully synced {len(supabase_records)} pickup records to Supabase.")
            except Exception as e:
                logger.error(f"Failed to sync pickups to Supabase: {e}")
        
        total_rev = res_df['Est. Revenue'].sum()
        logger.info(f"Total Estimated Daily Pickup Revenue: RM {total_rev:.2f}")
    else:
        logger.info("No pickups detected in the latest snapshot comparison.")

if __name__ == "__main__":
    analyze_pickup()
