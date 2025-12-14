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
    DetailedCriteria,
    NearbyLocality,
    ListLeadsResponse,
    UpdateLeadRequest,
    UpdateLeadStatusRequest,
    UpdateLeadMatchedPropertiesRequest
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


@router.get("/leads", response_model=ListLeadsResponse)
async def list_leads():
    """
    List all leads.

    Returns:
        - leads: Array of complete lead objects with all details
        - total_count: Total number of leads
    """
    try:
        leads_data = LeadPersistenceService.load_leads()

        # Convert raw lead data to CreateLeadResponse objects (full lead data)
        lead_objects = []
        for lead in leads_data:
            lead_obj = CreateLeadResponse(
                lead_id=lead["id"],
                query=lead.get("query", ""),
                extracted_criteria=DetailedCriteria(**lead["extracted_criteria"]),
                missing_criteria=lead.get("missing_criteria", []),
                matched_properties=lead.get("matched_properties", []),
                nearby_localities=lead.get("nearby_localities", []),
                created_at=lead["created_at"],
                status=lead.get("status", "new")
            )
            lead_objects.append(lead_obj)

        return ListLeadsResponse(
            leads=lead_objects,
            total_count=len(lead_objects)
        )

    except Exception as e:
        print(f"❌ Error listing leads: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list leads: {str(e)}"
        )


@router.get("/leads/{lead_id}", response_model=CreateLeadResponse)
async def get_lead(lead_id: str):
    """
    Get a specific lead by ID.

    Args:
        lead_id: UUID of the lead to retrieve

    Returns:
        Complete lead object with all details:
        - lead_id: Unique identifier
        - extracted_criteria: Property, proximity, and user journey criteria
        - missing_criteria: Criteria not found in query
        - matched_properties: WhatsApp listings matching the criteria
        - nearby_localities: Nearby areas if location was detected
        - created_at: ISO timestamp of creation
        - status: Lead status
    """
    try:
        leads_data = LeadPersistenceService.load_leads()

        # Find lead by ID
        lead = next((l for l in leads_data if l["id"] == lead_id), None)

        if not lead:
            raise HTTPException(
                status_code=404,
                detail=f"Lead {lead_id} not found"
            )

        # Convert to CreateLeadResponse
        lead_obj = CreateLeadResponse(
            lead_id=lead["id"],
            query=lead.get("query", ""),
            extracted_criteria=DetailedCriteria(**lead["extracted_criteria"]),
            missing_criteria=lead.get("missing_criteria", []),
            matched_properties=lead.get("matched_properties", []),
            nearby_localities=lead.get("nearby_localities", []),
            created_at=lead["created_at"],
            status=lead.get("status", "new")
        )

        return lead_obj

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error retrieving lead: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve lead: {str(e)}"
        )


@router.put("/leads/{lead_id}", response_model=CreateLeadResponse)
async def update_lead(lead_id: str, request: UpdateLeadRequest):
    """
    Update a lead by re-extracting criteria and re-matching properties.

    Takes a new query, extracts criteria, and matches properties again.
    Preserves: lead_id, created_at, and nearby_localities from existing lead.
    Updates: query, extracted_criteria, missing_criteria, matched_properties, status.

    Args:
        lead_id: UUID of the lead to update
        request: UpdateLeadRequest with new query and optional status

    Returns:
        Updated lead object with new criteria and matched properties
    """
    try:
        leads_data = LeadPersistenceService.load_leads()

        # Find lead by ID
        lead = next((l for l in leads_data if l["id"] == lead_id), None)

        if not lead:
            raise HTTPException(
                status_code=404,
                detail=f"Lead {lead_id} not found"
            )

        # Preserve original values
        original_created_at = lead["created_at"]
        preserved_nearby_localities = lead.get("nearby_localities", [])

        print(f"\n[UpdateLead] 🔄 Re-extracting criteria and re-matching for lead {lead_id}")
        print(f"[UpdateLead] Query: {request.query}")

        # STEP 1: Extract criteria from new query
        extraction_result = await LeadService.extract_detailed_criteria(request.query)
        if not extraction_result["success"]:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to extract criteria: {extraction_result['message']}"
            )

        criteria_response = extraction_result["data"]
        criteria = criteria_response.matched_criteria

        # STEP 2: Match properties from Supabase
        matched_properties = await LeadService.match_properties_from_criteria(criteria, limit=100)
        print(f"[UpdateLead] ✓ Matched {len(matched_properties)} properties")

        # STEP 3: Update lead with new extracted data
        lead["query"] = request.query
        lead["extracted_criteria"] = criteria.dict()
        lead["missing_criteria"] = criteria_response.missing_criteria
        lead["matched_properties"] = [prop.dict() for prop in matched_properties]
        lead["nearby_localities"] = preserved_nearby_localities  # Keep existing localities
        lead["last_updated_at"] = datetime.now().isoformat()

        # Optional: Update status if provided
        if request.status:
            lead["status"] = request.status
        else:
            # If status not provided, keep existing status
            pass

        # STEP 4: Save updated leads
        LeadPersistenceService.save_leads(leads_data)

        # Return updated lead
        lead_obj = CreateLeadResponse(
            lead_id=lead["id"],
            query=lead["query"],
            extracted_criteria=DetailedCriteria(**lead["extracted_criteria"]),
            missing_criteria=lead["missing_criteria"],
            matched_properties=lead["matched_properties"],
            nearby_localities=[NearbyLocality(**loc) for loc in lead.get("nearby_localities", [])],
            created_at=original_created_at,
            status=lead.get("status", "new")
        )

        print(f"✅ Lead {lead_id} updated successfully")
        print(f"   - Query updated: {request.query}")
        print(f"   - Criteria re-extracted: {len([f for f in criteria.property.__dict__.values() if f is not None])} fields")
        print(f"   - Properties re-matched: {len(matched_properties)} results")
        print(f"   - Nearby localities preserved: {len(preserved_nearby_localities)} areas\n")

        return lead_obj

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error updating lead: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update lead: {str(e)}"
        )


