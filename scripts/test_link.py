import pandas as pd
import sqlite3
import os

DB_PATH = "data/hotel_data.db"
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
    if not os.path.exists(DB_PATH):
        print("DB not found")
        return
    
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM snapshots", conn)
    conn.close()

    reg_df = pd.read_csv(REG_PATH) if os.path.exists(REG_PATH) else pd.DataFrame()
    sub_df = pd.read_csv(SUBMITTED_PATH) if os.path.exists(SUBMITTED_PATH) else pd.DataFrame()

    print(f"Snapshots: {len(df)}")
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
