import sqlite3
import os
from datetime import datetime
from utils.helpers import logger

DB_PATH = "data/hotel_data.db"

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

def save_snapshot(data_list):
    """Saves a list of hotel data dictionaries to the database."""
    conn = sqlite3.connect(DB_PATH, timeout=60)
    cursor = conn.cursor()
    
    scraped_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
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

            cursor.execute('''
                INSERT OR IGNORE INTO snapshots (hotel_name, location, district, platform, stay_date, nights, price, rooms_left, hotel_type, scraped_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                item['Hotel Name'],
                item['Location'],
                item.get('District'),
                item['Platform'],
                stay_date,
                nights,
                price_val,
                rooms_left,
                item.get('Hotel Type', 'Hotel'),
                scraped_at
            ))
        except Exception as e:
            logger.error(f"Error saving snapshot for {item.get('Hotel Name')}: {e}")
            
    conn.commit()
    conn.close()
    logger.info(f"Saved {len(data_list)} items to database snapshots.")
