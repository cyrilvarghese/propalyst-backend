"""
Pydantic models for shortlist feature
"""
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional


class CreateShortlistRequest(BaseModel):
    """Request model for creating a new shortlist"""
    description: str = Field(..., description="Original user query or description")
    source: str = Field(..., description="Full URL of the property search source")
    properties: List[Dict[str, Any]] = Field(..., description="List of property objects to shortlist")


class ShortlistItem(BaseModel):
    """Model representing a shortlist entry"""
    id: str = Field(..., description="Unique identifier for the shortlist")
    description: str = Field(..., description="Original user query or description")
    source: str = Field(..., description="Full URL of the property search source")
    created_at: str = Field(..., description="ISO timestamp of creation")
    properties: List[Dict[str, Any]] = Field(..., description="List of shortlisted properties")


class ShortlistResponse(BaseModel):
    """Response model for shortlist operations"""
    success: bool = Field(..., description="Whether the operation was successful")
    data: Any = Field(None, description="Response data (shortlist item or list of items)")
    message: Optional[str] = Field(None, description="Optional message about the operation")
