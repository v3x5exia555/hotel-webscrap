import sqlite3
import pandas as pd
from datetime import datetime
from utils.helpers import logger
from utils.database import DB_PATH, fetch_data_from_db

def generate_platform_matrix():
    """Generates a report showing which hotels are listed on which platforms."""
    logger.info("Fetching data for platform matrix from database...")
    
    # We fetch basic presence info (remove days limit to see full history)
    df = fetch_data_from_db("snapshots", limit=250000)
    
    if df is None or df.empty:
        logger.warning("No data found to generate matrix.")
        return

    # Reduce to latest status per property-platform
    df_unique = df.groupby(['hotel_name', 'location', 'hotel_type', 'platform'])['scraped_at'].max().reset_index()

    # Pivot the data to create the platform matrix
    matrix = df_unique.pivot_table(
        index=['hotel_name', 'location', 'hotel_type'], 
        columns='platform', 
        values='scraped_at',
        aggfunc='count',
        fill_value=0
    )
    
    # Convert counts to '✓' / '-'
    for col in matrix.columns:
        matrix[col] = matrix[col].apply(lambda x: '✓' if x > 0 else '-')

    output_file = f"data/platform_presence_{datetime.now().strftime('%Y%m%d')}.csv"
    matrix.to_csv(output_file)
    
    logger.info(f"Platform Presence Matrix generated: {output_file}")
    
    # Print a summary to console
    total_hotels = len(matrix)
    
    logger.info(f"Summary: {total_hotels} unique properties identified.")

if __name__ == "__main__":
    generate_platform_matrix()
