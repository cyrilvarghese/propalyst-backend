"""
Property scraping API endpoints
"""
from fastapi import APIRouter, HTTPException, Query
from datetime import datetime
from typing import List
from models.scraping import ScrapeResponse
from services.property_scraping_service import PropertyScrapingService
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlResult

router = APIRouter(
    prefix="/api",
    tags=["Property Listings"]
)


@router.get("/get_listing_details")
async def get_listing_details(url: str = Query(..., description="Property listing URL (SquareYards)")):
    """
    Get property listing details from URL

    Returns multiple properties if URL is a search results page,
    or a single property if URL is a property detail page.

    Example:
    ```
    GET /api/get_listing_details?url=https://www.squareyards.com/sale/5-bhk-for-sale-in-indiranagar-bangalore
    ```
    """
    try:
        print(f"[API] Fetching listing details for URL: {url}")

        # Get raw data from scraper (already well-formatted by schema)
        properties_data = await PropertyScrapingService.scrape_squareyards(url)

        # Return raw data directly - schema already structured it correctly
        return {
            "success": True,
            "properties": properties_data,
            "count": len(properties_data),
            "source": "squareyards",
            "scraped_at": datetime.now().isoformat()
        }

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
