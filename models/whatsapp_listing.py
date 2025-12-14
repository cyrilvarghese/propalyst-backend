"""
Pydantic models for WhatsApp Listing Data Extraction
"""
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class WhatsAppListingLLMInput(BaseModel):
    """Input payload sent to LLM for extraction"""
    raw_message: str = Field(..., description="Raw WhatsApp message text")


class WhatsAppListingLLMOutput(BaseModel):
    """Expected output from LLM for WhatsApp listing extraction"""
    message_type: str = Field(..., description="Classification: greeting, garbage, generic_info, supply_sale, supply_rent, demand_buy, demand_rent")
    agent_name: Optional[str] = Field(None, description="Agent name extracted from message")
    agent_contact: Optional[str] = Field(None, description="Agent contact number extracted from message")
    property_type: Optional[str] = Field(None, description="apartment, villa, independent_house, plot, land, office, retail, warehouse, industrial, other")
    area_sqft: Optional[float] = Field(None, description="Area in square feet")
    bedroom_count: Optional[int] = Field(None, description="Number of bedrooms (e.g., 3 BHK = 3, Studio = 0)")
    price: Optional[float] = Field(None, description="Price in rupees")
    price_text: Optional[str] = Field(None, description="Human-readable price phrase")
    location: Optional[str] = Field(None, description="Main locality or micro market")
    project_name: Optional[str] = Field(None, description="Building or project name")
    furnishing_status: Optional[str] = Field(None, description="unfurnished, semi_furnished, fully_furnished, bare_shell, warm_shell, unknown")
    parking_count: Optional[int] = Field(None, description="Number of car parks")
    parking_text: Optional[str] = Field(None, description="Raw parking description")
    facing_direction: Optional[str] = Field(None, description="north, south, east, west, north_east, road_facing, park_facing, etc.")
    special_features: List[str] = Field(default_factory=list, description="Feature tags like corner_plot, lake_view, gated_community")
    llm_notes: Optional[str] = Field(None, description="Free text notes from LLM")

class WhatsAppListingData(BaseModel):
    """Model representing complete extracted listing data"""
    id: str
    source_message_id: Optional[str] = None
    message_date: Optional[datetime] = None
    agent_contact: Optional[str] = None
    agent_name: Optional[str] = None
    company_name: Optional[str] = None
    raw_message: Optional[str] = None
    message_type: Optional[str] = None
    property_type: Optional[str] = None
    area_sqft: Optional[float] = None
    bedroom_count: Optional[int] = None
    price: Optional[float] = None
    price_text: Optional[str] = None
    location: Optional[str] = None
    project_name: Optional[str] = None
    furnishing_status: Optional[str] = None
    parking_count: Optional[int] = None
    parking_text: Optional[str] = None
    facing_direction: Optional[str] = None
    special_features: List[str] = Field(default_factory=list)
    llm_json: Optional[dict] = None
    created_at: Optional[datetime] = None
    sender_name: Optional[str] = None

    class Config:
        """Pydantic config for JSON serialization of datetime objects"""
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }

    def dict(self, **kwargs) -> dict:
        """Override dict() to handle datetime serialization for JSON compatibility"""
        data = super().dict(**kwargs)
        # Convert datetime objects to ISO format strings
        if data.get('message_date') and isinstance(data['message_date'], datetime):
            data['message_date'] = data['message_date'].isoformat()
        if data.get('created_at') and isinstance(data['created_at'], datetime):
            data['created_at'] = data['created_at'].isoformat()
        return data


class WhatsAppListingExtractionResponse(BaseModel):
    """Response model for extraction operations"""
    success: bool
    messages_processed: int = 0
    messages_extracted: int = 0
    messages_failed: int = 0
    errors: List[str] = Field(default_factory=list)
    message: Optional[str] = None
    data: Optional[List[WhatsAppListingData]] = None


class UnprocessedMessage(BaseModel):
    """Model for unprocessed messages from crea_wapp"""
    id: str
    message_date: Optional[datetime]
    agent_contact: str
    agent_name: Optional[str]
    company_name: Optional[str]
    raw_message: str
