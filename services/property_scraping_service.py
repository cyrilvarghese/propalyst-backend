"""
Property scraping service supporting multiple providers
"""
from typing import List, Dict, Any
from providers.scrapers.squareyards.squareyards_scraper import SquareYardsScraper
from providers.scrapers.magicbricks.magicbricks_scraper import MagicBricksScraper


class PropertyScrapingService:
    """Service for scraping property listings from multiple providers"""

    # Shared scraper instances (singleton pattern to save memory)
    _squareyards_scraper = None
    _magicbricks_scraper = None

    @classmethod
    def _get_squareyards_scraper(cls):
        """Get or create shared SquareYards scraper instance"""
        if cls._squareyards_scraper is None:
            cls._squareyards_scraper = SquareYardsScraper()
            print("[PropertyScrapingService] ✓ Created shared SquareYards scraper instance")
        return cls._squareyards_scraper

    @classmethod
    def _get_magicbricks_scraper(cls):
        """Get or create shared MagicBricks scraper instance"""
        if cls._magicbricks_scraper is None:
            cls._magicbricks_scraper = MagicBricksScraper()
            print("[PropertyScrapingService] ✓ Created shared MagicBricks scraper instance")
        return cls._magicbricks_scraper

    @classmethod
    async def scrape_squareyards(cls, url: str) -> List[Dict[str, Any]]:
        """
        Scrape properties from SquareYards URL

        Args:
            url: SquareYards property listing URL or search results URL

        Returns:
            List of property dictionaries (raw data from schema)
        """
        scraper = cls._get_squareyards_scraper()
        return await scraper.scrape(url)

    @classmethod
    async def scrape_magicbricks(cls, url: str) -> List[Dict[str, Any]]:
        """
        Scrape properties from MagicBricks URL

        Args:
            url: MagicBricks property listing URL or search results URL

        Returns:
            List of property dictionaries (raw data from schema)
        """
        scraper = cls._get_magicbricks_scraper()
        return await scraper.scrape(url)
