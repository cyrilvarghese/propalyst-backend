"""
WhatsApp Raw Messages Router

API endpoints for parsing WhatsApp chat exports and managing raw messages.
"""

from fastapi import APIRouter, UploadFile, File
from fastapi.responses import StreamingResponse
from datetime import datetime, timedelta
import json
import asyncio

from services.whatsapp_parser_service import WhatsAppParserService
from services.whatsapp_combined_processor_service import WhatsAppCombinedProcessorService
from services.supabase_service import SupabaseService


router = APIRouter(
    prefix="/api/whatsapp-raw",
    tags=["WhatsApp Raw Messages"]
)


@router.post("/upload-file")
async def upload_file(
    file: UploadFile = File(..., description="WhatsApp chat export text file")
):
    """
    STAGE 1: Upload WhatsApp file and parse into raw messages (NO LLM processing)

    **What it does**:
    1. Parse WhatsApp export file with regex
    2. Calculate hash for each message (MD5 of text + sender + date)
    3. Insert into `whatsapp_raw_messages` table
    4. Duplicates are automatically skipped (UNIQUE constraint on hash)
    5. **STOPS HERE** - No LLM processing

    **Next Step**: Use `POST /process-unprocessed-stream` to process with LLM

    **Benefits**:
    - Fast upload (no LLM calls)
    - Deduplication (upload same file = no duplicates)
    - User controls when to start Stage 2

    **Response**: JSON (not streaming)
    ```json
    {
      "success": true,
      "messages_parsed": 500,
      "messages_inserted": 300,
      "messages_skipped": 200,
      "ready_for_llm": 670,
      "message": "Uploaded successfully. 300 new messages ready for processing."
    }
    ```
    """
    try:
        # Validate file type
        if not file.filename.endswith('.txt'):
            from fastapi import HTTPException
            raise HTTPException(status_code=400, detail="Only .txt files are supported")

        # Read file content
        content = await file.read()
        content_str = content.decode('utf-8')

        # Parse with regex
        messages = WhatsAppParserService.parse_file_content(
            content_str,
            source_file=file.filename
        )

        print(f"[WhatsAppRaw] Parsed {len(messages)} messages from file")

        # Insert into raw messages table (with deduplication)
        insert_result = await WhatsAppParserService.insert_raw_messages(messages)

        print(f"[WhatsAppRaw] Inserted {insert_result['messages_inserted']} new, skipped {insert_result['messages_skipped']} duplicates")

        # Get count of unprocessed messages ready for LLM (last 4 months only)
        unprocessed_messages = await WhatsAppParserService.get_unprocessed_raw_messages(limit=10000)
        ready_for_llm_count = len(unprocessed_messages)

        return {
            "success": True,
            "messages_parsed": len(messages),
            "messages_inserted": insert_result['messages_inserted'],
            "messages_skipped": insert_result['messages_skipped'],
            "ready_for_llm": ready_for_llm_count,
            "message": f"Upload complete! {insert_result['messages_inserted']} new messages inserted, {insert_result['messages_skipped']} duplicates skipped. {ready_for_llm_count} messages ready for LLM processing (last 4 months)."
        }

    except Exception as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/process-unprocessed-stream")
