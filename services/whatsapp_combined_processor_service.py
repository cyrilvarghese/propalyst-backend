"""
WhatsApp Combined Processor Service

Combines message splitting and structured data extraction into a single LLM call.
More efficient than calling split + extraction separately.
"""

import os
import json
from typing import List, Dict, Any, Optional
from pathlib import Path
from google import genai
from dotenv import load_dotenv

load_dotenv()


class WhatsAppCombinedProcessorService:
    """
    Service for processing WhatsApp messages with combined splitting + extraction
    """

    PROMPT_FILE = Path(__file__).parent.parent / "prompts" / "whatsapp_combined_processor.txt"
    _prompt_cache: Optional[str] = None
    _client: Optional[genai.Client] = None
    _model: str = "gemini-2.0-flash-exp"

    @classmethod
    def _get_client(cls) -> genai.Client:
        """Get or create Gemini client"""
        if cls._client is None:
            api_key = os.getenv("GEMINI_AI_API_KEY") or os.getenv("GOOGLE_API_KEY")
            if not api_key:
                raise ValueError("GEMINI_AI_API_KEY or GOOGLE_API_KEY environment variable not set")
            cls._client = genai.Client(api_key=api_key)
            print("[CombinedProcessor] ✓ Created Gemini client instance")
        return cls._client

    @classmethod
    def _load_prompt(cls) -> str:
        """Load prompt from file (with caching)"""
        if cls._prompt_cache is None:
            with open(cls.PROMPT_FILE, 'r', encoding='utf-8') as f:
                cls._prompt_cache = f.read()
        return cls._prompt_cache

    @classmethod
    async def process_message(
        cls,
        message: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Process message with combined splitting + extraction

        Args:
            message: Message dictionary with keys: message_date, sender_name, message_text, etc.

        Returns:
            List of message dictionaries with both text AND structured fields.
            If single listing, returns [message with structured fields].
            If multiple listings, returns [msg1, msg2, msg3, ...] each with structured fields.
        """
        try:
            message_text = message.get('message_text', '').strip()

            # Skip empty messages
            if not message_text:
                return [message]

            # Skip very short messages (likely not property listings)
            if len(message_text) < 50:
                # For short messages, still try to extract but likely won't split
                pass

            # Load prompt and format with message text
            prompt_template = cls._load_prompt()
            prompt = prompt_template.format(message_text=message_text)

            # Call Gemini API
            client = cls._get_client()
            response = client.models.generate_content(
                model=cls._model,
                contents=prompt
            )

            # Parse LLM response
            result_text = response.text.strip()

            # Clean up markdown code blocks if present
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0].strip()

            result = json.loads(result_text)

            # Get listings from response
            listings = result.get('listings', [])

            if not listings:
                # No listings returned, keep original message
                return [message]

            # Build output messages with both text and structured fields
            output_messages = []

            for i, listing in enumerate(listings, 1):
                # Create new message with original metadata
                processed_msg = {
                    "message_date": message['message_date'],
                    "sender_name": message['sender_name'],
                    "message_text": listing.get('text', message_text).strip(),
                    "is_deleted": False,
                    "is_media": False,
                    "source_file": message.get('source_file'),
                    "line_number": message.get('line_number'),
                }

                # Add split metadata if multiple listings
                if len(listings) > 1:
                    processed_msg["split_from_original"] = True
                    processed_msg["split_index"] = i
                else:
                    processed_msg["split_from_original"] = False

                # Add ALL structured fields from extraction
                processed_msg["message_type"] = listing.get('message_type')
                processed_msg["extracted_agent_name"] = listing.get('agent_name')
                processed_msg["extracted_agent_contact"] = listing.get('agent_contact')
                processed_msg["property_type"] = listing.get('property_type')
                processed_msg["bhk_config"] = listing.get('bhk_config')  # NEW: bedroom count
                processed_msg["area_sqft"] = listing.get('area_sqft')
                processed_msg["price"] = listing.get('price')
                processed_msg["price_text"] = listing.get('price_text')
                processed_msg["location"] = listing.get('location')
                processed_msg["project_name"] = listing.get('project_name')
                processed_msg["furnishing_status"] = listing.get('furnishing_status')
                processed_msg["parking_count"] = listing.get('parking_count')
                processed_msg["parking_text"] = listing.get('parking_text')
                processed_msg["facing_direction"] = listing.get('facing_direction')
                processed_msg["special_features"] = listing.get('special_features', [])
                processed_msg["llm_notes"] = listing.get('llm_notes')

                output_messages.append(processed_msg)

            # Log processing result
            if len(output_messages) > 1:
                print(f"[CombinedProcessor] Split message from {message['sender_name']} into {len(output_messages)} parts")
            else:
                print(f"[CombinedProcessor] Processed single message from {message['sender_name']}")

            # Log extracted structured data
            msg_types = [msg.get('message_type') for msg in output_messages]
            print(f"[CombinedProcessor] Message types: {msg_types}")

            return output_messages

        except Exception as e:
            # On error, return original message (don't fail the whole pipeline)
            print(f"[CombinedProcessor] Error processing message: {e}")
            return [message]

    @classmethod
    async def process_messages_batch(
        cls,
        messages: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Process a batch of messages with combined splitting + extraction

        Args:
            messages: List of message dictionaries

        Returns:
            List of messages (some may be split, all have structured fields)
        """
        result = []
        split_count = 0
        extraction_count = 0

        for message in messages:
            processed = await cls.process_message(message)
            result.extend(processed)

            # Track statistics
            if len(processed) > 1:
                split_count += 1
            if processed[0].get('message_type'):
                extraction_count += len(processed)

        print(f"[CombinedProcessor] Processed {len(messages)} messages")
        print(f"[CombinedProcessor] Split {split_count} messages into multiple parts")
        print(f"[CombinedProcessor] Extracted structured data from {extraction_count} listings")
        print(f"[CombinedProcessor] Output: {len(result)} total messages")

        return result
