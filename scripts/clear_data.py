import sqlite3
import os
import glob

DB_PATH = "data/hotel_data.db"

def clear_data():
    if os.path.exists(DB_PATH):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        print("Truncating database tables...")
        cursor.execute("DELETE FROM snapshots")
        cursor.execute("DELETE FROM pickup_trends")
        conn.commit()
        # VACUUM must be outside a transaction
        conn.isolation_level = None
        cursor.execute("VACUUM")
        conn.close()
        print("Database cleared.")

    print("Deleting CSV files...")
    for folder in ["data/agoda", "data/bookingcom"]:
        files = glob.glob(f"{folder}/**/*.csv", recursive=True)
        for f in files:
            try:
                os.remove(f)
            except:
                pass
    print("Files deleted.")

if __name__ == "__main__":
    clear_data()
