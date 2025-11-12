"""
Property Search Models
======================

Pydantic models for property search parameters and responses.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class PropertySearchParams(BaseModel):
    """
    Structured search parameters extracted from natural language query.

    The LLM infers these from user input like:
    "3bhk property near indiranagar 100ft road with budget 4-7 crores"

    Inference Rules:
    - "3BHK", "2BHK" → property_type + category="residential"
    - "office", "shop" → category="commercial"
    - Location names extracted from context
    - Budget parsed from "lakhs", "crores", ranges
    """

    property_type: Optional[str] = Field(
        None,
        description="Type of property: 3BHK, 2BHK, Villa, etc."
    )

    category: str = Field(
        default="residential",
        description="Property category: residential or commercial"
    )

    location: Optional[str] = Field(
        None,
        description="Primary location: Indiranagar, Koramangala, etc."
    )

    budget_min: Optional[float] = Field(
        None,
        description="Minimum budget in crores"
    )

    budget_max: Optional[float] = Field(
        None,
        description="Maximum budget in crores"
    )

    keywords: List[str] = Field(
        default_factory=list,
        description="Additional search keywords"
    )

    city: str = Field(
        default="Bangalore",
        description="City for property search"
    )


class PropertyResult(BaseModel):
    """
    Individual property search result.
    """

    title: str = Field(..., description="Property title/heading")

    url: str = Field(..., description="Source URL")

    snippet: str = Field(..., description="Brief description")

    price: Optional[str] = Field(None, description="Property price")

    location: Optional[str] = Field(None, description="Property location")

    property_type: Optional[str] = Field(None, description="Type (3BHK, etc.)")

    source: str = Field(default="web", description="Source: magicbricks, housing, etc.")


class GroundingSource(BaseModel):
    """
    Citation source from Gemini grounding.
    """

    title: str
    url: str
    snippet: Optional[str] = None


class SearchResponse(BaseModel):
    """
    Complete search response with results and metadata.
    """

    results: List[PropertyResult] = Field(
        default_factory=list,
        description="List of property results"
    )

    extracted_params: PropertySearchParams = Field(
        ...,
        description="Parameters extracted from user query"
    )

    sources: List[GroundingSource] = Field(
        default_factory=list,
        description="Grounding sources (citations)"
    )

    total_results: int = Field(
        default=0,
        description="Total number of results found"
    )

    provider: str = Field(
        default="gemini",
        description="Search provider used"
    )


class PropertySearchRequest(BaseModel):
    """
    API request model for property search endpoint.
    """

    query: str = Field(
        ...,
        description="Natural language search query",
        examples=["3bhk near indiranagar budget 4-7 crores"]
    )

    sources: str = Field(
        default="",
        description="Comma-separated data sources to search (e.g., 'magicbricks,housing,99acres')"
    )

    provider: str = Field(
        default="gemini",
        description="Search provider: gemini, tavily, openai"
    )
