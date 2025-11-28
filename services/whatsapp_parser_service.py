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

from services.supabase_service import SupabaseService


class WhatsAppParserService:
    """
    Service for parsing WhatsApp chat export files into structured messages
    """

    # Regex pattern for WhatsApp message boundary
    # Matches: [DD/MM/YY, HH:MM:SS AM/PM] Sender: Message
    BOUNDARY_PATTERN = re.compile(
        r'^\[(\d{2}/\d{2}/\d{2}),\s*(\d{1,2}:\d{2}:\d{2}\s*[AP]M)\]\s*([^:]+):\s*(.*)',
        re.MULTILINE
    )

    # Pattern for detecting system messages without sender
    SYSTEM_MESSAGE_PATTERN = re.compile(
        r'^\[(\d{2}/\d{2}/\d{2}),\s*(\d{1,2}:\d{2}:\d{2}\s*[AP]M)\]\s*(.+)$',
        re.MULTILINE
    )

    @classmethod
    def parse_file_content(
        cls,
        content: str,
        source_file: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Parse WhatsApp export content string into structured messages

        Args:
            content: String content of WhatsApp export file
            source_file: Optional name of source file for tracking

        Returns:
            List of message dictionaries ready for database insertion
        """
        messages = []
        lines = content.split('\n')

        current_message = None
        current_line_number = None

        for line_num, line in enumerate(lines, start=1):
            # Strip invisible Unicode characters (like Left-to-Right marks) from the start
            # These are common in WhatsApp exports and prevent regex matching
            line_cleaned = line.lstrip('\u200e\u200f\ufeff')  # LTR mark, RTL mark, BOM

            # Try to match message boundary on cleaned line
            match = cls.BOUNDARY_PATTERN.match(line_cleaned)

            if match:
                # Save previous message if exists
                if current_message:
                    # Trim trailing whitespace from message text
                    current_message['message_text'] = current_message['message_text'].strip()
                    messages.append(current_message)

                # Parse new message
                date_str, time_str, sender, text = match.groups()

                try:
                    # Parse datetime (format: DD/MM/YY, HH:MM:SS AM/PM)
                    datetime_str = f"{date_str} {time_str.strip()}"
                    message_date = datetime.strptime(datetime_str, "%d/%m/%y %I:%M:%S %p")

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
            for msg in messages:
                msg_copy = msg.copy()

                # Calculate hash for deduplication
                msg_copy['message_hash'] = cls.calculate_message_hash(msg)

                # Convert datetime to ISO format
                if isinstance(msg_copy.get('message_date'), datetime):
                    msg_copy['message_date'] = msg_copy['message_date'].isoformat()

                messages_with_hash.append(msg_copy)

            # Insert into Supabase with upsert (ON CONFLICT DO NOTHING)
            client = SupabaseService._get_client()
            response = client.table("whatsapp_raw_messages").upsert(
                messages_with_hash,
                on_conflict='message_hash',
                ignore_duplicates=True
            ).execute()

            inserted_count = len(response.data) if response.data else 0
            skipped_count = len(messages) - inserted_count

            print(f"[WhatsAppParser] Inserted {inserted_count} new messages, skipped {skipped_count} duplicates")

            return {
                "success": True,
                "messages_inserted": inserted_count,
                "messages_skipped": skipped_count,
                "message": f"Inserted {inserted_count} messages, skipped {skipped_count} duplicates"
            }

        except Exception as e:
            print(f"[WhatsAppParser] Error inserting raw messages: {e}")
            return {
                "success": False,
                "messages_inserted": 0,
                "messages_skipped": 0,
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

