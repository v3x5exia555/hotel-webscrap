import sqlite3
import os
import pandas as pd
from datetime import datetime
from utils.helpers import logger

# Supabase imports
try:
    from supabase import create_client, Client
    SUPABASE_ENABLED = True
except ImportError:
    SUPABASE_ENABLED = False

DB_PATH = "data/hotel_data.db"
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
SUPABASE_SCHEMA = os.environ.get("SUPABASE_SCHEMA", "analysis_hotel")

_supabase_client = None

def get_supabase_client():
    global _supabase_client
    if not SUPABASE_ENABLED or not SUPABASE_URL or not SUPABASE_KEY:
        return None
    if _supabase_client is None:
        try:
            from supabase import create_client
            _supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
        except Exception as e:
            logger.error(f"Failed to initialize Supabase client: {e}")
    return _supabase_client

def get_supabase_table(table_name):
    client = get_supabase_client()
    if not client:
        return None
    return client.schema(SUPABASE_SCHEMA).table(table_name)

def fetch_data_from_db(table_name, days=None, limit=None):
    """Generic fetcher that prefers Supabase, then falls back to SQLite."""
    supabase = get_supabase_client()
    df = None
    
    table = get_supabase_table(table_name)
    if table:
        try:
            query = table.select("*")
            if days:
                from datetime import timedelta
                since = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
                date_col = "scraped_at" if table_name == "snapshots" else "detected_at"
                query = query.gte(date_col, since)
            
            if limit:
                query = query.limit(limit)
                
            res = query.execute()
            df = pd.DataFrame(res.data)
            if not df.empty:
                logger.info(f"✓ Fetched {len(df)} records from Supabase {table_name}")
                return df
        except Exception as e:
            logger.warning(f"Supabase fetch failed for {table_name}, falling back to SQLite: {e}")

    # SQLite Fallback
    if os.path.exists(DB_PATH):
        try:
            conn = sqlite3.connect(DB_PATH, timeout=30)
            sql = f"SELECT * FROM {table_name}"
            conditions = []
            if days:
                date_col = "scraped_at" if table_name == "snapshots" else "detected_at"
                conditions.append(f"DATE({date_col}) >= DATE('now', '-{days} days')")
            
            if conditions:
                sql += " WHERE " + " AND ".join(conditions)
            
            sql += " ORDER BY " + ("scraped_at" if table_name == "snapshots" else "detected_at") + " DESC"
            
            if limit:
                sql += f" LIMIT {limit}"
                
            df = pd.read_sql_query(sql, conn)
            conn.close()
            logger.info(f"✓ Fetched {len(df)} records from SQLite {table_name}")
            return df
        except Exception as e:
            logger.error(f"SQLite fetch failed for {table_name}: {e}")
            
    return pd.DataFrame()

def init_db():
    """Initializes the SQLite database with the necessary tables."""
    if not os.path.exists("data"):
        os.makedirs("data")
    
    conn = sqlite3.connect(DB_PATH, timeout=60)
    cursor = conn.cursor()
    # Enable WAL mode for better concurrency
    cursor.execute('PRAGMA journal_mode=WAL')
    
    # Snapshot table to store daily scrapes
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hotel_name TEXT,
            location TEXT,
            district TEXT,
            platform TEXT,
            stay_date TEXT,
            nights INTEGER DEFAULT 1,
            price REAL,
            rooms_left INTEGER,
            hotel_type TEXT DEFAULT 'Hotel',
            operator TEXT,
            scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(hotel_name, platform, stay_date, nights, scraped_at)
        )
    ''')
    
    # Summary table for daily pickup trends
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pickup_trends (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hotel_name TEXT,
            stay_date TEXT,
            nights INTEGER DEFAULT 1,
            platform TEXT,
            district TEXT,
            pickup_count INTEGER,
            estimated_revenue REAL,
            hotel_type TEXT DEFAULT 'Hotel',
            calculation_date TEXT,
            detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(hotel_name, stay_date, nights, platform, calculation_date, detected_at)
        )
    ''')

    # Migration: Add columns if they don't exist
    columns_to_add = [
        ("snapshots", "hotel_type", "TEXT DEFAULT 'Hotel'"),
        ("snapshots", "nights", "INTEGER DEFAULT 1"),
        ("snapshots", "district", "TEXT"),
        ("snapshots", "operator", "TEXT"),
        ("pickup_trends", "hotel_type", "TEXT DEFAULT 'Hotel'"),
        ("pickup_trends", "nights", "INTEGER DEFAULT 1"),
        ("pickup_trends", "district", "TEXT"),
        ("pickup_trends", "detected_at", "TEXT")
    ]
    
    for table, col, type_def in columns_to_add:
        try:
            cursor.execute(f"SELECT {col} FROM {table} LIMIT 1")
        except sqlite3.OperationalError:
            logger.info(f"Migrating database: Adding {col} to {table}")
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {col} {type_def}")
    
    conn.commit()
    conn.close()
    logger.info(f"Database initialized at {DB_PATH}")

