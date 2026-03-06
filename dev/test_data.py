import sys
import os
import pandas as pd
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path(__file__).parent.parent))
from utils.database import fetch_data_from_db

REG_PATH = "data/property_registration.csv"
SUBMITTED_PATH = "data/submitted_records.csv"

def fetch_data():
    print("Fetching snippets for testing...")
    df = fetch_data_from_db("snapshots", limit=1000)
    trends_df = fetch_data_from_db("pickup_trends", limit=500)
    
    reg_df = pd.read_csv(REG_PATH) if os.path.exists(REG_PATH) else pd.DataFrame()
    sub_df = pd.read_csv(SUBMITTED_PATH) if os.path.exists(SUBMITTED_PATH) else pd.DataFrame()
    
    return df, reg_df, None, trends_df, sub_df

if __name__ == "__main__":
    df, reg, pickup, trends, sub = fetch_data()
    print(f"Snapshots sample loaded: {len(df)}")
    print(f"Trends sample loaded: {len(trends)}")
    if not df.empty:
      print(f"Sample stay_date: {df['stay_date'].iloc[0]}")
