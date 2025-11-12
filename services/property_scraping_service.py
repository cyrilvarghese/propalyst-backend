"""
Simple property scraping service
"""
from typing import Tuple
from models.scraping import PropertyDetails, PropertyAgent
from providers.scrapers.squareyards_scraper import SquareYardsScraper


class PropertyScrapingService:
    """Service for scraping property listings"""

    @staticmethod
    async def scrape_squareyards(url: str) -> Tuple[PropertyDetails, PropertyAgent]:
        """
        Scrape property from SquareYards URL

        Args:
            url: SquareYards property listing URL

        Returns:
            Tuple of (PropertyDetails, PropertyAgent)
        """
        scraper = SquareYardsScraper()
        return await scraper.scrape(url)
