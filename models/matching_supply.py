"""
Pydantic models for Matching Supply operations
"""
from pydantic import BaseModel, Field
from typing import Optional


class MatchingSupplyCreateRequest(BaseModel):
    """Request model for creating a matching supply record"""
    lead_id: int = Field(..., description="Lead ID (bigint, must exist in leads table)", gt=0)
    whatsapp_listing_id: str = Field(..., description="UUID of WhatsApp listing from whatsapp_listing_data table")


class MatchingSupplyData(BaseModel):
    """Model representing a matching_supply record"""
    id: str = Field(..., description="UUID of matching supply record")
    lead_id: int = Field(..., description="Lead ID")
    supply_id: str = Field(..., description="Supply ID (WhatsApp listing UUID as text)")
    agent_name: Optional[str] = Field(None, description="Agent name from listing")
    agent_phone: Optional[str] = Field(None, description="Agent phone from listing")
    short_desc: Optional[str] = Field(None, description="Short property description")
    match_status: str = Field(default="Identified", description="Match status")
    created_at: str = Field(..., description="Creation timestamp")


class MatchingSupplyCreateResponse(BaseModel):
    """Response model for matching supply creation"""
    success: bool = Field(..., description="Whether operation succeeded")
    data: Optional[MatchingSupplyData] = Field(None, description="Created matching supply record")
    message: str = Field(..., description="Status message")
