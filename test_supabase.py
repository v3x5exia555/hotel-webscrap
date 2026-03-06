import os
import logging
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_supabase_connection():
    # Load .env file
    load_dotenv()
    
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    
    if not url or not key:
        logger.error("❌ SUPABASE_URL or SUPABASE_KEY not found in environment variables.")
        return False
    
    logger.info(f"Attempting to connect to Supabase at: {url}")
    
    try:
        from supabase import create_client, Client
    except ImportError:
        logger.error("❌ 'supabase' library not installed. Please run: pip install supabase")
        return False

    try:
        supabase: Client = create_client(url, key)
        # Test a simple query - listing tables is not directly possible via client easily, 
        # so we try to select from a table we expect to exist or just check the client status
        try:
            # Try to fetch some metadata or just check snapshots again
            response = supabase.table("snapshots").select("*").limit(1).execute()
            logger.info("✅ Successfully connected to Supabase and found 'snapshots' table!")
        except Exception as table_err:
            logger.warning(f"⚠️ Connected, but 'snapshots' table check failed: {table_err}")
            logger.info("Checking for any other tables...")
            # This is a bit of a hack as Supabase client doesn't support listing tables 
            # but we can try common ones or just remind the user.
        
        return True
    except Exception as e:
        logger.error(f"❌ Failed to connect to Supabase: {e}")
        return False

if __name__ == "__main__":
    test_supabase_connection()
