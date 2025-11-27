"""
WhatsApp Message Splitter Service

Uses LLM to detect and split messages containing multiple property listings.
"""

import os
import json
from typing import List, Dict, Any, Optional
from pathlib import Path
from openai import OpenAI


class WhatsAppMessageSplitterService:
    """
    Service for detecting and splitting WhatsApp messages with multiple listings
    """

    PROMPT_FILE = Path(__file__).parent.parent / "prompts" / "whatsapp_message_splitter.txt"
    _prompt_cache: Optional[str] = None
    _client: Optional[OpenAI] = None

    @classmethod
    def _get_client(cls) -> OpenAI:
        """Get or create OpenAI client"""
        if cls._client is None:
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY environment variable not set")
            cls._client = OpenAI(api_key=api_key)
        return cls._client

    @classmethod
    def _load_prompt(cls) -> str:
        """Load prompt from file (with caching)"""
        if cls._prompt_cache is None:
            with open(cls.PROMPT_FILE, 'r', encoding='utf-8') as f:
                cls._prompt_cache = f.read()
        return cls._prompt_cache

    @classmethod
    async def split_if_multiple(
        cls,
        message: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Analyze message and split if it contains multiple distinct property listings

        Args:
            message: Message dictionary with keys: message_date, sender_name, message_text, etc.

        Returns:
            List of message dictionaries. If single listing, returns [message].
            If multiple listings, returns [msg1, msg2, msg3, ...]
        """
        try:
            message_text = message.get('message_text', '').strip()

            # Skip empty messages
            if not message_text:
                return [message]

            # Skip very short messages (likely not multiple listings)
            if len(message_text) < 100:
                return [message]

            # Load prompt and format with message text
            prompt_template = cls._load_prompt()
            prompt = prompt_template.format(message_text=message_text)

            # Call OpenAI API with JSON mode
            client = cls._get_client()
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful assistant that analyzes real estate messages. Always respond with valid JSON."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                response_format={"type": "json_object"},
                temperature=0.1  # Low temperature for consistent output
            )

            # Parse LLM response
            result_text = response.choices[0].message.content
            result = json.loads(result_text)

            # Extract contact details from LLM response
            agent_name = result.get('common_agent_name')
            agent_mobile = result.get('common_agent_mobile')

            # Check if multiple listings detected
            if result.get('contains_multiple', False) and result.get('listings'):
                # Split into multiple messages
                split_messages = []
                listings = result['listings']

                for i, listing in enumerate(listings, 1):
                    split_msg = {
                        "message_date": message['message_date'],
                        "sender_name": message['sender_name'],
                        "message_text": listing['text'].strip(),
                        "is_deleted": False,
                        "is_media": False,
                        "source_file": message.get('source_file'),
                        "line_number": message.get('line_number'),
                        "split_from_original": True,  # Flag to indicate this was split
                        "split_index": i,  # Which part of the split (1, 2, 3...)
                        "extracted_agent_name": agent_name,  # LLM-extracted agent name
                        "extracted_agent_mobile": agent_mobile  # LLM-extracted mobile
                    }
                    split_messages.append(split_msg)

                print(f"[MessageSplitter] Split message from {message['sender_name']} into {len(split_messages)} parts")
                if agent_name or agent_mobile:
                    print(f"[MessageSplitter] Extracted contact: {agent_name} - {agent_mobile}")
                return split_messages
            else:
                # Keep as single message, but add extracted contact if available
                if agent_name or agent_mobile:
                    message['extracted_agent_name'] = agent_name
                    message['extracted_agent_mobile'] = agent_mobile
                return [message]

        except Exception as e:
            # On error, return original message (don't fail the whole pipeline)
            print(f"[MessageSplitter] Error processing message: {e}")
            return [message]

    @classmethod
    async def split_messages_batch(
        cls,
        messages: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Process a batch of messages and split any that contain multiple listings

        Args:
            messages: List of message dictionaries

        Returns:
            List of messages (some may be split, resulting in more messages than input)
        """
        result = []
        split_count = 0

        for message in messages:
            split_result = await cls.split_if_multiple(message)
            result.extend(split_result)

            # Track how many were split
            if len(split_result) > 1:
                split_count += 1

        print(f"[MessageSplitter] Processed {len(messages)} messages, split {split_count} into multiple parts")
        print(f"[MessageSplitter] Output: {len(result)} total messages")

        return result