def save_snapshot(data_list, batch_size=500):
    """Saves a list of hotel data dictionaries to the database with batch optimization.
    
    Batches inserts to reduce I/O overhead and improve performance.
    """
    if not data_list:
        return
    
    conn = sqlite3.connect(DB_PATH, timeout=60)
    cursor = conn.cursor()
    
    scraped_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Prepare batch data
    batch_data = []
    
    for item in data_list:
        try:
            # We assume 'stay_date' is passed in the item, or we use a default
            stay_date = item.get('Stay Date', datetime.now().strftime("%Y-%m-%d"))
            nights = item.get('Nights', 1)
            
            # Convert rooms_left to int, handle N/A and Unknown
            rooms_left_raw = item.get('Rooms Left', 'N/A')
            rooms_left = None
            if isinstance(rooms_left_raw, int):
                rooms_left = rooms_left_raw
            elif str(rooms_left_raw).isdigit():
                rooms_left = int(rooms_left_raw)

            # Price value extraction
            price_val = 0.0
            if 'Price Value' in item:
                price_val = item['Price Value']
            elif 'Discounted Price' in item:
                from utils.helpers import clean_price
                price_val = clean_price(item['Discounted Price'])

            batch_data.append((
                item['Hotel Name'],
                item['Location'],
                item.get('District'),
                item['Platform'],
                stay_date,
                nights,
                price_val,
                rooms_left,
                item.get('Hotel Type', 'Hotel'),
                item.get('Operator'),
                scraped_at
            ))
        except Exception as e:
            logger.error(f"Error preparing snapshot for {item.get('Hotel Name')}: {e}")
    
    # Batch insert: execute in chunks to reduce memory and I/O overhead
    if batch_data:
        for i in range(0, len(batch_data), batch_size):
            batch = batch_data[i:i+batch_size]
            try:
                cursor.executemany('''
                    INSERT OR IGNORE INTO snapshots (hotel_name, location, district, platform, stay_date, nights, price, rooms_left, hotel_type, operator, scraped_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', batch)
                conn.commit()
                logger.info(f"[Batch {i//batch_size + 1}] Inserted {len(batch)} records ({i}/{len(batch_data)})")
            except Exception as e:
                logger.error(f"Error during batch insert: {e}")
                conn.rollback()
    
    conn.close()
    logger.info(f"✓ Batch save complete: {len(data_list)} items to SQLite database snapshots.")

    # Supabase upload
    supabase = get_supabase_client()
    if supabase:
        try:
            # Prepare data for Supabase (CamelCase to snake_case if necessary, or keep as defined in table)
            # The SQLite table uses: hotel_name, location, district, platform, stay_date, nights, price, rooms_left, hotel_type, operator, scraped_at
            supabase_data = []
            for item in batch_data:
                supabase_data.append({
                    "hotel_name": item[0],
                    "location": item[1],
                    "district": item[2],
                    "platform": item[3],
                    "stay_date": item[4],
                    "nights": item[5],
                    "price": item[6],
                    "rooms_left": item[7],
                    "hotel_type": item[8],
                    "operator": item[9],
                    "scraped_at": item[10]
                })
            
            # Use helper to handle schema
            table = get_supabase_table("snapshots")
            if table:
                response = table.upsert(supabase_data).execute()
                logger.info(f"✓ Successfully synced {len(supabase_data)} records to Supabase.")
        except Exception as e:
            logger.error(f"Failed to sync data to Supabase: {e}")
