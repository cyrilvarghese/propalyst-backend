"""
WhatsApp Parser Service

Parses WhatsApp chat export files and stores messages in the database.
Implements the parsing specification from chat_chunks/chunk_100.txt.
"""

import re
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path

from services.supabase_service import SupabaseService
from models.whatsapp_raw_message import WhatsAppRawMessageCreate


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

    @classmethod
    async def insert_messages(
        cls,
        messages: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Insert parsed messages into the database

        Args:
            messages: List of message dictionaries

        Returns:
            Dictionary with success status and count
        """
        if not messages:
            return {
                "success": True,
                "messages_inserted": 0,
                "message": "No messages to insert"
            }

        try:
            # Convert datetime objects to ISO format strings for Supabase
            messages_for_insert = []
            for msg in messages:
                msg_copy = msg.copy()
                if isinstance(msg_copy.get('message_date'), datetime):
                    msg_copy['message_date'] = msg_copy['message_date'].isoformat()
                messages_for_insert.append(msg_copy)

            # Insert into Supabase
            client = SupabaseService._get_client()
            response = client.table("whatsapp_raw_messages").insert(messages_for_insert).execute()

            inserted_count = len(response.data) if response.data else 0

            return {
                "success": True,
                "messages_inserted": inserted_count,
                "message": f"Successfully inserted {inserted_count} messages"
            }

        except Exception as e:
            print(f"[WhatsAppParser] Error inserting messages: {e}")
            return {
                "success": False,
                "messages_inserted": 0,
                "message": f"Failed to insert messages: {str(e)}"
            }

    @classmethod
    async def parse_and_insert_file(
        cls,
        file_path: str
    ) -> Dict[str, Any]:
        """
        Parse a WhatsApp export file and insert all messages into database

        Args:
            file_path: Path to the WhatsApp export text file

        Returns:
            Dictionary with success status, counts, and any errors
        """
        try:
            # Parse file
            messages = cls.parse_file(file_path)

            # Insert messages
            insert_result = await cls.insert_messages(messages)

            return {
                "success": insert_result["success"],
                "messages_parsed": len(messages),
                "messages_inserted": insert_result["messages_inserted"],
                "message": insert_result["message"],
                "errors": None
            }

        except FileNotFoundError as e:
            return {
                "success": False,
                "messages_parsed": 0,
                "messages_inserted": 0,
                "message": str(e),
                "errors": [str(e)]
            }
        except Exception as e:
            return {
                "success": False,
                "messages_parsed": 0,
                "messages_inserted": 0,
                "message": f"Error processing file: {str(e)}",
                "errors": [str(e)]
            }

    @classmethod
    async def get_messages(
        cls,
        sender_name: Optional[str] = None,
        source_file: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        is_deleted: Optional[bool] = None,
        is_media: Optional[bool] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Retrieve messages from database with optional filters

        Args:
            sender_name: Filter by sender name (exact match)
            source_file: Filter by source file name
            date_from: Filter messages from this date onwards
            date_to: Filter messages up to this date
            is_deleted: Filter by deleted status
            is_media: Filter by media status
            limit: Maximum number of messages to return
            offset: Number of messages to skip

        Returns:
            List of message dictionaries
        """
        try:
            client = SupabaseService._get_client()
            query = client.table("whatsapp_raw_messages").select("*")

            # Apply filters
            if sender_name:
                query = query.eq("sender_name", sender_name)
            if source_file:
                query = query.eq("source_file", source_file)
            if date_from:
                query = query.gte("message_date", date_from.isoformat())
            if date_to:
                query = query.lte("message_date", date_to.isoformat())
            if is_deleted is not None:
                query = query.eq("is_deleted", is_deleted)
            if is_media is not None:
                query = query.eq("is_media", is_media)

            # Apply pagination and ordering
            query = query.order("message_date", desc=True)
            query = query.range(offset, offset + limit - 1)

            response = query.execute()
            return response.data or []

        except Exception as e:
            print(f"[WhatsAppParser] Error retrieving messages: {e}")
            raise
