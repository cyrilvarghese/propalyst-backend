"""
WhatsApp Parser Service

Parses WhatsApp chat export files and stores messages in the database.
Implements the parsing specification from chat_chunks/chunk_100.txt.
"""

import re
import hashlib
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from pathlib import Path
from enum import Enum

from services.supabase_service import SupabaseService


class WhatsAppFormatType(str, Enum):
    """Enum for WhatsApp export format types"""
    IOS = "ios"           # [DD/MM/YY, HH:MM:SS AM/PM] Sender: Message
    ANDROID = "android"   # DD/MM/YYYY, HH:MM - Sender: Message
    UNKNOWN = "unknown"


class WhatsAppParserService:
    """
    Service for parsing WhatsApp chat export files into structured messages
    """

    # iOS format: [DD/MM/YY, HH:MM:SS AM/PM] or [DD/MM/YYYY, HH:MM:SS] Sender: Message
    # Supports:
    # - 1-2 digit day/month (e.g., 11/3/25 or 11/03/25)
    # - 2 or 4 digit year (e.g., 25 or 2025)
    # - 12-hour with AM/PM or 24-hour format (e.g., 2:30:45 PM or 20:30:45)
    IOS_BOUNDARY_PATTERN = re.compile(
        r'^\[(\d{1,2}/\d{1,2}/\d{2,4}),\s*(\d{1,2}:\d{2}:\d{2}(?:\s*[AP]M)?)\]\s*([^:]+):\s*(.*)',
        re.MULTILINE
    )

    # Android format: DD/MM/YYYY, HH:MM - Sender: Message
    # Supports:
    # - 1-2 digit day/month (e.g., 3/4 or 03/04)
    # - 2 or 4 digit year (e.g., 25 or 2025)
    # - 24-hour format (20:30) or 12-hour with AM/PM (3:24 PM)
    ANDROID_BOUNDARY_PATTERN = re.compile(
        r'^(\d{1,2}/\d{1,2}/\d{2,4}),\s*(\d{1,2}:\d{2}(?:\s*[AP]M)?)\s*-\s*([^:]+):\s*(.*)',
        re.MULTILINE
    )

    # Legacy alias for backward compatibility
    BOUNDARY_PATTERN = IOS_BOUNDARY_PATTERN

    # Pattern for detecting system messages without sender (iOS format)
    # Supports 1-2 digit day/month, 2-4 digit year, and both 12-hour and 24-hour formats
    SYSTEM_MESSAGE_PATTERN = re.compile(
        r'^\[(\d{1,2}/\d{1,2}/\d{2,4}),\s*(\d{1,2}:\d{2}:\d{2}(?:\s*[AP]M)?)\]\s*(.+)$',
        re.MULTILINE
    )

    @classmethod
    def detect_format(cls, content: str) -> WhatsAppFormatType:
        """
        Detect WhatsApp export format by analyzing first 50 lines

        Args:
            content: String content of WhatsApp export file

        Returns:
            WhatsAppFormatType enum (ios, android, or unknown)
        """
        lines = content.split('\n')
        ios_count = 0
        android_count = 0

        # Sample first 50 lines to detect format
        for line in lines[:50]:
            line_cleaned = line.lstrip('\u200e\u200f\ufeff')

            if cls.IOS_BOUNDARY_PATTERN.match(line_cleaned):
                ios_count += 1
            elif cls.ANDROID_BOUNDARY_PATTERN.match(line_cleaned):
                android_count += 1

        # Return format with most matches
        if ios_count > android_count and ios_count > 0:
            return WhatsAppFormatType.IOS
        elif android_count > ios_count and android_count > 0:
            return WhatsAppFormatType.ANDROID
        else:
            return WhatsAppFormatType.UNKNOWN

    @classmethod
    def parse_file_content(
        cls,
        content: str,
        source_file: Optional[str] = None,
        format: Optional[WhatsAppFormatType] = None
    ) -> List[Dict[str, Any]]:
        """
        Parse WhatsApp export content string into structured messages

        Args:
            content: String content of WhatsApp export file
            source_file: Optional name of source file for tracking
            format: Optional format override (ios or android). Auto-detected if None.

        Returns:
            List of message dictionaries ready for database insertion

        Raises:
            ValueError: If format is unknown or unsupported
        """
        # Auto-detect format if not specified
        if format is None:
            format = cls.detect_format(content)

        if format == WhatsAppFormatType.UNKNOWN:
            raise ValueError("Unable to detect WhatsApp export format. Supported formats:\n"
                           "  iOS: [DD/MM/YY, HH:MM:SS AM/PM] or [DD/MM/YYYY, HH:MM:SS]\n"
                           "  Android: DD/MM/YY, HH:MM AM/PM or DD/MM/YYYY, HH:MM")

        # Select pattern based on format
        boundary_pattern = cls.IOS_BOUNDARY_PATTERN if format == WhatsAppFormatType.IOS else cls.ANDROID_BOUNDARY_PATTERN
        is_ios_format = format == WhatsAppFormatType.IOS

        messages = []
        lines = content.split('\n')

        current_message = None
        current_line_number = None

        for line_num, line in enumerate(lines, start=1):
            # Strip invisible Unicode characters (like Left-to-Right marks) from the start
            # These are common in WhatsApp exports and prevent regex matching
            line_cleaned = line.lstrip('\u200e\u200f\ufeff')  # LTR mark, RTL mark, BOM

            # Try to match message boundary on cleaned line
            match = boundary_pattern.match(line_cleaned)

            if match:
                # Save previous message if exists
                if current_message:
                    # Trim trailing whitespace from message text
                    current_message['message_text'] = current_message['message_text'].strip()
                    messages.append(current_message)

                # Parse new message
                date_str, time_str, sender, text = match.groups()

                try:
                    # Determine datetime format based on format type
                    if is_ios_format:
                        # iOS: detect year format (2-digit vs 4-digit) and time format (12-hour vs 24-hour)
                        year_part = date_str.split('/')[-1]
                        has_am_pm = 'AM' in time_str.upper() or 'PM' in time_str.upper()

                        if len(year_part) == 2:
                            # 2-digit year
                            datetime_format = "%d/%m/%y %I:%M:%S %p" if has_am_pm else "%d/%m/%y %H:%M:%S"
                        else:
                            # 4-digit year
                            datetime_format = "%d/%m/%Y %I:%M:%S %p" if has_am_pm else "%d/%m/%Y %H:%M:%S"
                    else:
                        # Android: detect year format (2-digit vs 4-digit) and time format (12-hour vs 24-hour)
                        year_part = date_str.split('/')[-1]
                        has_am_pm = 'AM' in time_str.upper() or 'PM' in time_str.upper()

                        if len(year_part) == 2:
                            # 2-digit year
                            datetime_format = "%d/%m/%y %I:%M %p" if has_am_pm else "%d/%m/%y %H:%M"
                        else:
                            # 4-digit year
                            datetime_format = "%d/%m/%Y %I:%M %p" if has_am_pm else "%d/%m/%Y %H:%M"

                    # Parse datetime using detected/specified format
                    datetime_str = f"{date_str} {time_str.strip()}"
                    message_date = datetime.strptime(datetime_str, datetime_format)

                    # Detect special message types
                    is_deleted = "This message was deleted" in text or "‎This message was deleted" in text
                    is_media = any(keyword in text.lower() for keyword in [
                        "image omitted",
                        "video omitted",
                        "audio omitted",
                        "document omitted",
                        "media omitted",
                        "‎image omitted",
                        "‎video omitted"
                    ])

                    # Create message object
                    current_message = {
                        "message_date": message_date,
                        "sender_name": sender.strip(),
                        "message_text": text,
                        "is_deleted": is_deleted,
                        "is_media": is_media,
                        "source_file": source_file,
                        "line_number": line_num
                    }
                    current_line_number = line_num

                except ValueError as e:
                    # Failed to parse datetime, skip this line
                    print(f"[WhatsAppParser] Failed to parse datetime at line {line_num}: {e}")
                    current_message = None
                    continue

            elif current_message and line_cleaned.strip():
                # Multi-line message continuation
                # Add newline and the cleaned line to current message
                current_message['message_text'] += '\n' + line_cleaned

            elif current_message and not line_cleaned.strip():
                # Empty line within a message - preserve it
                current_message['message_text'] += '\n'

        # Add the last message if exists
        if current_message:
            current_message['message_text'] = current_message['message_text'].strip()
            messages.append(current_message)

        return messages

    @classmethod
    def parse_file(cls, file_path: str) -> List[Dict[str, Any]]:
        """
        Parse WhatsApp export file into structured messages

        Args:
            file_path: Path to the WhatsApp export text file

        Returns:
            List of message dictionaries ready for database insertion

        Raises:
            FileNotFoundError: If file doesn't exist
            IOError: If file cannot be read
        """
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Read file content
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Parse content with source file name
        return cls.parse_file_content(content, source_file=path.name)

    @staticmethod
    def calculate_message_hash(message: Dict[str, Any]) -> str:
        """
        Calculate MD5 hash of message for deduplication

        Uses message_text ONLY to detect duplicates across different senders/dates.
        This ensures that the same property listing forwarded by multiple agents
        is recognized as a duplicate.

        Args:
            message: Message dictionary (requires 'message_text' key)

        Returns:
            MD5 hash string
        """
        # Hash based on message text only (ignores sender and date)
        message_text = message.get('message_text', '')
        return hashlib.md5(message_text.encode('utf-8')).hexdigest()

    @classmethod
    async def insert_raw_messages(
        cls,
        messages: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Insert raw parsed messages into whatsapp_raw_messages table with deduplication

        Args:
            messages: List of parsed message dictionaries

        Returns:
            Dict with counts of inserted and skipped messages
        """
        if not messages:
            return {
                "success": True,
                "messages_inserted": 0,
                "messages_skipped": 0,
                "message": "No messages to insert"
            }

        try:
            # Add hash to each message
            messages_with_hash = []
            hashes = []
            for msg in messages:
                msg_copy = msg.copy()

                # Calculate hash for deduplication
                msg_copy['message_hash'] = cls.calculate_message_hash(msg)
                hashes.append(msg_copy['message_hash'])

                # Convert datetime to ISO format
                if isinstance(msg_copy.get('message_date'), datetime):
                    msg_copy['message_date'] = msg_copy['message_date'].isoformat()

                messages_with_hash.append(msg_copy)

            # Check for existing duplicates BEFORE inserting
            client = SupabaseService._get_client()
            existing_response = client.table("whatsapp_raw_messages")\
                .select("id, sender_name, message_text, message_date, message_hash")\
                .in_("message_hash", hashes)\
                .execute()

            # Build lookup of existing messages by hash
            existing_by_hash = {}
            if existing_response.data:
                for existing in existing_response.data:
                    existing_by_hash[existing['message_hash']] = existing

            # Find duplicate pairs
            duplicate_pairs = []
            messages_to_insert = []

            for msg in messages_with_hash:
                msg_hash = msg['message_hash']
                if msg_hash in existing_by_hash:
                    # This is a duplicate
                    existing = existing_by_hash[msg_hash]
                    duplicate_pairs.append({
                        "existing": {
                            "id": existing['id'],
                            "sender": existing['sender_name'],
                            "preview": existing['message_text'][:150] if existing['message_text'] else "",
                            "date": existing['message_date']
                        },
                        "incoming": {
                            "sender": msg.get('sender_name'),
                            "preview": msg.get('message_text', '')[:150],
                            "date": msg.get('message_date')
                        }
                    })
                else:
                    # New message
                    messages_to_insert.append(msg)

            # Insert only new messages
            inserted_count = 0
            if messages_to_insert:
                response = client.table("whatsapp_raw_messages").insert(
                    messages_to_insert
                ).execute()
                inserted_count = len(response.data) if response.data else 0

            skipped_count = len(duplicate_pairs)

            print(f"[WhatsAppParser] Inserted {inserted_count} new messages, found {skipped_count} duplicates")

            return {
                "success": True,
                "messages_inserted": inserted_count,
                "messages_skipped": skipped_count,
                "duplicate_pairs": duplicate_pairs[:10],  # First 10 duplicate pairs
                "total_duplicates": skipped_count,
                "message": f"Inserted {inserted_count} messages, found {skipped_count} duplicates"
            }

        except Exception as e:
            print(f"[WhatsAppParser] Error inserting raw messages: {e}")
            return {
                "success": False,
                "messages_inserted": 0,
                "messages_skipped": 0,
                "duplicate_pairs": [],
                "total_duplicates": 0,
                "message": f"Failed to insert messages: {str(e)}"
            }

    @classmethod
    async def get_unprocessed_raw_messages(
        cls,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get raw messages that haven't been processed by LLM yet (from last 4 months)

        Args:
            limit: Maximum number of messages to return

        Returns:
            List of unprocessed message dictionaries
        """
        try:
            # Calculate cutoff date (4 months ago)
            cutoff_date = (datetime.now() - timedelta(days=120)).isoformat()

            client = SupabaseService._get_client()
            response = client.table("whatsapp_raw_messages")\
                .select("*")\
                .eq("processed", False)\
                .eq("is_deleted", False)\
                .eq("is_media", False)\
                .gte("message_date", cutoff_date)\
                .order("message_date", desc=False)\
                .limit(limit)\
                .execute()

            return response.data or []

        except Exception as e:
            print(f"[WhatsAppParser] Error getting unprocessed messages: {e}")
            raise

    @classmethod
    async def mark_as_processed(
        cls,
        raw_message_id: str
    ) -> Dict[str, Any]:
        """
        Mark a raw message as processed

        Args:
            raw_message_id: UUID of the raw message

        Returns:
            Success status
        """
        try:
            client = SupabaseService._get_client()
            client.table("whatsapp_raw_messages")\
                .update({
                    "processed": True,
                    "processed_at": datetime.now().isoformat()
                })\
                .eq("id", raw_message_id)\
                .execute()

            return {
                "success": True,
                "message": "Marked as processed"
            }

        except Exception as e:
            print(f"[WhatsAppParser] Error marking message as processed: {e}")
            return {
                "success": False,
                "message": str(e)
            }

