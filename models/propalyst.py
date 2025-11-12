"""
Propalyst Models
================

Pydantic models for Propalyst endpoints.
"""

from pydantic import BaseModel


class PropalystChatRequest(BaseModel):
    """
    Request model for Propalyst conversational endpoint.

    Attributes:
        session_id (str): Unique session identifier (UUID)
        user_input (str | None): User's answer (None for initial request)
        field (str | None): Which field this answer is for

    Examples:
        Initial request (start conversation):
        {
            "session_id": "abc-123",
            "user_input": null
        }

        User answering Q1:
        {
            "session_id": "abc-123",
            "user_input": "Whitefield",
            "field": "work_location"
        }

        User answering Q2:
        {
            "session_id": "abc-123",
            "user_input": "Yes",
            "field": "has_kids"
        }
    """
    session_id: str
    user_input: str | None = None
    field: str | None = None

    class Config:
        schema_extra = {
            "example": {
                "session_id": "abc-123",
                "user_input": "Whitefield",
                "field": "work_location"
            }
        }


class PropalystChatResponse(BaseModel):
    """
    Response model for Propalyst chat endpoint.

    Attributes:
        component (dict | None): UI component to show
        message (str): Agent's message to user
        session_id (str): Session identifier
        current_step (int): Current question number (1-5)
        completed (bool): Whether all questions answered

    Example:
        {
            "component": {
                "type": "TextInput",
                "props": {
                    "field": "work_location",
                    "placeholder": "e.g., Whitefield"
                }
            },
            "message": "Hi! Where do you work?",
            "session_id": "abc-123",
            "current_step": 1,
            "completed": false
        }
    """
    component: dict | None
    message: str
    session_id: str
    current_step: int
    completed: bool


class PropalystSummaryRequest(BaseModel):
    """
    Request model for generating conversation summary.

    Attributes:
        session_id (str): Unique session identifier

    Example:
        {
            "session_id": "abc-123"
        }
    """
    session_id: str


class PropalystSummaryResponse(BaseModel):
    """
    Response model for conversation summary.

    Attributes:
        summary (str): LLM-generated detailed summary
        session_id (str): Session identifier

    Example:
        {
            "summary": "Based on our conversation, you work in Whitefield...",
            "session_id": "abc-123"
        }
    """
    summary: str
    session_id: str


class PropalystAreasRequest(BaseModel):
    """
    Request model for fetching recommended areas.

    Attributes:
        session_id (str): Unique session identifier

    Example:
        {
            "session_id": "abc-123"
        }
    """
    session_id: str


class PropalystAreasResponse(BaseModel):
    """
    Response model for recommended areas.

    Attributes:
        areas (list): List of recommended area objects
        session_id (str): Session identifier

    Example:
        {
            "areas": [
                {
                    "areaName": "Whitefield",
                    "image": "https://...",
                    "childFriendlyScore": 9,
                    "schoolsNearby": 12,
                    "averageCommute": "15-20 min",
                    "budgetRange": "₹60K - ₹85K",
                    "highlights": ["IT Hub", "Great Schools", "Metro Access"]
                }
            ],
            "session_id": "abc-123"
        }
    """
    areas: list
    session_id: str




