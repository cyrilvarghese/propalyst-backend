"""
Pydantic models for CREA WhatsApp listings
"""
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class CreaWappListing(BaseModel):
    """Model representing a CREA WhatsApp listing from Supabase"""
    id: str = Field(..., description="UUID of the listing")
    created_at: datetime = Field(..., description="Timestamp when record was created")
    message_date: Optional[datetime] = Field(None, description="Date of the WhatsApp message")
    agent_name: str = Field(..., description="Name of the agent")
    agent_contact: Optional[str] = Field(None, description="Agent contact number")
    company_name: Optional[str] = Field(None, description="Real estate company name")
    listing_type: Optional[str] = Field(None, description="Type of listing (Sale, Rent, Requirement)")
    transaction_type: Optional[str] = Field(None, description="Transaction type (Buy, Rent, Lease)")
    property_type: Optional[str] = Field(None, description="Property type (Apartment, Villa, Plot, etc.)")
    configuration: Optional[str] = Field(None, description="BHK configuration (2 BHK, 3 BHK, etc.)")
    size_sqft: Optional[float] = Field(None, description="Property size in square feet")
    price: Optional[float] = Field(None, description="Property price in numeric format")
    price_text: Optional[str] = Field(None, description="Property price as text (e.g., '₹2.5 Cr')")
    location: Optional[str] = Field(None, description="Property location/area")
    project_name: Optional[str] = Field(None, description="Project name if applicable")
    facing: Optional[str] = Field(None, description="Property facing direction")
    floor: Optional[str] = Field(None, description="Floor number or range")
    furnishing: Optional[str] = Field(None, description="Furnishing status")
    parking: Optional[int] = Field(None, description="Number of parking spots")
    status: Optional[str] = Field(None, description="Property status (Ready, Under Construction, etc.)")
    amenities: Optional[str] = Field(None, description="Amenities available")
    raw_message: str = Field(..., description="Original WhatsApp message")


class CreaWappResponse(BaseModel):
    """Response model for CREA WhatsApp listings API"""
    success: bool = Field(..., description="Whether the operation was successful")
    data: List[CreaWappListing] = Field(default_factory=list, description="List of listings")
    count: int = Field(0, description="Number of listings returned")
    message: Optional[str] = Field(None, description="Optional message about the operation")


class MessageFormatRequest(BaseModel):
    """Request model for formatting raw WhatsApp messages"""
    raw_message: str = Field(..., description="Raw WhatsApp property listing message", min_length=1)
    agent_name: Optional[str] = Field("Naresh", description="Name of the agent reaching out (default: Naresh)")
    tone: Optional[str] = Field("professional_friendly", description="Tone of the output message (professional_friendly, casual, formal)")
    include_emojis: Optional[bool] = Field(True, description="Whether to include emojis in the formatted message")


class MessageFormatResponse(BaseModel):
    """Response model for formatted message"""
    success: bool = Field(..., description="Whether the operation was successful")
    formatted_message: Optional[str] = Field(None, description="LLM-formatted friendly broker outreach message")
    original_message: str = Field(..., description="Original raw message for reference")
    message: Optional[str] = Field(None, description="Optional status or error message")
