"""
Lead Router
===========

API endpoints for lead extraction and management.
"""

import os
from datetime import datetime
from fastapi import APIRouter, HTTPException

from models.lead import (
    ExtractDetailedCriteriaResponse,
    CreateLeadRequest,
    CreateLeadResponse,
    DetailedCriteria
)
from services.lead import LeadService
from services.lead.persistence import LeadPersistenceService


router = APIRouter(
    prefix="/api",
    tags=["Lead Management"]
)


@router.get("/extract-detailed-criteria", response_model=ExtractDetailedCriteriaResponse)
async def extract_detailed_criteria(query: str):
    """
    Extract detailed property criteria and user journey information from natural language query.

    Extracts 15+ criteria including:
    - Property: BHK, budget, area, type, age, location
    - Proximity: near school, airport, hospital, mall (boolean)
    - User journey: possession timeline, time in market, agents contacted

    If location is detected, also returns nearby localities with distances using Google Search grounding.

    Example:
        GET /api/extract-detailed-criteria?query=Looking for 3BHK near Indiranagar with budget 4-7 crores

    Returns:
        - matched_criteria: Successfully extracted property and user criteria
        - missing_criteria: List of criteria not found in query
        - nearby_localities: Nearby areas (only if location detected)
    """
    print("\n" + "🔍" * 5)
    print("EXTRACT DETAILED CRITERIA ENDPOINT HIT")
    print(f"  Query: '{query}'")
    print("🔍" * 5 + "\n")

    try:
        # Check API key
        gemini_api_key = os.getenv("GEMINI_AI_API_KEY")
        if not gemini_api_key:
            raise HTTPException(
                status_code=500,
                detail="GEMINI_API_KEY not configured in environment"
            )

        # Extract criteria
        result = await LeadService.extract_detailed_criteria(query)

        if not result["success"]:
            raise HTTPException(
                status_code=500,
                detail=result["message"]
            )

        print(f"✅ Extraction complete: {len(result['data'].missing_criteria)} missing criteria")
        return result["data"]

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Extraction failed: {str(e)}"
        )


@router.post("/leads/create", response_model=CreateLeadResponse)
async def create_lead(request: CreateLeadRequest):
    """
    Create a lead from natural language query.

    Combines:
    - Extracted criteria (property + proximity + user journey)
    - Missing criteria (list of fields not found in query)
    - Matched property listings (real WhatsApp listings from Supabase)
    - Nearby localities (if location detected)

    Returns lead with unique ID and timestamp.

    Example:
        {
            "query": "3BHK in Whitefield, budget 5 crores, possession in 6 months"
        }

    Returns:
        - lead_id: Unique identifier for the lead
        - extracted_criteria: Detailed criteria extracted from query
        - missing_criteria: List of criteria not found in query (for follow-up)
        - matched_properties: WhatsApp listings matching criteria (up to 100)
        - nearby_localities: Nearby areas if location detected
        - created_at: ISO timestamp of creation
    """
    print("\n" + "📝" * 40)
    print("CREATE LEAD ENDPOINT HIT")
    print(f"  Query: '{request.query}'")
    print("📝" * 40 + "\n")

    try:
        # Check API key
        gemini_api_key = os.getenv("GEMINI_AI_API_KEY")
        if not gemini_api_key:
            raise HTTPException(
                status_code=500,
                detail="GEMINI_AI_API_KEY not configured in environment"
            )

        # Create lead
        result = await LeadService.create_lead(request.query)

        if not result["success"]:
            raise HTTPException(
                status_code=500,
                detail=result["message"]
            )

        print(f"✅ Lead created: {result['data'].lead_id}")
        return result["data"]

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Lead creation failed: {str(e)}"
        )


@router.post("/leads/{lead_id}/match-properties")
async def rematch_lead_properties(lead_id: str):
    """
    Re-match properties for an existing lead.

    Use cases:
    - Manual re-triggering after new WhatsApp listings arrive
    - Future: Cron job to refresh matches periodically

    Args:
        lead_id: UUID of the lead to re-match

    Returns:
        Updated matched_properties list
    """
    print(f"\n🔄 RE-MATCH ENDPOINT HIT for lead {lead_id}\n")

    try:
        # Load lead from JSON
        leads = LeadPersistenceService.load_leads()
        lead = next((l for l in leads if l["id"] == lead_id), None)

        if not lead:
            raise HTTPException(status_code=404, detail=f"Lead {lead_id} not found")

        # Reconstruct criteria from lead
        criteria = DetailedCriteria(**lead["extracted_criteria"])

        # Re-match properties
        matched_properties = await LeadService.match_properties_from_criteria(
            criteria,
            limit=100
        )

        # Transform to simplified format
        matched_properties_simplified = [
            {
                "id": prop.get("id"),
                "property_type": prop.get("property_type"),
                "location": prop.get("location"),
                "bedroom_count": prop.get("bedroom_count"),
                "area_sqft": prop.get("area_sqft"),
                "price": prop.get("price"),
                "price_text": prop.get("price_text"),
                "message_type": prop.get("message_type"),
                "agent_name": prop.get("agent_name"),
                "agent_contact": prop.get("agent_contact"),
                "message_date": prop.get("message_date"),
                "raw_message": (prop.get("raw_message")[:200] + "...") if prop.get("raw_message") and len(prop.get("raw_message", "")) > 200 else prop.get("raw_message")
            }
            for prop in matched_properties
        ]

        # Update lead in storage
        lead["matched_properties"] = matched_properties_simplified
        lead["last_matched_at"] = datetime.now().isoformat()
        LeadPersistenceService.save_leads(leads)

        return {
            "success": True,
            "lead_id": lead_id,
            "matched_count": len(matched_properties_simplified),
            "matched_properties": matched_properties_simplified[:10],  # Return first 10 for preview
            "message": f"Re-matched {len(matched_properties_simplified)} properties"
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error re-matching: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Re-match failed: {str(e)}"
        )
