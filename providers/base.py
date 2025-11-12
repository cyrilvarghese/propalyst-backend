"""
Base Search Provider
====================

Abstract base class for all search providers.
"""

from abc import ABC, abstractmethod
from typing import List
from models.search import PropertySearchParams, PropertyResult


class BaseSearchProvider(ABC):
    """
    Abstract base class for property search providers.

    All providers (Gemini, Tavily, OpenAI) must implement these methods.
    """

    def __init__(self, api_key: str):
        """
        Initialize the search provider.

        Args:
            api_key: API key for the provider
        """
        self.api_key = api_key

    @abstractmethod
    async def search(self, params: PropertySearchParams, source: str = "") -> List[PropertyResult]:
        """
        Search for properties using the provider's API.

        Args:
            params: Structured search parameters
            source: Data source to search (magicbricks, housing, 99acres, etc.)

        Returns:
            List of property results
        """
        pass

    @abstractmethod
    async def extract_parameters(self, query: str) -> PropertySearchParams:
        """
        Extract structured parameters from natural language query.

        This method uses the provider's LLM to intelligently infer:
        - Property type (3BHK → residential)
        - Location (Indiranagar)
        - Budget (4-7 crores)
        - Other parameters

        Args:
            query: Natural language search query

        Returns:
            Structured search parameters
        """
        pass
