"""
WhatsApp Listing Router
========================

API endpoints for WhatsApp listing data extraction operations.
"""

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from typing import Optional
import json
import asyncio
from models.whatsapp_listing import WhatsAppListingExtractionResponse
from services.whatsapp_listing_extraction_service import WhatsAppListingExtractionService
from services.supabase_service import SupabaseService

router = APIRouter(
    prefix="/api/whatsapp-listings",
    tags=["WhatsApp Listing Extraction"]
)


@router.post("/extract-all-stream")
async def extract_all_listings_stream(
    batch_size: int = Query(100, description="Number of messages to process in this batch", ge=1, le=500)
):
    """
    Extract structured data from unprocessed WhatsApp messages (streaming)

    Simple database-driven approach:
    - Fetches batch_size unprocessed messages using LEFT JOIN
    - Processes each with LLM
    - Inserts to whatsapp_listing_data
    - Database automatically tracks progress (no JSON files)

    Args:
        batch_size: Number of messages to process (1-500, default: 100)

    Returns:
        StreamingResponse with real-time updates

    Examples:
        POST /api/whatsapp-listings/extract-all-stream?batch_size=10
        POST /api/whatsapp-listings/extract-all-stream?batch_size=100

    Event format:
        data: {"type": "start", "batch_size": 10}
        data: {"type": "progress", "message_id": "uuid", "status": "completed", "message_type": "supply_sale"}
        data: {"type": "complete", "summary": {"messages_extracted": 8, "messages_skipped": 2}}
    """
    async def event_generator():
        try:
            print(f"[API-WhatsAppListing] Starting batch extraction ({batch_size} messages)...")

            # Fetch batch of unprocessed messages (newest first)
            batch = await SupabaseService.get_unprocessed_messages(limit=batch_size, offset=0)

            if not batch:
                # Named event for "complete"
                yield f"event: complete\ndata: {json.dumps({'message': 'No unprocessed messages found!', 'batch_size': 0})}\n\n"
                return

            print(f"[API-WhatsAppListing] Retrieved {len(batch)} unprocessed messages")

            # Named event for "start"
            yield f"event: start\ndata: {json.dumps({'batch_size': len(batch)})}\n\n"

            # Simple counters (no file I/O)
            messages_extracted = 0
            messages_skipped = 0
            messages_failed = 0

            # Process each message in this batch
            for idx, message in enumerate(batch, 1):
                message_id = message.get("id")

                try:
                    raw_message = message.get("raw_message", "")

                    # Skip media messages - don't send to LLM, mark as garbage
                    if "<Media omitted>" in raw_message or raw_message.strip() == "":
                        messages_skipped += 1
                        print(f"[WhatsAppListing] Skipping media/empty message {message_id}")

                        # Insert minimal data as garbage type
                        listing_data = {
                            "source_message_id": message_id,
                            "message_date": message.get("message_date"),
                            "agent_contact": message.get("agent_contact"),
                            "agent_name": message.get("agent_name"),
                            "company_name": message.get("company_name"),
                            "raw_message": raw_message,
                            "message_type": "garbage",
                            "property_type": None,
                            "llm_json": {"message_type": "garbage", "reason": "media_omitted"}
                        }

                        result = await SupabaseService.insert_extracted_listing(listing_data)

                        # Named event for "progress"
                        event_data = {
                            'message_id': message_id,
                            'status': 'skipped',
                            'message_type': 'garbage',
                            'reason': 'media_omitted',
                            'progress': f'{idx}/{len(batch)}'
                        }
                        yield f"event: progress\ndata: {json.dumps(event_data)}\n\n"
                        continue  # Skip to next message without calling LLM

                    # Extract with LLM (pass message_id for logging)
                    llm_output = await WhatsAppListingExtractionService.extract_single_message(raw_message, message_id)

                    # Check if message type is relevant (supply/demand)
                    relevant_types = ['supply_sale', 'supply_rent', 'demand_buy', 'demand_rent']
                    is_relevant = llm_output.message_type in relevant_types

                    # Prepare data for insertion
                    # For non-relevant types (greeting/garbage/generic): store minimal data
                    # For relevant types: store full extracted data
                    if is_relevant:
                        # Full data for supply/demand messages
                        listing_data = {
                            "source_message_id": message_id,
                            "message_date": message.get("message_date"),
                            "agent_contact": llm_output.agent_contact or message.get("agent_contact"),
                            "agent_name": llm_output.agent_name or message.get("agent_name"),
                            "company_name": message.get("company_name"),
                            "raw_message": raw_message,
                            "message_type": llm_output.message_type,
                            "property_type": llm_output.property_type,
                            "area_sqft": llm_output.area_sqft,
                            "price": llm_output.price,
                            "price_text": llm_output.price_text,
                            "location": llm_output.location,
                            "project_name": llm_output.project_name,
                            "furnishing_status": llm_output.furnishing_status,
                            "parking_count": llm_output.parking_count,
                            "parking_text": llm_output.parking_text,
                            "facing_direction": llm_output.facing_direction,
                            "special_features": llm_output.special_features if llm_output.special_features else [],
                            "llm_json": {
                                "message_type": llm_output.message_type,
                                "agent_name": llm_output.agent_name,
                                "agent_contact": llm_output.agent_contact,
                                "property_type": llm_output.property_type,
                                "location": llm_output.location,
                                "price": llm_output.price
                            }
                        }
                    else:
                        # Minimal data for greeting/garbage/generic_info (just tracking)
                        messages_skipped += 1
                        listing_data = {
                            "source_message_id": message_id,
                            "message_date": message.get("message_date"),
                            "agent_contact": message.get("agent_contact"),
                            "agent_name": message.get("agent_name"),
                            "company_name": message.get("company_name"),
                            "raw_message": raw_message,
                            "message_type": llm_output.message_type,
                            "property_type": None,
                            "area_sqft": None,
                            "price": None,
                            "price_text": None,
                            "location": None,
                            "project_name": None,
                            "furnishing_status": None,
                            "parking_count": None,
                            "parking_text": None,
                            "facing_direction": None,
                            "special_features": [],
                            "llm_json": {"message_type": llm_output.message_type}
                        }

                    # Insert to database (all messages, but with different data)
                    result = await SupabaseService.insert_extracted_listing(listing_data)

                    if result.get("success"):
                        if is_relevant:
                            messages_extracted += 1
                            status = 'completed'
                            print(f"[WhatsAppListing] ✓ Extracted {message_id} - type: {llm_output.message_type}")
                        else:
                            messages_skipped += 1
                            status = 'skipped'
                            print(f"[WhatsAppListing] ⊘ Classified as {llm_output.message_type}, stored minimal data")

                        # Named event for "progress"
                        event_data = {
                            'message_id': message_id,
                            'status': status,
                            'progress': f'{idx}/{len(batch)}',
                            'message_type': llm_output.message_type,
                            'is_relevant': is_relevant
                        }
                        yield f"event: progress\ndata: {json.dumps(event_data)}\n\n"

                    else:
                        error_msg = result.get('message', 'Unknown error')
                        messages_failed += 1

                        # Named event for "progress" (failed status)
                        event_data = {
                            'message_id': message_id,
                            'status': 'failed',
                            'error': str(error_msg),
                            'progress': f'{idx}/{len(batch)}'
                        }
                        yield f"event: progress\ndata: {json.dumps(event_data)}\n\n"

                except Exception as e:
                    error_msg = str(e)
                    messages_failed += 1

                    # Named event for "progress" (failed status)
                    event_data = {
                        'message_id': message_id,
                        'status': 'failed',
                        'error': str(error_msg)[:200],  # Limit error message length
                        'progress': f'{idx}/{len(batch)}'
                    }
                    yield f"event: progress\ndata: {json.dumps(event_data)}\n\n"

                # Delay between messages to see logs clearly (2 seconds for testing)
                await asyncio.sleep(2)

            # Named event for "complete"
            completion_data = {
                'batch_size': len(batch),
                'messages_extracted': messages_extracted,
                'messages_skipped': messages_skipped,
                'messages_failed': messages_failed,
                'message': f'Batch complete! Extracted: {messages_extracted}, Skipped: {messages_skipped}, Failed: {messages_failed}'
            }
            yield f"event: complete\ndata: {json.dumps(completion_data)}\n\n"

            print(f"[API-WhatsAppListing] ✓ Batch complete: {messages_extracted} extracted, {messages_skipped} skipped, {messages_failed} failed")

        except Exception as e:
            print(f"[API-WhatsAppListing] ✗ Streaming error: {str(e)}")
            # Named event for "error"
            yield f"event: error\ndata: {json.dumps({'message': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )


