#!/usr/bin/env python3
"""
analysis_helper.py - Data Analysis & Validation Helper
Ensures all data is properly loaded, transformed, and ready for dashboard
"""

import sqlite3
import pandas as pd
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add parent dir to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.helpers import logger
from utils.database import DB_PATH, get_supabase_client, get_supabase_table

def analyze_snapshots():
    """Analyze snapshots table"""
    print("\n" + "="*70)
    print("📊 SNAPSHOTS TABLE ANALYSIS")
    print("="*70)
    
    supabase = get_supabase_client()
    df = None
    if supabase:
        try:
            print("  Fetching from Supabase...")
            res = supabase.table("snapshots").select("*").execute()
            df = pd.DataFrame(res.data)
        except Exception as e:
            print(f"  Supabase error, falling back to SQLite: {e}")

    if df is None:
        conn = sqlite3.connect(DB_PATH, timeout=30)
        df = pd.read_sql_query("SELECT * FROM snapshots", conn)
        conn.close()

    total = len(df)
    print(f"✓ Total records: {total:,}")
    
    hotels = df['hotel_name'].nunique()
    print(f"✓ Unique properties: {hotels:,}")
    
    platforms = df['platform'].nunique()
    print(f"✓ Unique platforms: {platforms}")
    
    plats = sorted(df['platform'].unique())
    print(f"  Platforms: {', '.join(plats)}")
    
    # Data quality
    null_price = df['price'].isna().sum()
    print(f"⚠️  Null prices: {null_price:,} ({100*null_price/total:.1f}%)")
    
    null_rooms = df['rooms_left'].isna().sum()
    print(f"⚠️  Null inventory: {null_rooms:,} ({100*null_rooms/total:.1f}%)")
    
    null_dist = df['district'].isna().sum()
    print(f"⚠️  Null districts: {null_dist:,} ({100*null_dist/total:.1f}%)")
    
    # Recency
    latest = df['scraped_at'].max()
    print(f"✓ Latest data: {latest}")
    
    oldest = df['scraped_at'].min()
    print(f"✓ Oldest data: {oldest}")
    
    # Coverage
    dates = pd.to_datetime(df['stay_date']).dt.date.nunique()
    print(f"✓ Unique stay dates covered: {dates:,}")

def analyze_pickup_trends():
    """Analyze pickup trends"""
    print("\n" + "="*70)
    print("📈 PICKUP TRENDS TABLE ANALYSIS")
    print("="*70)
    
    supabase = get_supabase_client()
    df = None
    if supabase:
        try:
            print("  Fetching from Supabase...")
            res = supabase.table("pickup_trends").select("*").execute()
            df = pd.DataFrame(res.data)
        except Exception as e:
            print(f"  Supabase error, falling back to SQLite: {e}")

    if df is None:
        conn = sqlite3.connect(DB_PATH, timeout=30)
        df = pd.read_sql_query("SELECT * FROM pickup_trends", conn)
        conn.close()

    total = len(df)
    print(f"✓ Total records: {total:,}")
    
    total_pickups = df['pickup_count'].sum()
    print(f"✓ Total pickups detected: {total_pickups:,}")
    
    total_revenue = df['estimated_revenue'].sum()
    print(f"✓ Total estimated revenue: RM{total_revenue:,.2f}")
    
    latest = df['detected_at'].max()
    print(f"✓ Latest analysis: {latest}")

def analyze_location_distribution():
    """Analyze geographic distribution"""
    print("\n" + "="*70)
    print("🗺️  LOCATION DISTRIBUTION")
    print("="*70)
    
    supabase = get_supabase_client()
    df = None
    if supabase:
        try:
            print("  Fetching from Supabase...")
            res = supabase.table("snapshots").select("district").execute()
            df = pd.DataFrame(res.data)
        except Exception as e:
            print(f"  Supabase error, falling back to SQLite: {e}")

    if df is None:
        conn = sqlite3.connect(DB_PATH, timeout=30)
        df = pd.read_sql_query("SELECT district FROM snapshots", conn)
        conn.close()

    dist_counts = df['district'].value_counts().head(10)
    
    print("\nTop 10 districts by record count:")
    for i, (dist, count) in enumerate(dist_counts.items()):
        print(f"  {i+1}. {dist}: {count:,} records")

