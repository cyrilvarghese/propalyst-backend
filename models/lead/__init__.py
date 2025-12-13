"""
Lead Models Module

Pydantic models for lead extraction and management:
- PropertyCriteria: Property search details
- ProximityPreferences: Amenity preferences
- UserJourney: User timeline and context
- Request/Response models for API endpoints
"""

from .schemas import (
    PropertyCriteria,
    ProximityPreferences,
    UserJourney,
    DetailedCriteria,
    NearbyLocality,
    ExtractDetailedCriteriaRequest,
    ExtractDetailedCriteriaResponse,
    CreateLeadRequest,
    CreateLeadResponse
)

__all__ = [
    "PropertyCriteria",
    "ProximityPreferences",
    "UserJourney",
    "DetailedCriteria",
    "NearbyLocality",
    "ExtractDetailedCriteriaRequest",
    "ExtractDetailedCriteriaResponse",
    "CreateLeadRequest",
    "CreateLeadResponse"
]