@router.post("/extract/{message_id}")
async def extract_single_message(message_id: str):
    """
    Extract structured data from a single message by ID (for testing)

    Args:
        message_id: Message UUID from crea_wapp table

    Returns:
        Extraction result with structured data

    Example:
        POST /api/whatsapp-listings/extract/uuid-here
    """
    try:
        print(f"[API-WhatsAppListing] Extracting single message: {message_id}")

        # Fetch the message from crea_wapp
        messages = await SupabaseService.get_unprocessed_messages(limit=1000)
        message = next((m for m in messages if m.get("id") == message_id), None)

        if not message:
            raise HTTPException(status_code=404, detail=f"Message {message_id} not found or already processed")

        raw_message = message.get("raw_message", "")

        # Check for media/empty messages - skip LLM, mark as garbage
        if "<Media omitted>" in raw_message or raw_message.strip() == "":
            print(f"[WhatsAppListing] Media/empty message detected - marking as garbage")

            # Insert as garbage without LLM call
            listing_data = {
                "source_message_id": message_id,
                "message_date": message.get("message_date"),
                "agent_contact": message.get("agent_contact"),
                "agent_name": message.get("agent_name"),
                "company_name": message.get("company_name"),
                "raw_message": raw_message,
                "message_type": "garbage",
                "property_type": None,
                "llm_json": {"message_type": "garbage", "reason": "media_omitted"}
            }

            result = await SupabaseService.insert_extracted_listing(listing_data)

            if result.get("success"):
                return {
                    "success": True,
                    "message": f"Message marked as garbage (media/empty)",
                    "is_relevant": False,
                    "message_type": "garbage",
                    "data": result.get("data")
                }
            else:
                raise HTTPException(status_code=500, detail=result.get("message"))

        # Extract with LLM (pass message_id for logging)
        llm_output = await WhatsAppListingExtractionService.extract_single_message(raw_message, message_id)

        # Check if message type is relevant
        relevant_types = ['supply_sale', 'supply_rent', 'demand_buy', 'demand_rent']
        is_relevant = llm_output.message_type in relevant_types

        # Prepare data for insertion
        if is_relevant:
            # Full data for supply/demand messages
            listing_data = {
                "source_message_id": message_id,
                "message_date": message.get("message_date"),
                "agent_contact": llm_output.agent_contact or message.get("agent_contact"),
                "agent_name": llm_output.agent_name or message.get("agent_name"),
                "company_name": message.get("company_name"),
                "raw_message": raw_message,
                "message_type": llm_output.message_type,
                "property_type": llm_output.property_type,
                "area_sqft": llm_output.area_sqft,
                "price": llm_output.price,
                "price_text": llm_output.price_text,
                "location": llm_output.location,
                "project_name": llm_output.project_name,
                "furnishing_status": llm_output.furnishing_status,
                "parking_count": llm_output.parking_count,
                "parking_text": llm_output.parking_text,
                "facing_direction": llm_output.facing_direction,
                "special_features": llm_output.special_features if llm_output.special_features else [],
                "llm_json": {
                    "message_type": llm_output.message_type,
                    "agent_name": llm_output.agent_name,
                    "agent_contact": llm_output.agent_contact,
                    "property_type": llm_output.property_type,
                    "location": llm_output.location,
                    "price": llm_output.price
                }
            }
        else:
            # Minimal data for greeting/garbage/generic_info
            listing_data = {
                "source_message_id": message_id,
                "message_date": message.get("message_date"),
                "agent_contact": message.get("agent_contact"),
                "agent_name": message.get("agent_name"),
                "company_name": message.get("company_name"),
                "raw_message": raw_message,
                "message_type": llm_output.message_type,
                "property_type": None,
                "llm_json": {"message_type": llm_output.message_type}
            }

        # Insert to database
        result = await SupabaseService.insert_extracted_listing(listing_data)

        if result.get("success"):
            return {
                "success": True,
                "message": f"Successfully processed message {message_id} - type: {llm_output.message_type}",
                "is_relevant": is_relevant,
                "message_type": llm_output.message_type,
                "data": result.get("data")
            }
        else:
            raise HTTPException(status_code=500, detail=result.get("message"))

    except HTTPException:
        raise
    except Exception as e:
        print(f"[API-WhatsAppListing] ✗ Error extracting message: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error extracting message: {str(e)}")


