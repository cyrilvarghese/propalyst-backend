"""
WhatsApp Stats Router

API endpoints for WhatsApp processing statistics.
- Raw message statistics
- Processing progress
"""

from fastapi import APIRouter, HTTPException
from datetime import datetime, timedelta

from services.supabase_service import SupabaseService
from config.whatsapp_config import RECENT_MESSAGES_CUTOFF_DAYS


router = APIRouter(
    prefix="/api/whatsapp-raw",
    tags=["WhatsApp Stats"]
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

        # Calculate cutoff date using configured threshold
        cutoff_date = (datetime.now() - timedelta(days=RECENT_MESSAGES_CUTOFF_DAYS)).isoformat()

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
        raise HTTPException(status_code=500, detail=str(e))