@router.put("/leads/{lead_id}/status", response_model=CreateLeadResponse)
async def update_lead_status(lead_id: str, request: UpdateLeadStatusRequest):
    """
    Update only the status of a lead.

    Use this endpoint to change lead status without re-extracting criteria or re-matching properties.

    Args:
        lead_id: UUID of the lead to update
        request: UpdateLeadStatusRequest with new status

    Returns:
        Updated lead object
    """
    try:
        leads_data = LeadPersistenceService.load_leads()

        # Find lead by ID
        lead = next((l for l in leads_data if l["id"] == lead_id), None)

        if not lead:
            raise HTTPException(
                status_code=404,
                detail=f"Lead {lead_id} not found"
            )

        # Update status
        lead["status"] = request.status
        lead["last_updated_at"] = datetime.now().isoformat()

        # Save updated leads
        LeadPersistenceService.save_leads(leads_data)

        # Return updated lead
        lead_obj = CreateLeadResponse(
            lead_id=lead["id"],
            query=lead.get("query", ""),
            extracted_criteria=DetailedCriteria(**lead["extracted_criteria"]),
            missing_criteria=lead.get("missing_criteria", []),
            matched_properties=lead.get("matched_properties", []),
            nearby_localities=[NearbyLocality(**loc) for loc in lead.get("nearby_localities", [])],
            created_at=lead["created_at"],
            status=lead["status"]
        )

        print(f"✅ Lead {lead_id} status updated to '{request.status}'")

        return lead_obj

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error updating lead status: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update lead status: {str(e)}"
        )


@router.put("/leads/{lead_id}/matched-properties")
async def update_lead_matched_properties(lead_id: str, request: UpdateLeadMatchedPropertiesRequest):
    """
    Update matched properties for a lead.

    Args:
        lead_id: UUID of the lead
        request: List of matched property objects to update

    Returns:
        Success message with updated property count
    """
    try:
        leads_data = LeadPersistenceService.load_leads()

        # Find lead by ID
        lead = next((l for l in leads_data if l["id"] == lead_id), None)

        if not lead:
            raise HTTPException(
                status_code=404,
                detail=f"Lead {lead_id} not found"
            )

        # Update matched properties
        lead["matched_properties"] = request.matched_properties
        lead["last_updated_at"] = datetime.now().isoformat()

        # Save updated leads
        LeadPersistenceService.save_leads(leads_data)

        print(f"✅ Matched properties updated for lead {lead_id}: {len(request.matched_properties)} properties")

        return {
            "success": True,
            "lead_id": lead_id,
            "matched_count": len(request.matched_properties),
            "message": f"Updated {len(request.matched_properties)} matched properties for lead {lead_id}"
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error updating matched properties: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update matched properties: {str(e)}"
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
    print("\n" + "=" * 80)
    print("📝 CREATE LEAD REQUEST")
    print("=" * 80)
    print(f"Query: {request.query}")
    print("=" * 80 + "\n")

    try:
        # Check API key
        gemini_api_key = os.getenv("GEMINI_AI_API_KEY")
        if not gemini_api_key:
            print("❌ GEMINI_API_KEY not configured")
            raise HTTPException(
                status_code=500,
                detail="GEMINI_AI_API_KEY not configured in environment"
            )

        print("[1/3] ⚙️  Extracting criteria from query...")
        # Create lead
        result = await LeadService.create_lead(request.query)

        if not result["success"]:
            print(f"❌ Criteria extraction failed: {result['message']}")
            raise HTTPException(
                status_code=500,
                detail=result["message"]
            )

        lead_data = result["data"]
        print(f"[2/3] ✅ Criteria extracted successfully")
        print(f"      - Matched criteria fields: {len([f for f in lead_data.extracted_criteria.property.__dict__.values() if f is not None])} found")
        print(f"      - Missing criteria: {', '.join(lead_data.missing_criteria) if lead_data.missing_criteria else 'None'}")

        print(f"[3/3] ✅ Properties matched: {len(lead_data.matched_properties)} results")
        if lead_data.nearby_localities:
            print(f"      - Nearby localities: {', '.join([f'{loc.name} ({loc.distance_km}km)' for loc in lead_data.nearby_localities])}")

        print("\n" + "=" * 80)
        print(f"✅ LEAD CREATED SUCCESSFULLY")
        print(f"   Lead ID: {lead_data.lead_id}")
        print(f"   Status: {lead_data.status}")
        print(f"   Created: {lead_data.created_at}")
        print("=" * 80 + "\n")

        return lead_data

    except HTTPException:
        raise
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        print("=" * 80 + "\n")
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

        # Convert Pydantic models to dicts for storage
        matched_properties_dicts = [prop.dict() for prop in matched_properties]

        # Update lead in storage
        lead["matched_properties"] = matched_properties_dicts
        lead["last_matched_at"] = datetime.now().isoformat()
        LeadPersistenceService.save_leads(leads)

        return {
            "success": True,
            "lead_id": lead_id,
            "matched_count": len(matched_properties),
            "matched_properties": matched_properties_dicts[:10],  # Return first 10 for preview
            "message": f"Re-matched {len(matched_properties)} properties"
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error re-matching: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Re-match failed: {str(e)}"
        )
