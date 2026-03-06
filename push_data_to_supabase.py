import os
import sqlite3
import pandas as pd
try:
    from supabase import create_client, Client
except ImportError:
    from supabase_py import create_client, Client # Fallback for older versions if any

from dotenv import load_dotenv
import logging
import hashlib
import numpy as np

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def sync_data():
    load_dotenv()
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    
    if not url or not key:
        logger.error("❌ SUPABASE_URL or SUPABASE_KEY missing in .env")
        return

    supabase: Client = create_client(url, key)
    
    # Path to local database — resolve relative to this script's location
    project_root = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(project_root, "data", "hotel_data.db")

    if not os.path.exists(db_path):
        logger.error(f"❌ Local database not found at {db_path}")
        return

    logger.info(f"Reading data from {db_path}...")
    
    try:
        conn = sqlite3.connect(db_path)
        
        # Tables to sync
        tables = ["snapshots", "pickup_trends"]
        
        for table_name in tables:
            cursor = conn.cursor()
            # Optimization: Only sync data from the last 2 days to avoid duplicate key errors on historical records
            date_col = "scraped_at" if table_name == "snapshots" else "detected_at"
            sync_query = f"SELECT * FROM {table_name} WHERE date({date_col}) >= date('now', '-2 days')"
            
            df_full = pd.read_sql_query(sync_query, conn)
            total_records = len(df_full)
            logger.info(f"📊 Table '{table_name}': Found {total_records:,} recent records to sync.")
            
            if df_full.empty:
                continue

            # Fetch and upload in large batches
            batch_size = 5000 
            for offset in range(0, total_records, batch_size):
                df = df_full.iloc[offset : offset + batch_size]

                
                if df.empty:
                    continue

                # Fix NaN values
                df = df.replace({np.nan: None, np.inf: None, -np.inf: None})
                
                # Clean records and generate custom ID as requested
                def clean_record(row_tuple):
                    index, r = row_tuple
                    cleaned = {}
                    for k, v in r.items():
                        if pd.isna(v): cleaned[k] = None
                        elif k in ['nights', 'rooms_left', 'pickup_count'] and v is not None:
                            try: cleaned[k] = int(float(v))
                            except: cleaned[k] = None
                        else: cleaned[k] = v
                    
                    # USER REQUEST: Update ID with hash(session) + index/unique_string
                    # We use a deterministic hash of the natural key to serve as the stable ID
                    if table_name == "snapshots":
                        # Composite key for snapshots
                        natural_key = f"{r.get('hotel_name')}_{r.get('platform')}_{r.get('stay_date')}_{r.get('nights')}_{r.get('scraped_at')}"
                    else:
                        # Composite key for pickup_trends
                        natural_key = f"{r.get('hotel_name')}_{r.get('stay_date')}_{r.get('nights')}_{r.get('platform')}_{r.get('calculation_date')}_{r.get('detected_at')}"
                    
                    # Generate stable 32-char hex ID
                    cleaned['id'] = hashlib.md5(natural_key.encode()).hexdigest()
                    
                    return cleaned
                
                records = [clean_record(item) for item in df.iterrows()]
                
                # Upload to Supabase in smaller API chunks
                api_chunk_size = 100
                logger.info(f"🚀 Uploading batch {offset//batch_size + 1} ({len(records)} records) for '{table_name}'...")
                
                for j in range(0, len(records), api_chunk_size):
                    chunk = records[j:j+api_chunk_size]
                    try:
                        schema_name = os.environ.get("SUPABASE_SCHEMA", "analysis_hotel")
                        
                        # Use the new varchar 'id' for conflict resolution
                        supabase.schema(schema_name).table(table_name).upsert(chunk, on_conflict="id").execute()
                    except Exception as e:
                        logger.error(f"❌ Failed to upload chunk at offset {offset+j} in {table_name}: {e}")

                        # Don't break entirely, try next chunk
                
                logger.info(f"✅ Progress for '{table_name}': {min(offset + batch_size, total_records):,}/{total_records:,}")

        conn.close()
        logger.info("✨ Full sync to Supabase completed successfully!")
                
    except Exception as e:
        logger.error(f"❌ Error during sync: {e}")

if __name__ == "__main__":
    sync_data()
