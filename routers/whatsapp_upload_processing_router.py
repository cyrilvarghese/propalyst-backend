"""
WhatsApp Upload & Processing Router

API endpoints for uploading WhatsApp chat exports and processing raw messages.
- Stage 1: Upload files and parse into raw messages
- Stage 2: Process messages with LLM
"""

from fastapi import APIRouter, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from datetime import datetime, timedelta
import json
import asyncio

from services.whatsapp_parser_service import WhatsAppParserService, WhatsAppFormatType
from services.whatsapp_combined_processor_service import WhatsAppCombinedProcessorService
from services.supabase_service import SupabaseService


router = APIRouter(
    prefix="/api/whatsapp-raw",
    tags=["WhatsApp Upload & Processing"]
)


@router.post("/upload-file")
async def upload_file(
    file: UploadFile = File(..., description="WhatsApp chat export text file"),
    date_format_preference: str = Form("DD/MM/YY", description="Date format: DD/MM/YY (default, most common) or MM/DD/YY (US format)")
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

    **Parameters**:
    - `file`: WhatsApp chat export .txt file
    - `date_format_preference`: Date format in export (default: DD/MM/YY for most countries, use MM/DD/YY for US exports)

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

        # Detect format
        detected_format = WhatsAppParserService.detect_format(content_str)
        print(f"[WhatsAppRaw] Format detected: {detected_format.value.upper()} (from file: {file.filename})")

        # Parse with regex
        messages = WhatsAppParserService.parse_file_content(
            content_str,
            source_file=file.filename,
            format=detected_format,
            date_format_preference=date_format_preference
        )

        print(f"[WhatsAppRaw] Parsed {len(messages)} messages from file (format: {detected_format.value})")

        # Insert into raw messages table (with deduplication)
        insert_result = await WhatsAppParserService.insert_raw_messages(messages)

        print(f"[WhatsAppRaw] Inserted {insert_result['messages_inserted']} new, found {insert_result['messages_skipped']} duplicates")

        # Get count of unprocessed messages ready for LLM (last 4 months only)
        unprocessed_messages = await WhatsAppParserService.get_unprocessed_raw_messages(limit=10000)
        ready_for_llm_count = len(unprocessed_messages)

        return {
            "success": True,
            "messages_parsed": len(messages),
            "messages_inserted": insert_result['messages_inserted'],
            "messages_skipped": insert_result['messages_skipped'],
            "duplicates": insert_result.get('duplicates', []),
            "ready_for_llm": ready_for_llm_count,
            "message": f"Upload complete! {insert_result['messages_inserted']} new messages inserted, {insert_result['messages_skipped']} duplicates found. {ready_for_llm_count} messages ready for LLM processing (last 4 months)."
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
