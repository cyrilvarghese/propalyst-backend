"""
WhatsApp Listing Extraction Service
====================================

Extracts structured data from raw WhatsApp messages using LLM analysis.
Processes messages from crea_wapp and stores clean data in whatsapp_listing_data table.
"""

import os
import json
from typing import Dict, Any, Optional
from pathlib import Path
from datetime import datetime
from google import genai
from dotenv import load_dotenv
from models.whatsapp_listing import (
    WhatsAppListingLLMInput,
    WhatsAppListingLLMOutput
)

load_dotenv()


class WhatsAppListingExtractionService:
    """Service for extracting structured data from WhatsApp messages using LLM"""

    # Shared Gemini client instance (singleton pattern)
    _client: Optional[genai.Client] = None
    _model: str = "gemini-2.5-flash"
    _prompt_cache: Optional[str] = None

    # Path to prompt file
    PROMPT_FILE = Path(__file__).parent.parent / "prompts" / "whatsapp_listing_extraction.txt"

    # Path to extraction log file
    EXTRACTION_LOG_FILE = Path(__file__).parent.parent / "data" / "extraction_log.txt"

    @classmethod
    def _load_prompt(cls) -> str:
        """Load prompt from file (with caching)"""
        if cls._prompt_cache is None:
            with open(cls.PROMPT_FILE, 'r') as f:
                cls._prompt_cache = f.read()
            print("[WhatsAppExtraction] ✓ Loaded prompt from file")
        return cls._prompt_cache

    @classmethod
    def _log_extraction(cls, message_id: str, raw_message: str, llm_response: str):
        """
        Log extraction to file for inspection

        Args:
            message_id: Message UUID
            raw_message: Original raw message
            llm_response: LLM response text
        """
        cls.EXTRACTION_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        log_entry = f"""
                    {'='*100}
                    EXTRACTION LOG - {timestamp}
                    Message ID: {message_id}
                    {'='*100}

                    BEFORE LLM - Raw Message:
                    {'-'*100}
                    {raw_message}
                    {'-'*100}

                    AFTER LLM - Response:
                    {'-'*100}
                    {llm_response}
                    {'-'*100}

                    {'='*100}

                    """

        with open(cls.EXTRACTION_LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(log_entry)

    @classmethod
    def _get_client(cls) -> genai.Client:
        """Get or create shared Gemini client instance (singleton)"""
        if cls._client is None:
            api_key = os.getenv("GEMINI_AI_API_KEY") or os.getenv("GOOGLE_API_KEY")

            if not api_key:
                raise ValueError("GEMINI_AI_API_KEY or GOOGLE_API_KEY must be set in environment")

            cls._client = genai.Client(api_key=api_key)
            print("[WhatsAppExtraction] ✓ Created shared Gemini client instance")

        return cls._client

    @classmethod
    async def extract_single_message(cls, raw_message: str, message_id: str = None) -> WhatsAppListingLLMOutput:
        """
        Extract structured data from a single raw WhatsApp message using LLM

        Args:
            raw_message: Raw WhatsApp message text
            message_id: Optional message ID for logging

        Returns:
            WhatsAppListingLLMOutput with structured extracted data

        Raises:
            Exception if LLM call fails or response is invalid
        """
        try:
            client = cls._get_client()

            # Load prompt from file and format with raw message
            prompt_template = cls._load_prompt()
            prompt = prompt_template.format(raw_message=raw_message)

            # Console log
            print(f"\n{'='*80}")
            print(f"[WhatsAppExtraction] BEFORE LLM - Raw Message ({len(raw_message)} chars):")
            print(f"{'='*80}")
            print(f"{raw_message[:200]}...")  # Console: first 200 chars only
            print(f"{'='*80}\n")

            # Call LLM
            response = client.models.generate_content(
                model=cls._model,
                contents=prompt
            )

            response_text = response.text.strip()

            # Console log
            print(f"\n{'='*80}")
            print(f"[WhatsAppExtraction] AFTER LLM - Full Response ({len(response_text)} chars):")
            print(f"{'='*80}")
            print(f"{response_text[:200]}...")  # Console: first 200 chars only
            print(f"{'='*80}\n")

            # Write full details to file for inspection
            if message_id:
                cls._log_extraction(message_id, raw_message, response_text)

            # Clean up markdown code blocks if present
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()

            # Parse JSON response
            extracted_data = json.loads(response_text)

            # Validate and create Pydantic model
            listing_output = WhatsAppListingLLMOutput(**extracted_data)

            print(f"[WhatsAppExtraction] ✓ Successfully extracted data (type: {listing_output.message_type})")

            return listing_output

        except json.JSONDecodeError as e:
            print(f"[WhatsAppExtraction] ✗ Failed to parse LLM JSON response: {e}")
            print(f"[WhatsAppExtraction] Raw response: {response_text[:500]}")
            raise Exception(f"Failed to parse LLM response as JSON: {str(e)}")

        except Exception as e:
            print(f"[WhatsAppExtraction] ✗ Error extracting message: {e}")
            raise Exception(f"Failed to extract message data: {str(e)}")