@router.get("")
async def get_extracted_listings(
    limit: int = Query(100, description="Maximum number of listings to return"),
    offset: int = Query(0, description="Number of listings to skip for pagination")
):
    """
    Get extracted listings with pagination

    Args:
        limit: Maximum number of listings (default: 100)
        offset: Number of listings to skip (default: 0)

    Returns:
        List of extracted listings

    Example:
        GET /api/whatsapp-listings?limit=50&offset=0
    """
    try:
        print(f"[API-WhatsAppListing] Retrieving extracted listings (limit: {limit}, offset: {offset})")

        result = await SupabaseService.get_extracted_listings(limit=limit, offset=offset)

        return result

    except Exception as e:
        print(f"[API-WhatsAppListing] ✗ Error retrieving listings: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving listings: {str(e)}")


@router.get("/stats")
async def get_extraction_stats():
    """
    Get extraction statistics

    Returns statistics about the extraction process including:
    - Total messages vs extracted count
    - Progress percentage
    - Message type breakdown

    Example:
        GET /api/whatsapp-listings/stats
    """
    try:
        print("[API-WhatsAppListing] Retrieving extraction stats")

        result = await SupabaseService.get_extraction_stats()

        return result

    except Exception as e:
        print(f"[API-WhatsAppListing] ✗ Error retrieving stats: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving stats: {str(e)}")


