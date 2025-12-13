"""
Filter logic and query building for listings search.
"""
from pydantic import BaseModel, Field
from typing import List, Literal, Union
from datetime import datetime, timedelta

class ListingFilter(BaseModel):
    field: Literal["price_cr", "bhk", "area_sqft", "locality", "near_landmark", 
                   "status", "property_type", "investment_grade", "message_type", "message_date"] = Field(
                       description="The attribute to filter on"
                   )
    op: Literal["eq", "gt", "lt", "gte", "lte", "in", "near"] = Field(
        description="The comparison operator"
    )
    value: Union[str, int, float, bool, List[str], List[int]] = Field(
        description="The value to compare against"
    )


def get_listing_value(listing: dict, field: str):
    """Extract value from listing for a given field."""
    if field == "price_cr":
        price = listing.get("price", 0)
        return float(price) / 10000000 if price else 0
    elif field == "bhk":
        return listing.get("bedroom_count")
    elif field == "area_sqft":
        return listing.get("area_sqft")
    elif field == "locality":
        # Return lowercase for case-insensitive comparison
        location = listing.get("location")
        return location.lower() if location else None
    elif field == "property_type":
        return listing.get("property_type")
    elif field == "message_type":
        return listing.get("message_type")
    elif field == "status":
        # Derive from special_features
        features = listing.get("special_features", [])
        if "ready_to_move" in features:
            return "ready_to_move"
        elif "under_construction" in features:
            return "under_construction"
        return None
    elif field == "investment_grade":
        # Import here to avoid circular dependency
        from .locality_data import LOCALITY_STATS
        # Derive: properties 5-25 cr in high-growth localities
        price_cr = float(listing.get("price", 0)) / 10000000
        locality = listing.get("location")
        if 5 <= price_cr <= 25 and locality in LOCALITY_STATS:
            stats = LOCALITY_STATS[locality]
            return stats.get("five_year_cagr_pct", 0) > 9.0
        return False
    return None


def apply_filter(listing: dict, filter_obj: ListingFilter) -> bool:
    """Apply a single filter to a listing."""
    field = filter_obj.field
    op = filter_obj.op
    value = filter_obj.value
    
    listing_value = get_listing_value(listing, field)
    
    if listing_value is None:
        return False
    
    # Special handling for locality - fuzzy, case-insensitive
    if field == "locality":
        if op == "eq":
            # Fuzzy match: check if value is contained in location
            return value.lower() in listing_value  # listing_value is already lowercase
        elif op == "in":
            # Check if any of the values match fuzzily
            if isinstance(value, list):
                return any(v.lower() in listing_value for v in value)
            return False
    
    if op == "eq":
        return listing_value == value
    elif op == "gt":
        return listing_value > value
    elif op == "lt":
        return listing_value < value
    elif op == "gte":
        return listing_value >= value
    elif op == "lte":
        return listing_value <= value
    elif op == "in":
        if isinstance(value, list):
            return listing_value in value
        return False
    elif op == "near":
        # Import here to avoid circular dependency
        from .locality_data import LANDMARK_TO_LOCALITIES
        # For near_landmark, check if locality is in the landmark's area
        if field == "near_landmark":
            locality = listing.get("location")
            nearby = LANDMARK_TO_LOCALITIES.get(value, [])
            return locality in nearby
        # For locality partial match
        if isinstance(listing_value, str) and isinstance(value, str):
            return value.lower() in listing_value.lower()
        return False
    
    return False


def apply_filters_to_supabase_query(query, filters):
    """Apply filter JSON to Supabase query dynamically."""
    from .locality_data import LANDMARK_TO_LOCALITIES
    
    for filter_obj in filters:
        field = filter_obj.get("field")
        op = filter_obj.get("op")
        value = filter_obj.get("value")
        
        # Map filter fields to database columns
        db_field = field
        if field == "bhk":
            db_field = "bedroom_count"
        elif field == "price_cr":
            # Price in DB is in rupees, filter is in crores
            if op == "eq":
                query = query.eq("price", int(value * 10000000))
            elif op == "gt":
                query = query.gt("price", int(value * 10000000))
            elif op == "lt":
                query = query.lt("price", int(value * 10000000))
            elif op == "gte":
                query = query.gte("price", int(value * 10000000))
            elif op == "lte":
                query = query.lte("price", int(value * 10000000))
            continue
        elif field == "locality":
            db_field = "location"
            # Use fuzzy, case-insensitive matching for locality
            if op == "eq":
                # Convert exact match to fuzzy match
                query = query.ilike(db_field, f"%{value}%")
                continue
            elif op == "in":
                # For IN operator, use OR with ilike for each value
                if isinstance(value, list) and len(value) > 0:
                    # Build OR condition with ilike for each locality
                    # Syntax: location.ilike.%val1%,location.ilike.%val2%
                    or_conditions = ",".join([f'location.ilike.%{v}%' for v in value])
                    query = query.or_(or_conditions)
                continue
        elif field == "near_landmark":
            # Handle landmark proximity with location IN query
            nearby_localities = LANDMARK_TO_LOCALITIES.get(value, [])
            if nearby_localities:
                query = query.in_("location", nearby_localities)
            continue
        elif field == "status":
            # Status is derived from special_features, skip for now
            continue
        elif field == "investment_grade":
            # Investment grade is computed, skip for now
            continue
        elif field == "message_date" or field == "date":
            # Handle date filtering
            db_field = "message_date"
        
        # Apply standard operators
        if op == "eq":
            query = query.eq(db_field, value)
        elif op == "gt":
            query = query.gt(db_field, value)
        elif op == "lt":
            query = query.lt(db_field, value)
        elif op == "gte":
            query = query.gte(db_field, value)
        elif op == "lte":
            query = query.lte(db_field, value)
        elif op == "in":
            if isinstance(value, list):
                query = query.in_(db_field, value)
        elif op == "near":
            # For text fields, use ilike for partial match
            query = query.ilike(db_field, f"%{value}%")
    
    # If no date filter specified, default to recent listings (last 30 days)
    has_date_filter = any(f.get("field") in ["message_date", "date"] for f in filters)
    if not has_date_filter:
        thirty_days_ago = (datetime.now() - timedelta(days=30)).isoformat()
        query = query.gte("message_date", thirty_days_ago)
        print(f"📅 No date filter specified, defaulting to listings from last 30 days")
    
    return query
