"""
Pydantic models for property scraping
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class PropertyDetails(BaseModel):
    """Complete property information"""
    property_id: str
    title: str
    price: str
    price_amount: Optional[int] = None
    location: str
    city: str
    sublocality: str
    bedrooms: int
    bathrooms: int
    bhk: str  # "5 BHK"
    area: str
    area_sqft: int
    carpet_area: str
    property_type: str
    facing: Optional[str] = None
    parking: Optional[str] = None
    flooring: Optional[str] = None
    furnishing: Optional[str] = None
    description: str
    url: str
    image_url: str


class PropertyAgent(BaseModel):
    """Agent/contact information"""
    name: str
    rating: Optional[float] = None
    image_url: str
    profile_url: str
    user_type: str = "CP"


class ScrapeRequest(BaseModel):
    """API request for scraping"""
    url: str
    source: str = "squareyards"


class ScrapeResponse(BaseModel):
    """API response with scraped data"""
    success: bool
    property: Optional[PropertyDetails] = None
    agent: Optional[PropertyAgent] = None
    source: str
    scraped_at: str
    error: Optional[str] = None
