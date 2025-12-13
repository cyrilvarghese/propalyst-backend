"""
Database operations for Supabase integration.
"""
from supabase import create_client, Client
import os
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Supabase client
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
USE_SUPABASE = os.getenv("USE_SUPABASE", "false").lower() == "true"

print(f"🔧 DEBUG: USE_SUPABASE = {USE_SUPABASE} (raw: {os.getenv('USE_SUPABASE', 'NOT SET')})")
print(f"🔧 DEBUG: SUPABASE_URL = {'SET' if SUPABASE_URL else 'NOT SET'}")
print(f"🔧 DEBUG: SUPABASE_KEY = {'SET' if SUPABASE_KEY else 'NOT SET'}")

supabase: Client = None
if USE_SUPABASE and SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("✅ Supabase client initialized (ACTIVE)")
    except Exception as e:
        print(f"❌ Error initializing Supabase: {e}")
        USE_SUPABASE = False
else:
    print("📁 Using mock data (Supabase disabled)")


def parse_listing_data(listing):
    """Parse and clean listing data from database."""
    # Parse special_features from JSON string to array
    if listing.get('special_features'):
        try:
            if isinstance(listing['special_features'], str):
                listing['special_features'] = json.loads(listing['special_features'])
        except:
            listing['special_features'] = []
    else:
        listing['special_features'] = []
    
    # Ensure numeric fields
    if listing.get('area_sqft'):
        try:
            listing['area_sqft'] = int(listing['area_sqft'])
        except:
            listing['area_sqft'] = 0
            
    if listing.get('price'):
        try:
            listing['price'] = int(listing['price'])
        except:
            listing['price'] = 0
            
    if listing.get('bedroom_count'):
        try:
            listing['bedroom_count'] = int(listing['bedroom_count'])
        except:
            listing['bedroom_count'] = None
    
    return listing


def query_listings(query_builder):
    """
    Execute Supabase query and return parsed results.
    
    Args:
        query_builder: Supabase query object
        
    Returns:
        List of parsed listings
    """
    if not supabase:
        return []
    
    try:
        print("Executing query:", query_builder)
        response = query_builder.execute()
        results = response.data
        
        # Parse and clean results
        for listing in results:
            parse_listing_data(listing)
        
        return results
    except Exception as e:
        print(f"❌ Database query error: {e}")
        return []


def get_listing_by_id(listing_id: str):
    """Fetch a single listing by ID from database."""
    if not supabase:
        return None
    
    try:
        response = supabase.table('whatsapp_listings_relevant')\
            .select('*')\
            .eq('id', listing_id)\
            .execute()
        if response.data:
            listing = response.data[0]
            parse_listing_data(listing)
            return listing
    except Exception as e:
        print(f"Error fetching listing: {e}")
    
    return None


def count_listings_by_location(locality: str):
    """Count listings in a specific locality."""
    if not supabase:
        return 0
    
    try:
        response = supabase.table('whatsapp_listings_relevant')\
            .select('id', count='exact')\
            .eq('location', locality)\
            .execute()
        return response.count or 0
    except:
        return 0