async def process_unprocessed_stream(
    limit: int = 1000
):
    """
    Process unprocessed raw messages (Stage 2 only - no file upload)

    **Use Cases**:
    - Resume processing after interruption
    - Process messages uploaded earlier
    - Reprocess with updated prompts

    **What it does**:
    1. Read unprocessed messages from `whatsapp_raw_messages`
    2. For each: LLM split + extract
    3. Insert into `whatsapp_listing_data`
    4. Mark as processed

    **Streaming Response**: Server-Sent Events (SSE)
    ```
    event: start
    data: {"batch_size": 670}

    event: progress
    data: {"status": "completed", "progress": "1/670", "message_type": "supply_sale"}

    event: complete
    data: {"messages_extracted": 650, "messages_failed": 20}
    ```
    """
    async def event_generator():
        try:
            # Get unprocessed messages (Stage 2 only)
            unprocessed_messages = await WhatsAppParserService.get_unprocessed_raw_messages(limit=limit)

            print(f"[WhatsAppRaw] Found {len(unprocessed_messages)} unprocessed messages")

            # Emit start event
            yield f"event: start\ndata: {json.dumps({'batch_size': len(unprocessed_messages)})}\n\n"

            if len(unprocessed_messages) == 0:
                yield f"event: complete\ndata: {json.dumps({'batch_size': 0, 'messages_extracted': 0, 'message': 'No unprocessed messages found'})}\n\n"
                return

            # Counters
            messages_extracted = 0
            messages_failed = 0

            # Process each unprocessed message with LLM
            for idx, raw_message in enumerate(unprocessed_messages, 1):
                raw_message_id = raw_message.get('id')

                try:
                    # Convert raw message to format expected by processor
                    message_for_processing = {
                        'message_date': raw_message.get('message_date'),
                        'sender_name': raw_message.get('sender_name'),
                        'message_text': raw_message.get('message_text'),
                        'source_file': raw_message.get('source_file'),
                        'line_number': raw_message.get('line_number')
                    }

                    # Process with combined LLM (split + extract)
                    split_result = await WhatsAppCombinedProcessorService.process_message(message_for_processing)

                    # Insert each split message into whatsapp_listing_data
                    for split_idx, processed_msg in enumerate(split_result, 1):
                        # Convert datetime to ISO string for Supabase
                        message_date = processed_msg.get('message_date')
                        if isinstance(message_date, datetime):
                            message_date = message_date.isoformat()

                        # Prepare data for database insertion
                        listing_data = {
                            "source_raw_message_id": raw_message_id,
                            "message_date": message_date,
                            "agent_contact": processed_msg.get('extracted_agent_contact'),
                            "agent_name": processed_msg.get('extracted_agent_name'),
                            "raw_message": processed_msg.get('message_text'),
                            "message_type": processed_msg.get('message_type'),
                            "property_type": processed_msg.get('property_type'),
                            "area_sqft": processed_msg.get('area_sqft'),
                            "bedroom_count": processed_msg.get('bedroom_count'),
                            "price": processed_msg.get('price'),
                            "price_text": processed_msg.get('price_text'),
                            "location": processed_msg.get('location'),
                            "project_name": processed_msg.get('project_name'),
                            "furnishing_status": processed_msg.get('furnishing_status'),
                            "parking_count": processed_msg.get('parking_count'),
                            "parking_text": processed_msg.get('parking_text'),
                            "facing_direction": processed_msg.get('facing_direction'),
                            "special_features": processed_msg.get('special_features', []),
                            "llm_json": {
                                "message_type": processed_msg.get('message_type'),
                                "split_from_original": processed_msg.get('split_from_original', False),
                                "split_index": processed_msg.get('split_index')
                            }
                        }

                        # Insert to whatsapp_listing_data
                        result = await SupabaseService.insert_extracted_listing(listing_data)

                        if result.get("success"):
                            messages_extracted += 1

                            # Emit progress event
                            event_data = {
                                'status': 'completed',
                                'progress': f'{idx}/{len(unprocessed_messages)}',
                                'message_type': processed_msg.get('message_type'),
                                'location': processed_msg.get('location'),
                                'split_index': f'{split_idx}/{len(split_result)}' if len(split_result) > 1 else None
                            }
                            yield f"event: progress\ndata: {json.dumps(event_data)}\n\n"

                            print(f"[WhatsAppRaw] ✓ Inserted listing {idx} (split {split_idx}/{len(split_result)}) - type: {processed_msg.get('message_type')}")
                        else:
                            messages_failed += 1
                            error_msg = result.get('message', 'Unknown error')

                            event_data = {
                                'status': 'failed',
                                'progress': f'{idx}/{len(unprocessed_messages)}',
                                'error': str(error_msg)[:200]
                            }
                            yield f"event: progress\ndata: {json.dumps(event_data)}\n\n"

                    # Mark raw message as processed
                    await WhatsAppParserService.mark_as_processed(raw_message_id)

                except Exception as e:
                    messages_failed += 1
                    print(f"[WhatsAppRaw] ✗ Error processing message {idx}: {e}")

                    event_data = {
                        'status': 'failed',
                        'progress': f'{idx}/{len(unprocessed_messages)}',
                        'error': str(e)[:200]
                    }
                    yield f"event: progress\ndata: {json.dumps(event_data)}\n\n"

                # Small delay
                await asyncio.sleep(0.5)

            # Emit complete event
            completion_data = {
                'batch_size': len(unprocessed_messages),
                'messages_extracted': messages_extracted,
                'messages_failed': messages_failed,
                'message': f'Processing complete! Extracted: {messages_extracted}, Failed: {messages_failed}'
            }
            yield f"event: complete\ndata: {json.dumps(completion_data)}\n\n"

            print(f"[WhatsAppRaw] ✓ Processing complete: {messages_extracted} extracted, {messages_failed} failed")

        except Exception as e:
            print(f"[WhatsAppRaw] ✗ Streaming error: {str(e)}")
            yield f"event: error\ndata: {json.dumps({'message': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.get("/raw-stats")
