"""
Property scraping service supporting multiple providers
"""
from typing import List, Dict, Any
from providers.scrapers.squareyards_scraper import SquareYardsScraper
from providers.scrapers.magicbricks_scraper import MagicBricksScraper


class PropertyScrapingService:
    """Service for scraping property listings from multiple providers"""

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

    @staticmethod
    async def scrape_magicbricks(url: str) -> List[Dict[str, Any]]:
        """
        Scrape properties from MagicBricks URL

        Args:
            url: MagicBricks property listing URL or search results URL

        Returns:
            List of property dictionaries (raw data from schema)
        """
        scraper = MagicBricksScraper()
        return await scraper.scrape(url)
