"""
Simple property scraping service
"""
from typing import List, Dict, Any
from providers.scrapers.squareyards_scraper import SquareYardsScraper


class PropertyScrapingService:
    """Service for scraping property listings"""

    @staticmethod
    async def scrape_squareyards(url: str) -> List[Dict[str, Any]]:
        """
        Scrape properties from SquareYards URL

        Args:
            url: SquareYards property listing URL or search results URL

        Returns:
            List of property dictionaries (raw data from schema)
        """
        scraper = SquareYardsScraper()
        return await scraper.scrape(url)
