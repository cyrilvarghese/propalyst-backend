"""
Unified Property Models
=======================

Pydantic models for unified property listing response schema.
Used to normalize data from multiple sources (WhatsApp listings, properties table)
into a consistent format for the frontend.

Purpose:
    - Single schema for UI rendering across different data sources
    - Consistent field names (bedrooms, sqft, price)
    - Source-specific fields are nullable (e.g., message_type for WhatsApp only)

Data Sources:
    1. WhatsApp Listings (whatsapp_listing_data table)
    2. Properties (properties_with_agent view)
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class UnifiedPropertyListing(BaseModel):
    """
    Unified property listing model that works for both WhatsApp and properties sources

    Common Fields:
        All sources provide: id, source, title, description, property_type, bedrooms,
        sqft, price, location, created_at

    Source-Specific Fields:
        WhatsApp only: message_type, raw_message
        Properties only: static_flyer_url, static_html_url, verified_by, owner_name, owner_number

    Nullable Fields:
        Fields that may not exist in all sources are marked Optional
    """

    # Core identification
    id: str = Field(..., description="UUID of the listing")
    source: str = Field(..., description="Data source: 'whatsapp' or 'properties'")

    # Basic property info
    title: Optional[str] = Field(None, description="Property title or project name")
    description: Optional[str] = Field(None, description="Property description")
    property_type: Optional[str] = Field(None, description="apartment, villa, plot, office, etc.")

    # Property specifications
    bedrooms: Optional[int] = Field(None, description="Number of bedrooms")
    bathrooms: Optional[int] = Field(None, description="Number of bathrooms")
    sqft: Optional[float] = Field(None, description="Area in square feet")
    price: Optional[float] = Field(None, description="Price in rupees")
    price_text: Optional[str] = Field(None, description="Human-readable price (e.g., '50 Lakhs')")

    # Location
    location: Optional[str] = Field(None, description="Location/area/city")
    project_name: Optional[str] = Field(None, description="Building or project name")

    # Property features
    furnishing_status: Optional[str] = Field(None, description="unfurnished, semi_furnished, fully_furnished")
    facing_direction: Optional[str] = Field(None, description="north, south, east, west, etc.")
    parking_count: Optional[int] = Field(None, description="Number of parking spaces")
    special_features: List[str] = Field(default_factory=list, description="List of features like gated_community, pool, etc.")

    # Media
    images: List[str] = Field(default_factory=list, description="Array of image URLs")

    # Agent/Contact information
    agent_name: Optional[str] = Field(None, description="Agent or poster name")
    agent_contact: Optional[str] = Field(None, description="Agent phone number")
    agent_email: Optional[str] = Field(None, description="Agent email")
    company_name: Optional[str] = Field(None, description="Real estate company name")
    agent_avatar: Optional[str] = Field(None, description="Agent avatar URL")
    agent_vanity_url: Optional[str] = Field(None, description="Agent profile vanity URL")

    # Owner information (properties only)
    owner_name: Optional[str] = Field(None, description="Property owner name (if different from agent)")
    owner_number: Optional[str] = Field(None, description="Property owner contact")

    # Status and metadata
    status: Optional[str] = Field(None, description="available, sold, rented, etc.")
    created_at: datetime = Field(..., description="When the listing was created")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")

    # WhatsApp-specific fields (NULL for properties source)
    message_type: Optional[str] = Field(None, description="supply_sale, supply_rent, demand_buy, demand_rent (WhatsApp only)")
    message_date: Optional[datetime] = Field(None, description="Original message timestamp from WhatsApp (WhatsApp only)")
    raw_message: Optional[str] = Field(None, description="Original WhatsApp message text (WhatsApp only)")

    # Properties-specific fields (NULL for WhatsApp source)
    static_flyer_url: Optional[str] = Field(None, description="Static flyer URL (properties only)")
    static_html_url: Optional[str] = Field(None, description="Static HTML page URL (properties only)")
    verified_by: Optional[str] = Field(None, description="Who verified this property (properties only)")
    view_count: Optional[int] = Field(None, description="Number of views (properties only)")
    currency: Optional[str] = Field(None, description="Currency code (properties only)")

    # Additional metadata
    source_key: Optional[str] = Field(None, description="Unique identifier from source system")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "source": "whatsapp",
                "title": "3BHK Apartment in Whitefield",
                "description": "Spacious 3BHK with modern amenities",
                "property_type": "apartment",
                "bedrooms": 3,
                "bathrooms": 2,
                "sqft": 1500.0,
                "price": 5000000.0,
                "price_text": "50 Lakhs",
                "location": "Whitefield, Bangalore",
                "project_name": "Brigade Meadows",
                "furnishing_status": "semi_furnished",
                "facing_direction": "north",
                "parking_count": 2,
                "special_features": ["gated_community", "swimming_pool", "gym"],
                "images": [],
                "agent_name": "Tajamul Ahmed",
                "agent_contact": "9876543210",
                "company_name": "Propalyst Realty",
                "status": "available",
                "created_at": "2025-01-15T10:30:00Z",
                "message_type": "supply_sale"
            }
        }


class UnifiedPropertyResponse(BaseModel):
    """
    Response model for unified property listings endpoint

    Returns separate arrays for WhatsApp and properties sources,
    but both use the same UnifiedPropertyListing schema for easy UI rendering.
    """

    whatsapp_listings: List[UnifiedPropertyListing] = Field(
        default_factory=list,
        description="WhatsApp listings with unified schema"
    )

    rb_properties: List[UnifiedPropertyListing] = Field(
        default_factory=list,
        description="Properties from properties table with unified schema"
    )

    counts: dict = Field(
        ...,
        description="Count breakdown by source",
        example={"whatsapp": 50, "properties": 30}
    )

    total_count: int = Field(
        ...,
        description="Total number of listings across all sources"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "whatsapp_listings": [
                    {
                        "id": "uuid-1",
                        "source": "whatsapp",
                        "bedrooms": 3,
                        "sqft": 1500,
                        "price": 5000000,
                        "agent_name": "Tajamul",
                        "message_type": "supply_sale"
                    }
                ],
                "rb_properties": [
                    {
                        "id": "uuid-2",
                        "source": "properties",
                        "bedrooms": 3,
                        "sqft": 1500,
                        "price": 5000000,
                        "agent_name": "John Doe",
                        "static_flyer_url": "https://..."
                    }
                ],
                "counts": {"whatsapp": 1, "properties": 1},
                "total_count": 2
            }
        }