@router.get("/search")
async def search_whatsapp_listings(
    agent_name: Optional[str] = Query(None, description="Agent or company name to search for"),
    property_query: Optional[str] = Query(None, description="Property type or project name (e.g., 'Villa', '3BHK')"),
    location: Optional[str] = Query(None, description="Location to search for"),
    message_type: Optional[str] = Query(None, description="Filter by message type: supply_sale, supply_rent, demand_buy, demand_rent"),
    limit: int = Query(100, description="Maximum number of results", ge=1, le=500),
    similarity_threshold: float = Query(0.3, description="Fuzzy matching threshold (0-1)", ge=0, le=1)
):
    """
    Search extracted WhatsApp listings with fuzzy matching

    Searches structured data from whatsapp_listings_relevant view (supply/demand only).
    Uses hybrid strategy: exact database matching + fuzzy client-side matching.
    Filters use AND logic (all specified filters must match).

    Query Parameters:
        agent_name: Search in agent_name, agent_contact, company_name fields
        property_query: Search in property_type, project_name fields
        location: Search in location field
        message_type: Filter by type (supply_sale, supply_rent, demand_buy, demand_rent)
        limit: Maximum results to return (1-500, default: 100)
        similarity_threshold: Fuzzy match threshold 0-1 (default: 0.3, lower = more lenient)

    Examples:
        GET /api/whatsapp-listings/search?location=Whitefield
        GET /api/whatsapp-listings/search?agent_name=Tajamul&property_query=Villa
        GET /api/whatsapp-listings/search?location=Indiranagar&message_type=supply_sale
        GET /api/whatsapp-listings/search?property_query=3BHK&location=Koramangala&limit=50
    """
    try:
        print(f"[API-WhatsAppListing] Searching with filters: agent={agent_name}, property={property_query}, location={location}, type={message_type}")

        result = await SupabaseService.unified_search_whatsapp(
            agent_name=agent_name,
            property_query=property_query,
            location=location,
            message_type=message_type,
            limit=limit,
            similarity_threshold=similarity_threshold
        )

        return result

    except Exception as e:
        print(f"[API-WhatsAppListing] ✗ Error searching listings: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error searching listings: {str(e)}")


# Progress endpoints removed - use /stats instead for database-driven progress
