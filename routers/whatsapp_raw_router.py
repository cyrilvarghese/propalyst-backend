"""
WhatsApp Raw Messages Router

API endpoints for parsing WhatsApp chat exports and managing raw messages.
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Query
from typing import Optional
from datetime import datetime
import tempfile
import os
import json
from pathlib import Path

from services.whatsapp_parser_service import WhatsAppParserService
from services.whatsapp_message_splitter_service import WhatsAppMessageSplitterService
from services.whatsapp_combined_processor_service import WhatsAppCombinedProcessorService
from models.whatsapp_raw_message import (
    WhatsAppParseResponse,
    WhatsAppRawMessage,
    WhatsAppMessageFilters
)


router = APIRouter(
    prefix="/api/whatsapp-raw",
    tags=["WhatsApp Raw Messages"]
)


@router.post("/test-parse")
async def test_parse_file(
    file: UploadFile = File(..., description="WhatsApp chat export text file")
):
    """
    **TESTING ENDPOINT**: Parse WhatsApp file and write output to text file

    This endpoint is for testing the parser WITHOUT database insertion.

    It will:
    1. Accept an uploaded WhatsApp export file
    2. Parse it into structured messages
    3. Filter out deleted messages and media-only messages
    4. **Use LLM to detect and split messages with multiple listings**
    5. Write the parsed output to `data/parsed_output.json`
    6. Return the parsed messages

    **No database operations** - just file parsing and output to JSON.

    **Filtering**: Automatically excludes:
    - Messages marked as deleted ("This message was deleted")
    - Media-only messages ("image omitted", "video omitted", etc.)

    **LLM Processing**: Uses GPT-4o-mini to:
    - Detect messages containing multiple distinct property listings
    - Split them into separate messages (preserving sender/date)
    - Extract structured data from each listing (property type, price, location, etc.)
    - All in ONE LLM call (efficient!)
    """
    temp_path = None

    try:
        # Validate file type
        if not file.filename.endswith('.txt'):
            raise HTTPException(
                status_code=400,
                detail="Only .txt files are supported"
            )

        # Read file content directly
        content = await file.read()
        content_str = content.decode('utf-8')

        # Parse the content
        messages = WhatsAppParserService.parse_file_content(
            content_str,
            source_file=file.filename
        )

        # Filter out deleted and media messages
        messages_filtered = [
            msg for msg in messages
            if not msg.get('is_deleted', False) and not msg.get('is_media', False)
        ]

        # Prepare output file (create directory and start with empty array)
        output_dir = Path(__file__).parent.parent / "data"
        output_dir.mkdir(exist_ok=True)
        output_file = output_dir / "parsed_output.json"

        # Initialize output file with empty array
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('[\n')

        # Process and write messages incrementally
        messages_split_count = 0
        first_message = True

        for idx, message in enumerate(messages_filtered, 1):
            # Process message (split + extract using combined LLM call)
            split_result = await WhatsAppCombinedProcessorService.process_message(message)

            # Write each split message to file immediately
            for msg in split_result:
                # Convert datetime to ISO format
                msg_copy = msg.copy()
                if isinstance(msg_copy.get('message_date'), datetime):
                    msg_copy['message_date'] = msg_copy['message_date'].isoformat()

                # Write to file with proper JSON formatting
                with open(output_file, 'a', encoding='utf-8') as f:
                    if not first_message:
                        f.write(',\n')
                    json.dump(msg_copy, f, indent=2, ensure_ascii=False)
                    first_message = False

                messages_split_count += 1

            # Optional: print progress every 10 messages
            if idx % 10 == 0:
                print(f"[TestParse] Processed {idx}/{len(messages_filtered)} messages...")

        # Close JSON array
        with open(output_file, 'a', encoding='utf-8') as f:
            f.write('\n]')

        # Calculate statistics
        messages_expanded = messages_split_count - len(messages_filtered)  # How many extra from splitting

        # Read back a sample for the response
        with open(output_file, 'r', encoding='utf-8') as f:
            all_messages = json.load(f)
            sample_messages = all_messages[:5] if len(all_messages) > 0 else []

        return {
            "success": True,
            "messages_parsed": len(messages),
            "messages_filtered": len(messages_filtered),
            "messages_excluded": len(messages) - len(messages_filtered),
            "messages_after_split": messages_split_count,
            "messages_expanded": messages_expanded,
            "output_file": str(output_file),
            "message": f"Successfully parsed {len(messages)} messages, kept {len(messages_filtered)} after filtering, expanded to {messages_split_count} after LLM processing (+{messages_expanded}). Extracted structured data from all listings. Output written incrementally to {output_file}",
            "sample_messages": sample_messages
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing file: {str(e)}"
        )


@router.post("/upload", response_model=WhatsAppParseResponse)
async def upload_chat_export(
    file: UploadFile = File(..., description="WhatsApp chat export text file")
):
    """
    Upload and parse a WhatsApp chat export file

    Accepts a .txt file exported from WhatsApp and:
    1. Parses it into individual messages
    2. Stores each message in the database

    **File Format**: Standard WhatsApp export with timestamps like `[DD/MM/YY, HH:MM:SS AM/PM] Sender: Message`

    **Returns**: Count of messages parsed and inserted
    """
    temp_path = None

    try:
        # Validate file type
        if not file.filename.endswith('.txt'):
            raise HTTPException(
                status_code=400,
                detail="Only .txt files are supported"
            )

        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix='.txt', mode='wb') as tmp:
            content = await file.read()
            tmp.write(content)
            temp_path = tmp.name

        # Parse and insert
        result = await WhatsAppParserService.parse_and_insert_file(temp_path)

        return WhatsAppParseResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing file: {str(e)}"
        )
    finally:
        # Cleanup temporary file
        if temp_path and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except Exception as e:
                print(f"[WhatsAppRawRouter] Failed to delete temp file: {e}")


@router.post("/parse-local", response_model=WhatsAppParseResponse)
async def parse_local_file(
    file_path: str = Query(
        ...,
        description="Absolute path to the WhatsApp export file on the server",
        example="/home/propalyst/propalyst-backend/chat_chunks/chunk_100.txt"
    )
):
    """
    Parse a WhatsApp export file from local filesystem

    Useful for processing files already on the server (e.g., in chat_chunks/ directory).

    **File Path**: Must be absolute path to the file

    **Returns**: Count of messages parsed and inserted
    """
    try:
        result = await WhatsAppParserService.parse_and_insert_file(file_path)
        return WhatsAppParseResponse(**result)

    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"File not found: {file_path}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing file: {str(e)}"
        )


@router.get("/messages", response_model=list[WhatsAppRawMessage])
async def get_messages(
    sender_name: Optional[str] = Query(
        None,
        description="Filter by sender name (exact match)"
    ),
    source_file: Optional[str] = Query(
        None,
        description="Filter by source file name"
    ),
    date_from: Optional[datetime] = Query(
        None,
        description="Filter messages from this date onwards (ISO 8601 format)"
    ),
    date_to: Optional[datetime] = Query(
        None,
        description="Filter messages up to this date (ISO 8601 format)"
    ),
    is_deleted: Optional[bool] = Query(
        None,
        description="Filter by deleted status"
    ),
    is_media: Optional[bool] = Query(
        None,
        description="Filter by media status"
    ),
    limit: int = Query(
        100,
        ge=1,
        le=1000,
        description="Maximum number of messages to return"
    ),
    offset: int = Query(
        0,
        ge=0,
        description="Number of messages to skip (for pagination)"
    )
):
    """
    Retrieve WhatsApp raw messages with optional filters

    Returns messages ordered by message date (most recent first).
    Supports pagination using `limit` and `offset` parameters.

    **Example queries**:
    - Get latest 100 messages: `GET /messages`
    - Get messages from specific sender: `GET /messages?sender_name=John`
    - Get messages from specific file: `GET /messages?source_file=chunk_100.txt`
    - Get non-deleted messages: `GET /messages?is_deleted=false`
    - Get messages in date range: `GET /messages?date_from=2025-01-01T00:00:00Z&date_to=2025-01-31T23:59:59Z`
    """
    try:
        messages = await WhatsAppParserService.get_messages(
            sender_name=sender_name,
            source_file=source_file,
            date_from=date_from,
            date_to=date_to,
            is_deleted=is_deleted,
            is_media=is_media,
            limit=limit,
            offset=offset
        )

        return messages

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving messages: {str(e)}"
        )


@router.get("/stats")
async def get_statistics():
    """
    Get statistics about stored WhatsApp messages

    Returns:
    - Total message count
    - Unique sender count
    - Date range
    - Counts by type (deleted, media)
    """
    try:
        client = WhatsAppParserService._get_client()

        # Get all messages (we'll calculate stats client-side for simplicity)
        # In production, you'd want to use aggregation queries
        all_messages = await WhatsAppParserService.get_messages(limit=10000)

        if not all_messages:
            return {
                "total_messages": 0,
                "unique_senders": 0,
                "deleted_messages": 0,
                "media_messages": 0,
                "date_range": None
            }

        # Calculate statistics
        senders = set(msg["sender_name"] for msg in all_messages)
        deleted_count = sum(1 for msg in all_messages if msg.get("is_deleted", False))
        media_count = sum(1 for msg in all_messages if msg.get("is_media", False))

        # Get date range
        dates = [datetime.fromisoformat(msg["message_date"].replace('Z', '+00:00'))
                 for msg in all_messages if msg.get("message_date")]
        date_range = None
        if dates:
            date_range = {
                "earliest": min(dates).isoformat(),
                "latest": max(dates).isoformat()
            }

        return {
            "total_messages": len(all_messages),
            "unique_senders": len(senders),
            "deleted_messages": deleted_count,
            "media_messages": media_count,
            "date_range": date_range
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error calculating statistics: {str(e)}"
        )
