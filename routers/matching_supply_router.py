"""
Matching Supply Router
======================

API endpoints for creating matching supply records from WhatsApp listings.
"""

from fastapi import APIRouter, HTTPException
from models.matching_supply import (
    MatchingSupplyCreateRequest,
    MatchingSupplyCreateResponse
)
from services.supabase_service import SupabaseService

router = APIRouter(
    prefix="/api/matching-supply",
    tags=["Matching Supply"]
)


@router.post("", response_model=MatchingSupplyCreateResponse)
async def create_matching_supply(request: MatchingSupplyCreateRequest):
    """
    Create a new matching supply record from WhatsApp listing

    Process:
    1. Fetch WhatsApp listing by whatsapp_listing_id
    2. Generate short_desc using LLM (with fallback logic)
    3. Map fields: supply_id (uuid→text), agent_name, agent_phone
    4. Check for duplicate (lead_id + supply_id)
    5. Insert into matching_supply table with match_status='Identified'

    Error Handling:
        - 404: WhatsApp listing not found
        - 400: Duplicate match already exists
        - 400: Lead ID doesn't exist (FK violation)
        - 500: LLM or database errors

    Request Body:
        ```json
        {
            "lead_id": 12345,
            "whatsapp_listing_id": "550e8400-e29b-41d4-a716-446655440000"
        }
        ```

    Example:
        POST /api/matching-supply
        {
            "lead_id": 123,
            "whatsapp_listing_id": "550e8400-e29b-41d4-a716-446655440000"
        }
    """
    try:
        print(f"[API-MatchingSupply] Creating match: lead_id={request.lead_id}, listing_id={request.whatsapp_listing_id}")

        # Step 1: Fetch WhatsApp listing by ID
        listing_result = await SupabaseService.get_extracted_listing_by_id(request.whatsapp_listing_id)

        if not listing_result.get("success"):
            raise HTTPException(
                status_code=404,
                detail=f"WhatsApp listing not found: {request.whatsapp_listing_id}"
            )

        listing_data = listing_result.get("data")

        # Step 2: Check for duplicate match (lead_id + supply_id)
        supply_id = str(listing_data.get("id"))  # Convert UUID to text

        duplicate_exists = await SupabaseService.check_matching_supply_duplicate(
            lead_id=request.lead_id,
            supply_id=supply_id
        )

        if duplicate_exists:
            raise HTTPException(
                status_code=400,
                detail=f"Match already exists for lead {request.lead_id} and supply {supply_id[:20]}..."
            )

        # Step 3: Generate short_desc using LLM (with fallback)
        short_desc = await SupabaseService.generate_short_desc(listing_data)

        # Step 4: Map fields and prepare insert data
        match_data = {
            "lead_id": request.lead_id,
            "supply_id": supply_id,  # UUID as text
            "agent_name": listing_data.get("agent_name"),
            "agent_phone": listing_data.get("agent_contact"),  # Note: agent_contact in listing
            "short_desc": short_desc,
            "match_status": "Identified"  # Default status
        }

        # Step 5: Insert into matching_supply table
        insert_result = await SupabaseService.insert_matching_supply(match_data)

        if not insert_result.get("success"):
            error_msg = insert_result.get("message", "Unknown error")
            raise HTTPException(
                status_code=400,
                detail=error_msg
            )

        print(f"[API-MatchingSupply] ✓ Successfully created match for lead {request.lead_id}")

        return MatchingSupplyCreateResponse(
            success=True,
            data=insert_result.get("data"),
            message=insert_result.get("message")
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"[API-MatchingSupply] ✗ Error creating match: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error creating matching supply: {str(e)}"
        )
