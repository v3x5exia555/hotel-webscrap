import os
import sqlite3
import pandas as pd
from supabase import create_client, Client
from dotenv import load_dotenv
import logging

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
            cursor.execute(f"SELECT count(*) FROM {table_name}")
            total_count = cursor.fetchone()[0]
            logger.info(f"📊 Table '{table_name}': Found {total_count:,} total records.")
            
            # Fetch and upload in large batches from SQLite
            batch_size = 5000 
            for offset in range(0, total_count, batch_size):
                df = pd.read_sql_query(f"SELECT * FROM {table_name} LIMIT {batch_size} OFFSET {offset}", conn)
                
                if df.empty:
                    continue

                # Fix NaN values
                import numpy as np
                df = df.replace({np.nan: None, np.inf: None, -np.inf: None})
                
                records = df.to_dict('records')
                
                # Clean records
                def clean_record(r):
                    cleaned = {}
                    for k, v in r.items():
                        if pd.isna(v): cleaned[k] = None
                        elif k in ['nights', 'rooms_left', 'pickup_count'] and v is not None:
                            try: cleaned[k] = int(float(v))
                            except: cleaned[k] = None
                        else: cleaned[k] = v
                    if 'id' in cleaned: del cleaned['id']
                    return cleaned
                
                records = [clean_record(r) for r in records]
                
                # Upload to Supabase in smaller API chunks
                api_chunk_size = 100
                logger.info(f"🚀 Uploading batch {offset//batch_size + 1} ({len(records)} records) for '{table_name}'...")
                
                for j in range(0, len(records), api_chunk_size):
                    chunk = records[j:j+api_chunk_size]
                    try:
                        schema_name = os.environ.get("SUPABASE_SCHEMA", "analysis_hotel")
                        supabase.schema(schema_name).table(table_name).upsert(chunk).execute()
                    except Exception as e:
                        logger.error(f"❌ Failed to upload chunk at offset {offset+j} in {table_name}: {e}")
                        # Don't break entirely, try next chunk
                
                logger.info(f"✅ Progress for '{table_name}': {min(offset + batch_size, total_count):,}/{total_count:,}")

        conn.close()
        logger.info("✨ Full sync to Supabase completed successfully!")
                
    except Exception as e:
        logger.error(f"❌ Error during sync: {e}")

if __name__ == "__main__":
    sync_data()
