import sys
import os
import pandas as pd
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path(__file__).parent.parent))

from utils.database import fetch_data_from_db

REG_PATH = "data/property_registration.csv"
SUBMITTED_PATH = "data/submitted_records.csv"

def fuzzy_match(ota_name, official_names):
    if pd.isna(ota_name): return None
    ota_clean = ota_name.strip().lower()
    for off_name in official_names:
        off_clean = str(off_name).strip().lower()
        if off_clean in ota_clean or ota_clean in off_clean:
            return off_name
    return None

def test_data_link():
    print("Fetching data for test link from database...")
    df = fetch_data_from_db("snapshots", limit=100000)
    
    if df is None or df.empty:
        print("No snapshots found in database.")
        return
    
    reg_df = pd.read_csv(REG_PATH) if os.path.exists(REG_PATH) else pd.DataFrame()
    sub_df = pd.read_csv(SUBMITTED_PATH) if os.path.exists(SUBMITTED_PATH) else pd.DataFrame()

    print(f"Snapshots loaded: {len(df)}")
    master_df = df.groupby(['hotel_name', 'location']).agg({'platform': 'last'}).reset_index()
    print(f"Unique OTA Hotels: {len(master_df)}")

    if not reg_df.empty:
        official_names = reg_df['Hotel Name'].tolist()
        master_df['Matched Official Name'] = master_df['hotel_name'].apply(lambda x: fuzzy_match(x, official_names))
        
        matches = master_df[master_df['Matched Official Name'].notna()]
        print(f"Fuzzy Matches (Containment): {len(matches)}")
        print("\n--- Examples ---")
        print(matches[['hotel_name', 'Matched Official Name']].head(10))

if __name__ == "__main__":
    test_data_link()
