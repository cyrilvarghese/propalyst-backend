"""
Property scraping API endpoints
"""
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from datetime import datetime
from typing import List, Optional
import json
from urllib.parse import unquote
from models.scraping import ScrapeResponse
from services.property_scraping_service import PropertyScrapingService
from services.relevance_scoring_service import RelevanceScoringService
from services.data_persistence_service import DataPersistenceService
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlResult

router = APIRouter(
    prefix="/api",
    tags=["Property Listings"]
)


@router.get("/get_listing_details")
async def get_listing_details(
    url: str = Query(..., description="Property listing URL (SquareYards)"),
    orig_query: Optional[str] = Query(None, description="Original search query for relevance scoring")
):
    """
    Get property listing details from URL

    Returns multiple properties if URL is a search results page,
    or a single property if URL is a property detail page.

    If orig_query is provided, returns Server-Sent Events stream with relevance scores.
    Otherwise returns regular JSON response.

    Examples:
    ```
    # Regular response:
    GET /api/get_listing_details?url=https://www.squareyards.com/sale/5-bhk-for-sale-in-indiranagar-bangalore

    # Streaming with relevance scoring:
    GET /api/get_listing_details?url=https://www.squareyards.com/sale/5-bhk-for-sale-in-indiranagar-bangalore&orig_query=2bhk with east facing 2 car parking
    ```
    """
    try:
        print(f"[API] === Incoming Request ===")
        print(f"[API] URL parameter (raw): {url}")
        print(f"[API] orig_query parameter: {orig_query}")

        # Decode URL in case it's double-encoded
        decoded_url = unquote(url)
        print(f"[API] URL parameter (decoded): {decoded_url}")
        print(f"[API] Fetching listing details for URL: {decoded_url}")

        # Get raw data from scraper (already well-formatted by schema)
        properties_data = await PropertyScrapingService.scrape_squareyards(decoded_url)

        # If no orig_query, return regular JSON response
        if not orig_query:
            print(f"[API] No orig_query provided, returning regular response")
            return {
                "success": True,
                "properties": properties_data,
                "count": len(properties_data),
                "source": "squareyards",
                "scraped_at": datetime.now().isoformat()
            }

        # With orig_query, return streaming response with batch relevance scoring
        print(f"[API] orig_query provided: '{orig_query}', streaming with batch relevance scores")

        async def generate_sse_events():
            """Generate Server-Sent Events with batch-scored properties"""
            scoring_service = RelevanceScoringService()
            scraped_at = datetime.now().isoformat()
            batch_size = 10  # Score 10 properties per API call

            try:
                total_properties = len(properties_data)
                print(f"[API] Streaming {total_properties} properties in batches of {batch_size}")

                # Process properties in batches
                for i in range(0, total_properties, batch_size):
                    # Get batch slice (e.g., 0:10, then 10:20)
                    batch = properties_data[i:i + batch_size]
                    batch_num = (i // batch_size) + 1
                    total_batches = (total_properties + batch_size - 1) // batch_size

                    print(f"[API] Processing batch {batch_num}/{total_batches} ({len(batch)} properties)...")

                    # Score entire batch in ONE API call
                    scored_batch = await scoring_service._score_batch(batch, orig_query)

                    # Stream each scored property from this batch immediately
                    for scored_property in scored_batch:
                        yield f"event: property\n"
                        yield f"data: {json.dumps(scored_property)}\n\n"

                    print(f"[API] ✓ Streamed batch {batch_num}/{total_batches}")

                # Send completion event
                completion_data = {
                    "count": total_properties,
                    "source": "squareyards",
                    "scraped_at": scraped_at,
                    "api_calls_made": (total_properties + batch_size - 1) // batch_size
                }
                yield f"event: complete\n"
                yield f"data: {json.dumps(completion_data)}\n\n"

                print(f"[API] ✓ Streaming complete. Made {completion_data['api_calls_made']} API calls for {total_properties} properties")

            except Exception as e:
                print(f"[API] Error during scoring: {e}")
                import traceback
                print(f"[API] Traceback: {traceback.format_exc()}")
                error_data = {"error": str(e)}
                yield f"event: error\n"
                yield f"data: {json.dumps(error_data)}\n\n"

        return StreamingResponse(
            generate_sse_events(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"  # Disable nginx buffering
            }
        )

    except Exception as e:
        print(f"[API] Error fetching listing details: {str(e)}")
        return {
            "success": False,
            "properties": [],
            "count": 0,
            "source": "squareyards",
            "scraped_at": datetime.now().isoformat(),
            "error": str(e)
        }


@router.get("/get_listing_details_batch")
async def get_listing_details_batch(
    url: str = Query(..., description="Property listing URL (SquareYards)"),
    orig_query: str = Query(..., description="Original search query for relevance scoring"),
    batch_size: int = Query(10, description="Number of properties to score per API call (default: 10)"),
    use_cache: bool = Query(True, description="Use cached data if available (default: true)")
):
    """
    Get property listing details with batch relevance scoring (non-streaming).

    This endpoint collects all properties first, then scores them in batches to reduce API calls.
    For example, 15 properties will be scored in 2 API calls (10 + 5) instead of 15 individual calls.

    If the URL has been previously scraped, returns cached data (unless use_cache=false).

    Parameters:
    - url: Property listing URL
    - orig_query: User's search query for relevance scoring (required)
    - batch_size: Properties per API call (default: 10)
    - use_cache: Use cached data if available (default: true)

    Returns:
    - JSON response with all scored properties

    Example:
    ```
    GET /api/get_listing_details_batch?url=https://www.squareyards.com/sale/5-bhk-for-sale-in-indiranagar-bangalore&orig_query=2bhk with east facing 2 car parking&batch_size=10
    ```
    """
    try:
        print(f"[API-Batch] === Incoming Batch Request ===")
        print(f"[API-Batch] URL parameter (raw): {url}")
        print(f"[API-Batch] orig_query parameter: {orig_query}")
        print(f"[API-Batch] batch_size: {batch_size}")
        print(f"[API-Batch] use_cache: {use_cache}")

        # Decode URL in case it's double-encoded
        decoded_url = unquote(url)
        print(f"[API-Batch] URL parameter (decoded): {decoded_url}")

        # Check cache first if enabled
        if use_cache:
            print(f"[API-Batch] Checking cache for URL: {decoded_url}")
            cached_properties = await DataPersistenceService.get_properties_by_url(decoded_url)

            if cached_properties is not None:
                print(f"[API-Batch] ✓ Cache hit! Found {len(cached_properties)} properties in cache")
                return {
                    "success": True,
                    "properties": cached_properties,
                    "count": len(cached_properties),
                    "source": "squareyards",
                    "from_cache": True,
                    "cached_at": "N/A",  # Would need to store timestamps for full tracking
                    "api_calls_made": 0
                }
            else:
                print(f"[API-Batch] Cache miss - will scrape and score fresh data")

        print(f"[API-Batch] Fetching listing details for URL: {decoded_url}")

        # Get raw data from scraper
        properties_data = await PropertyScrapingService.scrape_squareyards(decoded_url)
        print(f"[API-Batch] Scraped {len(properties_data)} properties")

        # Batch score all properties
        scoring_service = RelevanceScoringService()
        scored_properties = await scoring_service.score_properties_batch(
            properties_data,
            orig_query,
            batch_size=batch_size
        )

        print(f"[API-Batch] Returning {len(scored_properties)} scored properties")

        # Save properties to JSON file
        api_calls_made = (len(scored_properties) + batch_size - 1) // batch_size
        persistence_result = await DataPersistenceService.save_scraped_properties(
            url=decoded_url,
            properties=scored_properties,
            merge=True,  # Merge with existing data
            source="squareyards"
        )

        print(f"[API-Batch] Persistence result: {persistence_result}")

        return {
            "success": True,
            "properties": scored_properties,
            "count": len(scored_properties),
            "source": "squareyards",
            "scraped_at": datetime.now().isoformat(),
            "from_cache": False,
            "api_calls_made": api_calls_made,
            "persistence": persistence_result
        }

    except Exception as e:
        print(f"[API-Batch] Error fetching listing details: {str(e)}")
        import traceback
        print(f"[API-Batch] Traceback: {traceback.format_exc()}")
        return {
            "success": False,
            "properties": [],
            "count": 0,
            "source": "squareyards",
            "scraped_at": datetime.now().isoformat(),
            "error": str(e)
        }


@router.get("/get_listing_details_batch_magicbricks")
async def get_listing_details_batch_magicbricks(
    url: str = Query(..., description="Property listing URL (MagicBricks)"),
    orig_query: str = Query(..., description="Original search query for relevance scoring"),
    batch_size: int = Query(10, description="Number of properties to score per API call (default: 10)"),
    use_cache: bool = Query(True, description="Use cached data if available (default: true)")
):
    """
    Get property listing details from MagicBricks with batch relevance scoring (non-streaming).

    This endpoint collects all properties first, then scores them in batches to reduce API calls.
    For example, 15 properties will be scored in 2 API calls (10 + 5) instead of 15 individual calls.

    If the URL has been previously scraped, returns cached data (unless use_cache=false).

    Parameters:
    - url: Property listing URL (MagicBricks)
    - orig_query: User's search query for relevance scoring (required)
    - batch_size: Properties per API call (default: 10)
    - use_cache: Use cached data if available (default: true)

    Returns:
    - JSON response with all scored properties

    Example:
    ```
    GET /api/get_listing_details_batch_magicbricks?url=https://www.magicbricks.com/office-space-for-rent-in-church-street-bangalore&orig_query=2bhk with east facing 2 car parking&batch_size=10
    ```
    """
    try:
        print(f"[API-MagicBricks] === Incoming MagicBricks Batch Request ===")
        print(f"[API-MagicBricks] URL parameter (raw): {url}")
        print(f"[API-MagicBricks] orig_query parameter: {orig_query}")
        print(f"[API-MagicBricks] batch_size: {batch_size}")
        print(f"[API-MagicBricks] use_cache: {use_cache}")

        # Decode URL in case it's double-encoded
        decoded_url = unquote(url)
        print(f"[API-MagicBricks] URL parameter (decoded): {decoded_url}")

        # Check cache first if enabled
        if use_cache:
            print(f"[API-MagicBricks] Checking cache for URL: {decoded_url}")
            cached_properties = await DataPersistenceService.get_properties_by_url(decoded_url)

            if cached_properties is not None:
                print(f"[API-MagicBricks] ✓ Cache hit! Found {len(cached_properties)} properties in cache")
                return {
                    "success": True,
                    "properties": cached_properties,
                    "count": len(cached_properties),
                    "source": "magicbricks",
                    "from_cache": True,
                    "api_calls_made": 0
                }
            else:
                print(f"[API-MagicBricks] Cache miss - will scrape and score fresh data")

        print(f"[API-MagicBricks] Fetching listing details for URL: {decoded_url}")

        # Get raw data from scraper
        properties_data = await PropertyScrapingService.scrape_magicbricks(decoded_url)
        print(f"[API-MagicBricks] Scraped {len(properties_data)} properties")

        # Batch score all properties using MagicBricks-specific scoring
        # (MagicBricks has different field names than SquareYards)
        scoring_service = RelevanceScoringService()
        scored_properties = await scoring_service.score_properties_batch_magicbricks(
            properties_data,
            orig_query,
            batch_size=batch_size
        )

        print(f"[API-MagicBricks] Returning {len(scored_properties)} scored properties")

        # Save properties to JSON file
        api_calls_made = (len(scored_properties) + batch_size - 1) // batch_size
        persistence_result = await DataPersistenceService.save_scraped_properties(
            url=decoded_url,
            properties=scored_properties,
            merge=True,  # Merge with existing data
            source="magicbricks"
        )

        print(f"[API-MagicBricks] Persistence result: {persistence_result}")

        return {
            "success": True,
            "properties": scored_properties,
            "count": len(scored_properties),
            "source": "magicbricks",
            "scraped_at": datetime.now().isoformat(),
            "from_cache": False,
            "api_calls_made": api_calls_made,
            "persistence": persistence_result
        }

    except Exception as e:
        print(f"[API-MagicBricks] Error fetching listing details: {str(e)}")
        import traceback
        print(f"[API-MagicBricks] Traceback: {traceback.format_exc()}")
        return {
            "success": False,
            "properties": [],
            "count": 0,
            "source": "magicbricks",
            "scraped_at": datetime.now().isoformat(),
            "error": str(e)
        }


@router.get("/scraped_properties")
async def get_all_scraped_properties():
    """
    Retrieve all scraped properties from the data file.

    Returns all properties organized by the URL they were scraped from.

    Example:
    ```
    GET /api/scraped_properties
    ```
    """
    try:
        print(f"[API] Retrieving all scraped properties")
        result = await DataPersistenceService.get_all_data()
        return result
    except Exception as e:
        print(f"[API] Error retrieving properties: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "data": {}
        }


@router.get("/scraped_properties/by_url")
async def get_properties_by_url(url: str = Query(..., description="The URL that was scraped")):
    """
    Retrieve properties scraped from a specific URL.

    Parameters:
    - url: The property listing URL to retrieve properties for

    Returns:
    - Array of properties that were scraped from this URL

    Example:
    ```
    GET /api/scraped_properties/by_url?url=https://www.squareyards.com/sale/5-bhk-for-sale-in-indiranagar-bangalore
    ```
    """
    try:
        decoded_url = unquote(url)
        print(f"[API] Retrieving properties for URL: {decoded_url}")

        properties = await DataPersistenceService.get_properties_by_url(decoded_url)

        if properties is None:
            return {
                "success": False,
                "message": "URL not found in data file",
                "url": decoded_url,
                "properties": []
            }

        return {
            "success": True,
            "url": decoded_url,
            "properties": properties,
            "count": len(properties)
        }

    except Exception as e:
        print(f"[API] Error retrieving properties: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "properties": []
        }


@router.delete("/scraped_properties/by_url")
async def delete_properties_by_url(url: str = Query(..., description="The URL whose properties should be deleted")):
    """
    Delete properties scraped from a specific URL.

    Parameters:
    - url: The property listing URL to delete properties for

    Returns:
    - Status of the deletion operation

    Example:
    ```
    DELETE /api/scraped_properties/by_url?url=https://www.squareyards.com/sale/5-bhk-for-sale-in-indiranagar-bangalore
    ```
    """
    try:
        decoded_url = unquote(url)
        print(f"[API] Deleting properties for URL: {decoded_url}")

        result = await DataPersistenceService.delete_properties_by_url(decoded_url)
        return result

    except Exception as e:
        print(f"[API] Error deleting properties: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "url": unquote(url)
        }


@router.delete("/scraped_properties")
async def clear_all_properties():
    """
    Clear all scraped properties from the data file.

    WARNING: This will delete all stored property data!

    Example:
    ```
    DELETE /api/scraped_properties
    ```
    """
    try:
        print(f"[API] Clearing all scraped properties")
        result = await DataPersistenceService.clear_all_data()
        return result

    except Exception as e:
        print(f"[API] Error clearing properties: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }
