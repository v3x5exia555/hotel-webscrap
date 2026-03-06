import os
import sys
import logging
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def setup_supabase():
    """Provides instructions and SQL for initializing the Supabase database."""
    load_dotenv()
    
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    
    if not url or not key:
        logger.error("❌ SUPABASE_URL or SUPABASE_KEY not found in .env file.")
        return

    print("="*60)
    print("🚀 SUPABASE INITIALIZATION GUIDE")
    print("="*60)
    print("\n1. Go to your Supabase Dashboard:")
    print(f"   {url.replace('.supabase.co', '.supabase.com')}")
    print("\n2. Open the 'SQL Editor' from the left sidebar.")
    print("\n3. Click 'New Query' and paste the following SQL block:")
    print("\n" + "-"*20 + " SQL START " + "-"*20)
    print("""
-- 1. Create the snapshots table
CREATE TABLE IF NOT EXISTS snapshots (
    id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    hotel_name TEXT,
    location TEXT,
    district TEXT,
    platform TEXT,
    stay_date DATE,
    nights INTEGER DEFAULT 1,
    price REAL,
    rooms_left INTEGER,
    hotel_type TEXT DEFAULT 'Hotel',
    operator TEXT,
    scraped_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(hotel_name, platform, stay_date, nights, scraped_at)
);

-- 2. Create the pickup_trends table
CREATE TABLE IF NOT EXISTS pickup_trends (
    id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    hotel_name TEXT,
    stay_date DATE,
    nights INTEGER DEFAULT 1,
    platform TEXT,
    district TEXT,
    pickup_count INTEGER,
    estimated_revenue REAL,
    hotel_type TEXT DEFAULT 'Hotel',
    calculation_date TEXT,
    detected_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(hotel_name, stay_date, nights, platform, calculation_date, detected_at)
);

-- 3. Add performance indexes
CREATE INDEX IF NOT EXISTS idx_snapshots_scraped_at ON snapshots (scraped_at);
CREATE INDEX IF NOT EXISTS idx_snapshots_stay_date ON snapshots (stay_date);
CREATE INDEX IF NOT EXISTS idx_trends_detected_at ON pickup_trends (detected_at);
""")
    print("-"*20 + " SQL END " + "-"*20)
    print("\n4. Click 'Run'.")
    print("\n5. Once finished, run the test script to verify:")
    print("   python3 test_supabase.py")
    print("\n" + "="*60)

if __name__ == "__main__":
    setup_supabase()