def analyze_platform_distribution():
    """Analyze platform distribution"""
    print("\n" + "="*70)
    print("🌐 PLATFORM DISTRIBUTION")
    print("="*70)
    
    supabase = get_supabase_client()
    df = None
    if supabase:
        try:
            print("  Fetching from Supabase...")
            res = supabase.table("snapshots").select("platform, hotel_name").execute()
            df = pd.DataFrame(res.data)
        except Exception as e:
            print(f"  Supabase error, falling back to SQLite: {e}")

    if df is None:
        conn = sqlite3.connect(DB_PATH, timeout=30)
        df = pd.read_sql_query("SELECT platform, hotel_name FROM snapshots", conn)
        conn.close()

    plat_stats = df.groupby('platform').agg(
        records=('platform', 'count'),
        hotels=('hotel_name', 'nunique')
    ).reset_index()
    
    print("\nRecords and hotels per platform:")
    for idx, row in plat_stats.iterrows():
        print(f"  {row['platform']}: {row['records']:,} records | {row['hotels']:,} hotels")

def rebuild_master_fact_table():
    """Rebuild the master fact table used by dashboard"""
    print("\n" + "="*70)
    print("🔧 REBUILDING MASTER FACT TABLE")
    print("="*70)
    
    supabase = get_supabase_client()
    df = None
    if supabase:
        try:
            print("  Fetching from Supabase...")
            res = supabase.table("snapshots").select("hotel_name, location, district, platform, stay_date, price, scraped_at, hotel_type").execute()
            df = pd.DataFrame(res.data)
        except Exception as e:
            print(f"  Supabase error, falling back to SQLite: {e}")

    if df is None:
        conn = sqlite3.connect(DB_PATH, timeout=60)
        df = pd.read_sql_query("SELECT hotel_name, location, district, platform, stay_date, price, scraped_at, hotel_type FROM snapshots WHERE price IS NOT NULL", conn)
        conn.close()

    if df.empty:
        print("⚠️ No data available to rebuild fact table.")
        return pd.DataFrame()

    # Manual aggregation in pandas to replicate the SQL query
    fact_df = df.groupby(['hotel_name', 'location', 'district', 'platform', 'stay_date', 'hotel_type']).agg(
        total_nights=('hotel_name', 'count'),
        total_rev=('price', 'sum'),
        scan_days=('scraped_at', lambda x: pd.to_datetime(x).dt.date.nunique()),
        latest_scan=('scraped_at', 'max')
    ).reset_index()
    
    print(f"✓ Generated fact table: {len(fact_df):,} rows")
    print(f"✓ Unique hotels: {fact_df['hotel_name'].nunique():,}")
    print(f"✓ Unique platforms: {fact_df['platform'].nunique():,}")
    print(f"✓ Unique locations: {fact_df['location'].nunique():,}")
    
    # Summary statistics
    print(f"\nRevenue statistics:")
    print(f"  Total: RM{fact_df['total_rev'].sum():,.2f}")
    print(f"  Average per record: RM{fact_df['total_rev'].mean():,.2f}")
    print(f"  Max: RM{fact_df['total_rev'].max():,.2f}")
    
    return fact_df

def health_check():
    """Run all checks"""
    print("\n" + "="*70)
    print("🏥 DATABASE HEALTH CHECK")
    print("="*70)
    
    try:
        analyze_snapshots()
        analyze_pickup_trends()
        analyze_location_distribution()
        analyze_platform_distribution()
        rebuild_master_fact_table()
        
        print("\n" + "="*70)
        print("✅ DATABASE HEALTH CHECK COMPLETE")
        print("="*70)
        print("\n✓ All systems operational!")
        print("✓ Dashboard is ready to display data")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    health_check()