async def get_raw_message_stats():
    """
    Get statistics about raw messages (Stage 1)

    Returns counts of:
    - Total raw messages (all time)
    - Messages from last 4 months
    - Messages older than 4 months
    - Processed vs unprocessed (last 4 months)
    - Deleted/media messages
    - Ready for LLM (last 4 months only)
    - Unique senders
    - Date range
    """
    try:
        client = SupabaseService._get_client()

        # Calculate cutoff date (4 months ago)
        cutoff_date = (datetime.now() - timedelta(days=120)).isoformat()

        # Get total count of ALL messages (using count API for efficiency)
        total_response = client.table("whatsapp_raw_messages")\
            .select("*", count="exact", head=True)\
            .execute()
        total_messages_all_time = total_response.count if hasattr(total_response, 'count') and total_response.count else 0

        # Get messages from last 4 months (paginate to fetch all records)
        recent_messages = []
        batch_size = 1000
        offset = 0

        while True:
            response = client.table("whatsapp_raw_messages")\
                .select("*")\
                .gte("message_date", cutoff_date)\
                .range(offset, offset + batch_size - 1)\
                .execute()

            batch = response.data or []
            if not batch:
                break

            recent_messages.extend(batch)
            offset += batch_size

            if len(batch) < batch_size:
                break  # Last batch

        # Calculate counts
        recent_count = len(recent_messages)
        old_messages_count = total_messages_all_time - recent_count

        if recent_count == 0:
            return {
                "total_messages_all_time": total_messages_all_time,
                "recent_messages_4_months": 0,
                "old_messages_over_4_months": old_messages_count,
                "processed": 0,
                "unprocessed": 0,
                "deleted": 0,
                "media": 0,
                "ready_for_llm": 0,
                "unique_senders": 0,
                "date_range": None
            }

        # Calculate statistics (only for recent messages)
        processed_count = sum(1 for msg in recent_messages if msg.get("processed"))
        unprocessed_count = sum(1 for msg in recent_messages if not msg.get("processed"))
        deleted_count = sum(1 for msg in recent_messages if msg.get("is_deleted"))
        media_count = sum(1 for msg in recent_messages if msg.get("is_media"))

        # Ready for LLM = unprocessed AND not deleted AND not media (last 4 months only)
        ready_for_llm = sum(
            1 for msg in recent_messages
            if not msg.get("processed")
            and not msg.get("is_deleted")
            and not msg.get("is_media")
        )

        unique_senders = len(set(msg.get("sender_name") for msg in recent_messages if msg.get("sender_name")))

        # Date range (only recent messages)
        dates = [msg.get("message_date") for msg in recent_messages if msg.get("message_date")]
        date_range = None
        if dates:
            date_range = {
                "earliest": min(dates),
                "latest": max(dates)
            }

        return {
            "total_messages_all_time": total_messages_all_time,
            "recent_messages_4_months": recent_count,
            "old_messages_over_4_months": old_messages_count,
            "processed": processed_count,
            "unprocessed": unprocessed_count,
            "deleted": deleted_count,
            "media": media_count,
            "ready_for_llm": ready_for_llm,
            "unique_senders": unique_senders,
            "date_range": date_range
        }

    except Exception as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=str(e))
