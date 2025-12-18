"""
Lead Models
===========

Pydantic models for lead extraction and management.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class PropertyCriteria(BaseModel):
    """Property search criteria extracted from query"""

    bhk: Optional[int] = Field(
        None,
        description="Number of bedrooms (1, 2, 3, etc.)"
    )

    budget_min: Optional[float] = Field(
        None,
        description="Minimum budget in crores"
    )

    budget_max: Optional[float] = Field(
        None,
        description="Maximum budget in crores"
    )

    area_sqft_min: Optional[float] = Field(
        None,
        description="Minimum area in square feet"
    )

    area_sqft_max: Optional[float] = Field(
        None,
        description="Maximum area in square feet"
    )

    property_type: Optional[str] = Field(
        None,
        description="Type: apartment, villa, independent house, etc."
    )

    property_age: Optional[str] = Field(
        None,
        description="Age: new, resale, under construction, years old"
    )

    location: Optional[str] = Field(
        None,
        description="Primary location/locality"
    )

    req_type: Optional[str] = Field(
        None,
        description="Requirement type: supply_sale, supply_rent, demand_buy, demand_rent"
    )

    # Multiple locations support
    locations: List[str] = Field(
        default_factory=list,
        description="Multiple acceptable locations (use if query mentions several areas)"
    )

    # Plot size (for villas, independent houses, plots)
    plot_size_min: Optional[float] = Field(
        None,
        description="Minimum plot size in sqft"
    )

    plot_size_max: Optional[float] = Field(
        None,
        description="Maximum plot size in sqft"
    )

    # Built-up area (different from plot size)
    built_up_area_min: Optional[float] = Field(
        None,
        description="Minimum built-up area in sqft"
    )

    built_up_area_max: Optional[float] = Field(
        None,
        description="Maximum built-up area in sqft"
    )

    # Property status
    property_status: Optional[str] = Field(
        None,
        description="ready_to_move, under_construction, new_launch"
    )

    # Furnishing status
    furnishing_status: Optional[str] = Field(
        None,
        description="unfurnished, semi_furnished, fully_furnished, bare_shell, warm_shell"
    )

    # Special features (catch-all)
    special_features: List[str] = Field(
        default_factory=list,
        description="Special requirements: maids_room, garden, pool, gym, etc. Also includes complex layouts"
    )


class ProximityPreferences(BaseModel):
    """Boolean preferences for proximity to amenities"""

    near_school: bool = Field(
        default=False,
        description="Wants property near schools"
    )

    near_airport: bool = Field(
        default=False,
        description="Wants property near airport"
    )

    near_hospital: bool = Field(
        default=False,
        description="Wants property near hospital"
    )

    near_shopping_mall: bool = Field(
        default=False,
        description="Wants property near shopping mall"
    )


class UserJourney(BaseModel):
    """User journey and timeline information"""

    possession_timeline: Optional[str] = Field(
        None,
        description="When needs possession: immediate, 6 months, 1 year, flexible"
    )

    time_in_market: Optional[str] = Field(
        None,
        description="How long searching: just started, 2 months, 6 months, etc."
    )

    agents_contacted: Optional[int] = Field(
        None,
        description="Number of agents already contacted"
    )

    work_locations: List[str] = Field(
        default_factory=list,
        description="User's work location(s) - areas where they commute for work"
    )


class DetailedCriteria(BaseModel):
    """Complete criteria extraction result"""

    property: PropertyCriteria
    proximity: ProximityPreferences
    user_journey: UserJourney


class NearbyLocality(BaseModel):
    """Nearby locality with distance"""

    name: str = Field(
        ...,
        description="Locality name"
    )

    distance_km: float = Field(
        ...,
        description="Distance in kilometers"
    )


class ExtractDetailedCriteriaRequest(BaseModel):
    """Request model for criteria extraction"""

    query: str = Field(
        ...,
        min_length=1,
        description="Natural language query",
        examples=["Looking for 3BHK near Indiranagar with budget 4-7 crores"]
    )


class ExtractDetailedCriteriaResponse(BaseModel):
    """Response with extracted criteria and nearby localities"""

    matched_criteria: DetailedCriteria = Field(
        ...,
        description="Successfully extracted criteria"
    )

    missing_criteria: List[str] = Field(
        ...,
        description="List of criteria not found in query"
    )

    nearby_localities: List[NearbyLocality] = Field(
        default_factory=list,
        description="Nearby localities (empty if location not detected or search failed)"
    )


class CreateLeadRequest(BaseModel):
    """Request to create lead from query"""

    query: str = Field(
        ...,
        min_length=1,
        description="Natural language query",
        examples=["3BHK in Whitefield, budget 5 crores, possession in 6 months"]
    )

    name: Optional[str] = Field(
        None,
        min_length=1,
        description="Name of the lead (person's name). Optional - defaults to 'Unknown Lead'"
    )

    contact_number: Optional[str] = Field(
        None,
        min_length=10,
        description="Contact number of the lead. Optional - defaults to 'Not provided'"
    )


class CreateLeadResponse(BaseModel):
    """Lead creation response"""

    lead_id: str = Field(
        ...,
        description="Unique lead identifier"
    )

    query: str = Field(
        ...,
        description="Original natural language query"
    )

    name: str = Field(
        ...,
        description="Name of the lead (person's name)"
    )

    contact_number: str = Field(
        ...,
        description="Contact number of the lead"
    )

    extracted_criteria: DetailedCriteria = Field(
        ...,
        description="Extracted property criteria and user journey"
    )

    missing_criteria: List[str] = Field(
        default_factory=list,
        description="List of criteria not found in query"
    )

    matched_properties: List[Dict[str, Any]] = Field(
        ...,
        description="Matched property listings (dummy data initially)"
    )

    nearby_localities: List[NearbyLocality] = Field(
        default_factory=list,
        description="Nearby localities if location was detected (empty if not found)"
    )

    created_at: str = Field(
        ...,
        description="ISO timestamp of lead creation"
    )

    status: str = Field(
        default="new",
        description="Lead status: new, in_progress, matched, contacted, closed"
    )


class UpdateLeadRequest(BaseModel):
    """Request to update a lead - re-extract criteria and re-match properties"""

    query: str = Field(
        ...,
        min_length=1,
        description="Natural language query to re-extract criteria and re-match properties"
    )

    name: Optional[str] = Field(
        None,
        min_length=1,
        description="Optional: Update name of the lead"
    )

    contact_number: Optional[str] = Field(
        None,
        min_length=10,
        description="Optional: Update contact number of the lead"
    )

    status: Optional[str] = Field(
        None,
        description="Optional: Update lead status (new, in_progress, matched, contacted, closed)"
    )


class UpdateLeadStatusRequest(BaseModel):
    """Request to update only the status of a lead"""

    status: str = Field(
        ...,
        description="Lead status: new, in_progress, matched, contacted, closed"
    )


class UpdateLeadMatchedPropertiesRequest(BaseModel):
    """Request to update matched properties for a lead"""

    matched_properties: List[Dict[str, Any]] = Field(
        ...,
        description="Updated list of matched property objects"
    )


class ListLeadsResponse(BaseModel):
    """Response for listing all leads"""

    leads: List[CreateLeadResponse] = Field(
        default_factory=list,
        description="List of complete lead objects"
    )

    total_count: int = Field(
        ...,
        description="Total number of leads"
    )
