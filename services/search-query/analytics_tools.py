"""
Analytics tools for aggregating and summarizing listing data.
These tools process data in Python to avoid overwhelming the LLM with raw listings.
"""
from .tools import search_listings


def get_price_distribution(filters):
    """
    Get price distribution for listings matching filters.
    Groups listings into price ranges instead of returning raw data.
    
    Args:
        filters: List of filter dicts (same format as search_listings)
        
    Returns:
        {
            "total_count": int,
            "distribution": {
                "range_name": {
                    "count": int,
                    "avg_price_cr": float,
                    "min_price_cr": float,
                    "max_price_cr": float,
                    "sample_ids": [str]  # Up to 3 example listing IDs
                }
            }
        }
    """
    # Get raw listings
    listings = search_listings(filters)
    
    if not listings:
        return {"total_count": 0, "distribution": {}}
    
    # Define price ranges (in crores)
    ranges = {
        "0-5 Cr": {"min": 0, "max": 5, "listings": []},
        "5-10 Cr": {"min": 5, "max": 10, "listings": []},
        "10-20 Cr": {"min": 10, "max": 20, "listings": []},
        "20-50 Cr": {"min": 20, "max": 50, "listings": []},
        "50+ Cr": {"min": 50, "max": float('inf'), "listings": []},
    }
    
    # Group listings into ranges
    for listing in listings:
        price = listing.get("price")
        if price is None:
            continue  # Skip listings without price
            
        price_cr = price / 10000000
        
        for range_name, range_info in ranges.items():
            if range_info["min"] <= price_cr < range_info["max"]:
                range_info["listings"].append(listing)
                break
    
    # Build summary for each range
    distribution = {}
    for range_name, range_info in ranges.items():
        listings_in_range = range_info["listings"]
        
        if not listings_in_range:
            continue
            
        prices = [l.get("price", 0) / 10000000 for l in listings_in_range if l.get("price")]
        
        distribution[range_name] = {
            "count": len(listings_in_range),
            "avg_price_cr": round(sum(prices) / len(prices), 2),
            "min_price_cr": round(min(prices), 2),
            "max_price_cr": round(max(prices), 2),
            "sample_ids": [l.get("id") for l in listings_in_range[:3]]
        }
    
    return {
        "total_count": len(listings),
        "distribution": distribution
    }


def get_bhk_distribution(filters):
    """
    Get BHK distribution for listings matching filters.
    
    Args:
        filters: List of filter dicts
        
    Returns:
        {
            "total_count": int,
            "distribution": {
                "bhk_count": {
                    "count": int,
                    "avg_price_cr": float,
                    "localities": [str],  # Top 3 localities
                    "sample_ids": [str]
                }
            }
        }
    """
    listings = search_listings(filters)
    
    if not listings:
        return {"total_count": 0, "distribution": {}}
    
    # Group by BHK
    bhk_groups = {}
    for listing in listings:
        bhk = listing.get("bedroom_count", "Unknown")
        bhk_key = f"{bhk} BHK" if bhk != "Unknown" else "Unknown"
        
        if bhk_key not in bhk_groups:
            bhk_groups[bhk_key] = []
        bhk_groups[bhk_key].append(listing)
    
    # Build summary
    distribution = {}
    for bhk_key, bhk_listings in bhk_groups.items():
        prices = [l.get("price", 0) / 10000000 for l in bhk_listings if l.get("price") is not None]
        localities = [l.get("location") for l in bhk_listings if l.get("location")]
        
        # Count locality frequency
        locality_counts = {}
        for loc in localities:
            locality_counts[loc] = locality_counts.get(loc, 0) + 1
        
        # Get top 3 localities
        top_localities = sorted(locality_counts.items(), key=lambda x: x[1], reverse=True)[:3]
        
        distribution[bhk_key] = {
            "count": len(bhk_listings),
            "avg_price_cr": round(sum(prices) / len(prices), 2) if prices else 0,
            "top_localities": [loc for loc, _ in top_localities],
            "sample_ids": [l.get("id") for l in bhk_listings[:3]]
        }
    
    return {
        "total_count": len(listings),
        "distribution": distribution
    }


def get_summary_stats(filters):
    """
    Get statistical summary for listings matching filters.
    
    Args:
        filters: List of filter dicts
        
    Returns:
        {
            "count": int,
            "price_stats": {
                "min_cr": float,
                "max_cr": float,
                "avg_cr": float,
                "median_cr": float
            },
            "area_stats": {
                "min_sqft": int,
                "max_sqft": int,
                "avg_sqft": int
            }
        }
    """
    listings = search_listings(filters)
    
    if not listings:
        return {"count": 0, "price_stats": {}, "area_stats": {}}
    
    # Extract prices and areas
    prices = [l.get("price", 0) / 10000000 for l in listings if l.get("price") is not None]
    areas = [l.get("area_sqft", 0) for l in listings if l.get("area_sqft")]
    
    # Calculate median
    def median(values):
        sorted_values = sorted(values)
        n = len(sorted_values)
        if n % 2 == 0:
            return (sorted_values[n//2 - 1] + sorted_values[n//2]) / 2
        return sorted_values[n//2]
    
    result = {
        "count": len(listings),
        "price_stats": {},
        "area_stats": {}
    }
    
    if prices:
        result["price_stats"] = {
            "min_cr": round(min(prices), 2),
            "max_cr": round(max(prices), 2),
            "avg_cr": round(sum(prices) / len(prices), 2),
            "median_cr": round(median(prices), 2)
        }
    
    if areas:
        result["area_stats"] = {
            "min_sqft": int(min(areas)),
            "max_sqft": int(max(areas)),
            "avg_sqft": int(sum(areas) / len(areas))
        }
    
    return result


def get_locality_breakdown(filters):
    """
    Get breakdown of listings by locality.
    
    Args:
        filters: List of filter dicts
        
    Returns:
        {
            "total_count": int,
            "localities": {
                "locality_name": {
                    "count": int,
                    "avg_price_cr": float,
                    "property_types": [str]  # Unique property types
                }
            }
        }
    """
    listings = search_listings(filters)
    
    if not listings:
        return {"total_count": 0, "localities": {}}
    
    # Group by locality
    locality_groups = {}
    for listing in listings:
        locality = listing.get("location", "Unknown")
        
        if locality not in locality_groups:
            locality_groups[locality] = []
        locality_groups[locality].append(listing)
    
    # Build summary
    localities = {}
    for locality, loc_listings in locality_groups.items():
        prices = [l.get("price", 0) / 10000000 for l in loc_listings if l.get("price") is not None]
        property_types = list(set([l.get("property_type") for l in loc_listings if l.get("property_type")]))
        
        localities[locality] = {
            "count": len(loc_listings),
            "avg_price_cr": round(sum(prices) / len(prices), 2) if prices else 0,
            "property_types": property_types
        }
    
    return {
        "total_count": len(listings),
        "localities": localities
    }
