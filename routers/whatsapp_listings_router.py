"""
WhatsApp Listings Router

API endpoints for managing extracted WhatsApp listings.
- Retry LLM reprocessing and preview results
- Update database with corrected data
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List

from services.whatsapp_combined_processor_service import WhatsAppCombinedProcessorService
from services.supabase_service import SupabaseService


router = APIRouter(
    prefix="/api/whatsapp-raw",
    tags=["WhatsApp Listings"]
)


class ListingUpdateRequest(BaseModel):
    """Request body for updating a listing with corrected data"""
    message_date: Optional[str] = None
    agent_contact: Optional[str] = None
    agent_name: Optional[str] = None
    raw_message: Optional[str] = None
    message_type: Optional[str] = None
    property_type: Optional[str] = None
    area_sqft: Optional[int] = None
    bedroom_count: Optional[int] = None
    price: Optional[float] = None
    price_text: Optional[str] = None
    location: Optional[str] = None
    project_name: Optional[str] = None
    furnishing_status: Optional[str] = None
    parking_count: Optional[int] = None
    parking_text: Optional[str] = None
    facing_direction: Optional[str] = None
    special_features: Optional[List[str]] = None
    llm_json: Optional[dict] = None


@router.post("/retry-listing/{listing_id}")
async def retry_listing_processing(
    listing_id: str
):
    """
    Reprocess a single extracted listing with LLM (PREVIEW only - no database update)

    **Use Case**: When the first LLM processing didn't work as expected, retry the extraction

    **What it does**:
    1. Query whatsapp_listing_data for the specified listing ID
    2. Get the source raw message from whatsapp_raw_messages
    3. Reprocess through WhatsAppCombinedProcessorService (LLM extraction)
    4. Return both old and new results for REVIEW (stored temporarily)
    5. **DOES NOT update database** - use `PATCH /listings/{listing_id}` to update
    6. User can call this again to retry if new results still look bad

    **Response**:
    ```json
    {
      "success": true,
      "listing_id": "uuid-here",
      "status": "preview",
      "old_result": { "current data in database" },
      "new_result": { "newly reprocessed data from LLM" },
      "changes": {
        "message_type": { "old": "garbage", "new": "supply_sale", "changed": true },
        "location": { "old": null, "new": "Whitefield", "changed": true }
      },
      "message": "Preview ready! Send the new_result data to PATCH /listings/{listing_id} to update, or call /retry-listing/{listing_id} again if still incorrect"
    }
    ```

    **Frontend Flow**:
    1. Display old_result and new_result side-by-side
    2. If approved: Send new_result data to `PATCH /listings/{listing_id}`
    3. If not approved: Call `POST /retry-listing/{listing_id}` again to reprocess
    """
    try:
        # Get the current listing
        listing_result = await SupabaseService.get_extracted_listing_by_id(listing_id)

        if not listing_result.get("success"):
            raise HTTPException(status_code=404, detail=f"Listing not found: {listing_id}")

        current_listing = listing_result.get("data")
        old_result = current_listing.copy()

        # Get the source raw message
        raw_message_id = current_listing.get("source_raw_message_id")
        if not raw_message_id:
            raise HTTPException(
                status_code=400,
                detail=f"Listing has no source raw message ID. Cannot retry."
            )

        # Get raw message data
        client = SupabaseService._get_client()
        raw_response = client.table("whatsapp_raw_messages")\
            .select("*")\
            .eq("id", raw_message_id)\
            .execute()

        if not raw_response.data or len(raw_response.data) == 0:
            raise HTTPException(
                status_code=404,
                detail=f"Source raw message not found: {raw_message_id}"
            )

        raw_message = raw_response.data[0]

        # Prepare message for reprocessing
        message_for_reprocessing = {
            'message_date': raw_message.get('message_date'),
            'sender_name': raw_message.get('sender_name'),
            'message_text': raw_message.get('message_text'),
            'source_file': raw_message.get('source_file'),
            'line_number': raw_message.get('line_number')
        }

        print(f"[WhatsAppListings] Retrying listing {listing_id} from raw message {raw_message_id}")

        # Reprocess with LLM
        split_result = await WhatsAppCombinedProcessorService.process_message(message_for_reprocessing)

        if not split_result or len(split_result) == 0:
            raise HTTPException(status_code=500, detail="LLM processing returned no results")

        # If the original was a split message, take the same split_index
        split_index = current_listing.get("llm_json", {}).get("split_index")

        # Use the split_index if available, otherwise use the first result
        if split_index and split_index <= len(split_result):
            new_processed = split_result[split_index - 1]
        else:
            new_processed = split_result[0]

        # Convert datetime to ISO string
        message_date = new_processed.get('message_date')
        if isinstance(message_date, datetime):
            message_date = message_date.isoformat()

        # Build new result object (frontend will send this back to approve endpoint)
        new_result = {
            "message_date": message_date,
            "agent_contact": new_processed.get('extracted_agent_contact'),
            "agent_name": new_processed.get('extracted_agent_name'),
            "raw_message": new_processed.get('message_text'),
            "message_type": new_processed.get('message_type'),
            "property_type": new_processed.get('property_type'),
            "area_sqft": new_processed.get('area_sqft'),
            "bedroom_count": new_processed.get('bedroom_count'),
            "price": new_processed.get('price'),
            "price_text": new_processed.get('price_text'),
            "location": new_processed.get('location'),
            "project_name": new_processed.get('project_name'),
            "furnishing_status": new_processed.get('furnishing_status'),
            "parking_count": new_processed.get('parking_count'),
            "parking_text": new_processed.get('parking_text'),
            "facing_direction": new_processed.get('facing_direction'),
            "special_features": new_processed.get('special_features', []),
            "llm_json": {
                "message_type": new_processed.get('message_type'),
                "split_from_original": new_processed.get('split_from_original', False),
                "split_index": new_processed.get('split_index'),
                "reprocessed_at": datetime.now().isoformat(),
                "reprocessed_split_count": len(split_result)
            }
        }

        print(f"[WhatsAppListings] ✓ Reprocessing complete for listing {listing_id}")
        print(f"[WhatsAppListings]   Old message_type: {old_result.get('message_type')}")
        print(f"[WhatsAppListings]   New message_type: {new_result.get('message_type')}")

        # Build detailed changes
        changes = {}
        for key in ['message_type', 'agent_name', 'location', 'property_type', 'bedroom_count', 'price']:
            if old_result.get(key) != new_result.get(key):
                changes[key] = {
                    "old": old_result.get(key),
                    "new": new_result.get(key),
                    "changed": True
                }

        return {
            "success": True,
            "listing_id": listing_id,
            "status": "preview",
            "old_result": old_result,
            "new_result": new_result,
            "changes": changes if changes else {"note": "No changes - extraction is the same"},
            "message": "Preview ready! Send the new_result to /approve-listing/{listing_id} in request body to update, or retry if still incorrect."
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[WhatsAppListings] ✗ Error retrying listing: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/listings/{listing_id}")
async def update_listing(
    listing_id: str,
    update_data: ListingUpdateRequest
):
    """
    Update a listing with corrected data

    **Use Case**: After reviewing the LLM reprocessed data from `/retry-listing/{listing_id}`

    **What it does**:
    1. Receives the updated listing data from frontend (from `/retry-listing` new_result)
    2. Updates the database with the new LLM-extracted data
    3. Returns confirmation of database update

    **Request Body**: Send the `new_result` data from `/retry-listing` response
    ```json
    {
      "message_type": "supply_sale",
      "location": "Whitefield",
      "agent_name": "John Doe",
      ...
    }
    ```

    **Response**:
    ```json
    {
      "success": true,
      "listing_id": "uuid-here",
      "status": "updated",
      "updated_record": { "updated fields with new extraction" },
      "message": "Listing updated successfully"
    }
    ```
    """
    try:
        # Verify listing exists
        listing_result = await SupabaseService.get_extracted_listing_by_id(listing_id)
        if not listing_result.get("success"):
            raise HTTPException(status_code=404, detail=f"Listing not found: {listing_id}")

        # Convert update data to dict, removing None values
        update_dict = update_data.dict(exclude_none=True)

        if not update_dict:
            raise HTTPException(status_code=400, detail="No update data provided")

        print(f"[WhatsAppListings] Updating listing {listing_id} with {len(update_dict)} fields")

        # Update the database
        update_result = await SupabaseService.update_extracted_listing(listing_id, update_dict)

        if not update_result.get("success"):
            raise HTTPException(status_code=500, detail="Failed to update listing in database")

        updated_record = update_result.get("data")

        print(f"[WhatsAppListings] ✓ Updated listing {listing_id}")

        return {
            "success": True,
            "listing_id": listing_id,
            "status": "updated",
            "updated_record": updated_record,
            "message": "Listing updated successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[WhatsAppListings] ✗ Error updating listing: {e}")
        raise HTTPException(status_code=500, detail=str(e))
