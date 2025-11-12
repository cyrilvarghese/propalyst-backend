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
    prefix="/api/scrape",
    tags=["Property Scraping"]
)


@router.get("/squareyards", response_model=ScrapeResponse)
async def scrape_squareyards(url: str = Query(..., description="SquareYards property listing URL")):
    """
    Scrape property details from SquareYards URL

    Example:
    ```
    GET /api/scrape/squareyards?url=https://www.squareyards.com/sale/5-bhk-for-sale-in-indiranagar-bangalore
    ```
    """
    try:
        print(f"[API] Scraping SquareYards URL: {url}")

        property_details, agent = await PropertyScrapingService.scrape_squareyards(url)

        return ScrapeResponse(
            success=True,
            property=property_details,
            agent=agent,
            source="squareyards",
            scraped_at=datetime.now().isoformat()
        )

    except Exception as e:
        print(f"[API] Scraping error: {str(e)}")
        return ScrapeResponse(
            success=False,
            property=None,
            agent=None,
            source="squareyards",
            scraped_at=datetime.now().isoformat(),
            error=str(e)
        )


@router.get("/crawl")
async def basic_crawl(url: str = Query(..., description="URL to crawl")):
    """
    Basic web crawling - fetches page and returns markdown content

    Example:
    ```
    GET /api/scrape/crawl?url=https://www.squareyards.com/sale/5-bhk-for-sale-in-indiranagar-bangalore
    ```
    """
    try:
        print(f"[API] Basic crawl for URL: {url}")

        async with AsyncWebCrawler(config=BrowserConfig(
            viewport_height=800,
            viewport_width=1200,
            headless=True,
            verbose=True,
        )) as crawler:
            results: List[CrawlResult] = await crawler.arun(url=url)

            for i, result in enumerate(results):
                print(f"[API] Result {i + 1}:")
                print(f"[API] Success: {result.success}")

                if result.success:
                    markdown_length = len(result.markdown.raw_markdown)
                    print(f"[API] Markdown length: {markdown_length} chars")
                    print(f"[API] First 200 chars: {result.markdown.raw_markdown[:200]}...")

                    return {
                        "success": True,
                        "url": url,
                        "markdown_length": markdown_length,
                        "markdown": result.markdown.raw_markdown,
                        "html_length": len(result.html) if result.html else 0,
                        "scraped_at": datetime.now().isoformat()
                    }
                else:
                    return {
                        "success": False,
                        "url": url,
                        "error": "Failed to crawl the URL",
                        "scraped_at": datetime.now().isoformat()
                    }

        return {
            "success": False,
            "url": url,
            "error": "No results returned from crawler",
            "scraped_at": datetime.now().isoformat()
        }

    except Exception as e:
        print(f"[API] Crawl error: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "url": url,
            "error": str(e),
            "scraped_at": datetime.now().isoformat()
        }
