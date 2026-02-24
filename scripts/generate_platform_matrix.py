import sqlite3
import pandas as pd
from datetime import datetime
from utils.helpers import logger
from utils.database import DB_PATH

def generate_platform_matrix():
    """Generates a report showing which hotels are listed on which platforms."""
    conn = sqlite3.connect(DB_PATH)
    
    # Get the latest status for each hotel-platform-stay_date
    query = """
    SELECT 
        hotel_name, 
        location,
        hotel_type,
        platform,
        MAX(scraped_at) as last_seen
    FROM snapshots
    GROUP BY hotel_name, location, hotel_type, platform
    """
    
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    if df.empty:
        logger.warning("No data found to generate matrix.")
        return

    # Pivot the data to create the platform matrix
    matrix = df.pivot_table(
        index=['hotel_name', 'location', 'hotel_type'], 
        columns='platform', 
        values='last_seen',
        aggfunc='count',
        fill_value=0
    )
    
    # Convert counts to 'Yes' / 'No'
    for col in matrix.columns:
        matrix[col] = matrix[col].apply(lambda x: '✓' if x > 0 else '-')

    output_file = f"data/platform_presence_{datetime.now().strftime('%Y%m%d')}.csv"
    matrix.to_csv(output_file)
    
    logger.info(f"Platform Presence Matrix generated: {output_file}")
    
    # Print a summary to console
    total_hotels = len(matrix)
    multi_platform = len(matrix[(matrix == '✓').all(axis=1)])
    
    logger.info(f"Summary: {total_hotels} unique properties identified.")
    logger.info(f"Properties found on multiple platforms: {multi_platform}")

if __name__ == "__main__":
    generate_platform_matrix()
