"""
Relevance scoring service using LLM to rank properties against user queries
"""
import os
import json
import time
import asyncio
from typing import Dict, Any
from pathlib import Path
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()


class RelevanceScoringService:
    """Service for scoring property relevance using LLM"""

    # ACTIVE: Structured prompt with matches/mismatches arrays and weighted scoring
    PROMPT_PATH = Path(__file__).parent.parent / "providers" / "scrapers" / "prompts" / "relevance_scoring_prompt_structured.txt"

    # INACTIVE: Simple prompt with just relevance_score and relevance_reason
    # PROMPT_PATH = Path(__file__).parent.parent / "providers" / "scrapers" / "prompts" / "relevance_scoring_prompt.txt"

    def __init__(self):
        """Initialize Gemini API and load prompt"""
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GEMINI_AI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY or GEMINI_AI_API_KEY not found in environment")

        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash-exp')

        # Load prompt template
        if self.PROMPT_PATH.exists():
            with open(self.PROMPT_PATH, 'r', encoding='utf-8') as f:
                self.prompt_template = f.read().strip()
        else:
            raise FileNotFoundError(f"Prompt template not found: {self.PROMPT_PATH}")

    async def score_single_property(self, property_data: Dict[str, Any], user_query: str) -> Dict[str, Any]:
        """
        Score a single property's relevance against user query

        Args:
            property_data: Property dictionary with all fields
            user_query: Original user search query

        Returns:
            Property dict with added relevance_score and relevance_reason
        """
        # Create a clean summary of property for LLM
        property_summary = {
            "title": property_data.get("title", ""),
            "location": property_data.get("location", ""),
            "price": property_data.get("price", ""),
            "bedrooms": property_data.get("bedrooms", ""),
            "bathrooms": property_data.get("bathrooms", ""),
            "area": property_data.get("area", ""),
            "facing": property_data.get("facing", ""),
            "parking": property_data.get("parking", ""),
            "flooring": property_data.get("flooring", ""),
            "furnishing": property_data.get("furnishing", ""),
            "description": property_data.get("description", "")[:200]  # Truncate description
        }

        # Format prompt template with property data
        prompt = self.prompt_template.format(
            user_query=user_query,
            property_summary=json.dumps(property_summary, indent=2)
        )

        # Retry logic for rate limiting
        max_retries = 3
        base_delay = 1  # seconds

        for attempt in range(max_retries):
            try:
                # Add delay between requests to avoid rate limiting (except first attempt)
                if attempt > 0:
                    delay = base_delay * (2 ** attempt)  # Exponential backoff
                    print(f"[RelevanceScoring] Retry {attempt + 1}/{max_retries} after {delay}s delay...")
                    await asyncio.sleep(delay)

                # Call Gemini API
                print(f"[RelevanceScoring] Calling Gemini API for property: {property_data.get('title', 'Unknown')[:50]}...")
                response = self.model.generate_content(prompt)
                response_text = response.text.strip()

                print(f"[RelevanceScoring] Raw LLM response (first 200 chars): {response_text[:200]}")

                # Remove markdown code blocks if present
                if response_text.startswith("```"):
                    response_text = response_text.split("```")[1]
                    if response_text.startswith("json"):
                        response_text = response_text[4:]
                    response_text = response_text.strip()

                print(f"[RelevanceScoring] Cleaned response (first 200 chars): {response_text[:200]}")

                # Parse JSON response
                scoring_result = json.loads(response_text)
                print(f"[RelevanceScoring] Parsed JSON successfully: score={scoring_result.get('relevance_score')}")

                # Validate score is between 1-10
                score = scoring_result.get("relevance_score", 5)
                if not isinstance(score, int) or score < 1 or score > 10:
                    print(f"[RelevanceScoring] WARNING: Invalid score {score}, defaulting to 5")
                    score = 5

                # Add scoring to property data
                property_data["relevance_score"] = score

                # Support both simple prompt format (relevance_reason) and structured format (matches/mismatches)
                if "relevance_reason" in scoring_result:
                    # Simple prompt format
                    property_data["relevance_reason"] = scoring_result.get("relevance_reason", "")
                elif "matches" in scoring_result or "mismatches" in scoring_result:
                    # Structured prompt format - convert arrays to readable reason
                    matches = scoring_result.get("matches", [])
                    mismatches = scoring_result.get("mismatches", [])

                    reason_parts = []
                    if matches:
                        reason_parts.append("Matches: " + "; ".join(matches))
                    if mismatches:
                        reason_parts.append("Mismatches: " + "; ".join(mismatches))

                    property_data["relevance_reason"] = ". ".join(reason_parts) if reason_parts else ""
                    property_data["matches"] = matches
                    property_data["mismatches"] = mismatches
                else:
                    property_data["relevance_reason"] = ""

                print(f"[RelevanceScoring] ✓ Successfully scored property: {score}/10")
                return property_data

            except json.JSONDecodeError as e:
                print(f"[RelevanceScoring] ✗ JSON Parse Error: {e}")
                print(f"[RelevanceScoring] Failed to parse response: {response_text[:500]}")
                property_data["relevance_score"] = 5
                property_data["relevance_reason"] = f"JSON parsing error: {str(e)[:100]}"
                return property_data

            except Exception as e:
                error_type = type(e).__name__
                error_msg = str(e)

                # Check if it's a rate limit error (ResourceExhausted)
                if "ResourceExhausted" in error_type or "429" in error_msg or "quota" in error_msg.lower() or "rate limit" in error_msg.lower():
                    print(f"[RelevanceScoring] ⚠ Rate limit hit (attempt {attempt + 1}/{max_retries}): {e}")

                    if attempt < max_retries - 1:
                        # Will retry with exponential backoff
                        continue
                    else:
                        # Last attempt failed, return with rate limit error
                        print(f"[RelevanceScoring] ✗ Rate limit exceeded after {max_retries} attempts")
                        property_data["relevance_score"] = 5
                        property_data["relevance_reason"] = "API rate limit exceeded. Please try again in a moment."
                        return property_data
                else:
                    # Non-rate-limit error, don't retry
                    print(f"[RelevanceScoring] ✗ Unexpected Error: {error_type}: {e}")
                    import traceback
                    print(f"[RelevanceScoring] Traceback: {traceback.format_exc()}")
                    print(f"[RelevanceScoring] Property title: {property_data.get('title', 'Unknown')}")
                    property_data["relevance_score"] = 5
                    property_data["relevance_reason"] = f"Scoring error: {error_type}"
                    return property_data

        # Shouldn't reach here, but just in case
        property_data["relevance_score"] = 5
        property_data["relevance_reason"] = "Failed to score after multiple retries"
        return property_data

    async def score_properties_batch(self, properties: list[Dict[str, Any]], user_query: str, batch_size: int = 10) -> list[Dict[str, Any]]:
        """
        Score multiple properties in batches to reduce API calls

        Args:
            properties: List of property dictionaries
            user_query: Original user search query
            batch_size: Number of properties to score per API call (default: 10)

        Returns:
            List of properties with added relevance_score and relevance_reason
        """
        print(f"[RelevanceScoring] Batch scoring {len(properties)} properties in batches of {batch_size}")

        scored_properties = []

        # Process properties in batches
        for i in range(0, len(properties), batch_size):
            batch = properties[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (len(properties) + batch_size - 1) // batch_size

            print(f"[RelevanceScoring] Processing batch {batch_num}/{total_batches} ({len(batch)} properties)...")

            # Score this batch
            scored_batch = await self._score_batch(batch, user_query)
            scored_properties.extend(scored_batch)

        print(f"[RelevanceScoring] ✓ Batch scoring complete. Scored {len(scored_properties)} properties")
        return scored_properties

    async def score_properties_batch_magicbricks(self, properties: list[Dict[str, Any]], user_query: str, batch_size: int = 10) -> list[Dict[str, Any]]:
        """
        Score multiple MagicBricks properties in batches (MagicBricks-specific field mapping)

        MagicBricks has different field names than SquareYards:
        - super_area instead of area
        - No bedrooms field
        - Different field availability

        Args:
            properties: List of MagicBricks property dictionaries
            user_query: Original user search query
            batch_size: Number of properties to score per API call (default: 10)

        Returns:
            List of properties with added relevance_score, relevance_reason, matches, mismatches
        """
        print(f"[RelevanceScoring] Batch scoring {len(properties)} MagicBricks properties in batches of {batch_size}")

        scored_properties = []

        # Process properties in batches
        for i in range(0, len(properties), batch_size):
            batch = properties[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (len(properties) + batch_size - 1) // batch_size

            print(f"[RelevanceScoring] Processing MagicBricks batch {batch_num}/{total_batches} ({len(batch)} properties)...")

            # Score this batch with MagicBricks field mapping
            scored_batch = await self._score_batch_magicbricks(batch, user_query)
            scored_properties.extend(scored_batch)

        print(f"[RelevanceScoring] ✓ MagicBricks batch scoring complete. Scored {len(scored_properties)} properties")
        return scored_properties

    async def _score_batch_magicbricks(self, properties: list[Dict[str, Any]], user_query: str) -> list[Dict[str, Any]]:
        """
        Score a single batch of MagicBricks properties (field-mapped version)

        Args:
            properties: List of MagicBricks property dictionaries (up to 10)
            user_query: Original user search query

        Returns:
            List of properties with scores
        """
        # Create summaries for MagicBricks properties with proper field mapping
        properties_summaries = []
        for idx, prop in enumerate(properties):
            summary = {
                "property_id": idx,
                "title": prop.get("title", ""),
                "location": "N/A",  # MagicBricks doesn't provide location
                "price": prop.get("price", ""),
                "bedrooms": "Not specified",  # MagicBricks doesn't extract bedrooms
                "area": prop.get("super_area", ""),  # MagicBricks uses super_area
                "facing": prop.get("facing", ""),
                "parking": prop.get("parking", ""),
                "furnishing": prop.get("furnishing", ""),
                "property_type": "Not specified",  # MagicBricks doesn't specify type in schema
                "bathroom": prop.get("bathroom", ""),
                "floor": prop.get("floor", ""),
                "balcony": prop.get("balcony", ""),
                "description": prop.get("description", "")[:500]  # Limit description length
            }
            properties_summaries.append(summary)

        # Build batch prompt from file with MagicBricks adaptation
        batch_prompt_template = self.prompt_template

        # Replace single property placeholder with batch properties array
        batch_prompt = batch_prompt_template.replace(
            "{property_summary}",
            f"Array of MagicBricks properties to evaluate:\n{json.dumps(properties_summaries, indent=2)}\n\nFor EACH property in this array, calculate a relevance_score (1-10) and provide matches/mismatches arrays.\n\nNOTE: MagicBricks properties have limited field availability (no bedrooms, no location, no property_type). Evaluate based on available fields."
        ).format(user_query=user_query)

        # Retry logic for rate limiting
        max_retries = 3
        base_delay = 1

        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    delay = base_delay * (2 ** attempt)
                    print(f"[RelevanceScoring] Retry {attempt + 1}/{max_retries} after {delay}s delay...")
                    await asyncio.sleep(delay)

                # Call Gemini API for the entire batch
                print(f"[RelevanceScoring] Calling Gemini API for MagicBricks batch of {len(properties)} properties...")
                response = self.model.generate_content(batch_prompt)
                response_text = response.text.strip()

                # Remove markdown code blocks if present
                if response_text.startswith("```"):
                    response_text = response_text.split("```")[1]
                    if response_text.startswith("json"):
                        response_text = response_text[4:]
                    response_text = response_text.strip()

                # Parse JSON response
                scoring_results = json.loads(response_text)

                # Validate it's a list
                if not isinstance(scoring_results, list):
                    raise ValueError("Expected JSON array response")

                # Map scores back to properties
                for result in scoring_results:
                    prop_id = result.get("property_id")
                    score = result.get("relevance_score", 5)

                    # Validate score
                    if not isinstance(score, int) or score < 1 or score > 10:
                        score = 5

                    # Add to property
                    if 0 <= prop_id < len(properties):
                        properties[prop_id]["relevance_score"] = score

                        # Support both simple prompt format (relevance_reason) and structured format (matches/mismatches)
                        if "relevance_reason" in result:
                            # Simple prompt format
                            properties[prop_id]["relevance_reason"] = result.get("relevance_reason", "")
                        elif "matches" in result or "mismatches" in result:
                            # Structured prompt format - convert arrays to readable reason
                            matches = result.get("matches", [])
                            mismatches = result.get("mismatches", [])

                            reason_parts = []
                            if matches:
                                reason_parts.append("Matches: " + "; ".join(matches))
                            if mismatches:
                                reason_parts.append("Mismatches: " + "; ".join(mismatches))

                            properties[prop_id]["relevance_reason"] = ". ".join(reason_parts) if reason_parts else ""
                            properties[prop_id]["matches"] = matches
                            properties[prop_id]["mismatches"] = mismatches
                        else:
                            properties[prop_id]["relevance_reason"] = ""

                print(f"[RelevanceScoring] ✓ Successfully scored MagicBricks batch of {len(properties)} properties")
                return properties

            except json.JSONDecodeError as e:
                print(f"[RelevanceScoring] ✗ JSON Parse Error in MagicBricks batch: {e}")
                print(f"[RelevanceScoring] Failed response: {response_text[:500]}")
                # Fall back to default scores
                for prop in properties:
                    prop["relevance_score"] = 5
                    prop["relevance_reason"] = f"Batch scoring failed: JSON error"
                return properties

            except Exception as e:
                error_type = type(e).__name__
                error_msg = str(e)

                if "ResourceExhausted" in error_type or "429" in error_msg or "quota" in error_msg.lower():
                    print(f"[RelevanceScoring] ⚠ Rate limit hit in MagicBricks batch (attempt {attempt + 1}/{max_retries})")

                    if attempt < max_retries - 1:
                        continue
                    else:
                        print(f"[RelevanceScoring] ✗ Rate limit exceeded after {max_retries} attempts")
                        for prop in properties:
                            prop["relevance_score"] = 5
                            prop["relevance_reason"] = "API rate limit exceeded"
                        return properties
                else:
                    print(f"[RelevanceScoring] ✗ MagicBricks batch scoring error: {error_type}: {e}")
                    for prop in properties:
                        prop["relevance_score"] = 5
                        prop["relevance_reason"] = f"Batch scoring error"
                    return properties

        # Fallback
        for prop in properties:
            prop["relevance_score"] = 5
            prop["relevance_reason"] = "Failed after retries"
        return properties

    async def _score_batch(self, properties: list[Dict[str, Any]], user_query: str) -> list[Dict[str, Any]]:
        """
        Score a single batch of properties in one API call

        Args:
            properties: List of property dictionaries (up to 10)
            user_query: Original user search query

        Returns:
            List of properties with scores
        """
        # Create summaries for all properties in the batch
        properties_summaries = []
        for idx, prop in enumerate(properties):
            summary = {
                "property_id": idx,
                "title": prop.get("title", ""),
                "location": prop.get("location", ""),
                "price": prop.get("price_crore", prop.get("price", "")),
                "bedrooms": prop.get("bedrooms", ""),
                "area": prop.get("area", ""),
                "facing": prop.get("facing", ""),
                "parking": prop.get("parking", ""),
                "furnishing": prop.get("furnishing", ""),
                "property_type": prop.get("property_type", ""),
                "description": prop.get("description", "")[:500]  # Limit description length
            }
            properties_summaries.append(summary)

        # Build batch prompt from file
        # ACTIVE: Loading structured prompt from relevance_scoring_prompt_structured.txt
        # For batch evaluation, format as array of properties with property_id field
        batch_prompt_template = self.prompt_template

        # Replace single property placeholder with batch properties array
        batch_prompt = batch_prompt_template.replace(
            "{property_summary}",
            f"Array of properties to evaluate:\n{json.dumps(properties_summaries, indent=2)}\n\nFor EACH property in this array, calculate a relevance_score (1-10) and provide matches/mismatches arrays."
        ).format(user_query=user_query)

        # Retry logic for rate limiting
        max_retries = 3
        base_delay = 1

        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    delay = base_delay * (2 ** attempt)
                    print(f"[RelevanceScoring] Retry {attempt + 1}/{max_retries} after {delay}s delay...")
                    await asyncio.sleep(delay)

                # Call Gemini API for the entire batch
                print(f"[RelevanceScoring] Calling Gemini API for batch of {len(properties)} properties...")
                response = self.model.generate_content(batch_prompt)
                response_text = response.text.strip()

                # Remove markdown code blocks if present
                if response_text.startswith("```"):
                    response_text = response_text.split("```")[1]
                    if response_text.startswith("json"):
                        response_text = response_text[4:]
                    response_text = response_text.strip()

                # Parse JSON response
                scoring_results = json.loads(response_text)

                # Validate it's a list
                if not isinstance(scoring_results, list):
                    raise ValueError("Expected JSON array response")

                # Map scores back to properties
                for result in scoring_results:
                    prop_id = result.get("property_id")
                    score = result.get("relevance_score", 5)

                    # Validate score
                    if not isinstance(score, int) or score < 1 or score > 10:
                        score = 5

                    # Add to property
                    if 0 <= prop_id < len(properties):
                        properties[prop_id]["relevance_score"] = score

                        # Support both simple prompt format (relevance_reason) and structured format (matches/mismatches)
                        if "relevance_reason" in result:
                            # Simple prompt format
                            properties[prop_id]["relevance_reason"] = result.get("relevance_reason", "")
                        elif "matches" in result or "mismatches" in result:
                            # Structured prompt format - convert arrays to readable reason
                            matches = result.get("matches", [])
                            mismatches = result.get("mismatches", [])

                            reason_parts = []
                            if matches:
                                reason_parts.append("Matches: " + "; ".join(matches))
                            if mismatches:
                                reason_parts.append("Mismatches: " + "; ".join(mismatches))

                            properties[prop_id]["relevance_reason"] = ". ".join(reason_parts) if reason_parts else ""
                            properties[prop_id]["matches"] = matches
                            properties[prop_id]["mismatches"] = mismatches
                        else:
                            properties[prop_id]["relevance_reason"] = ""

                print(f"[RelevanceScoring] ✓ Successfully scored batch of {len(properties)} properties")
                return properties

            except json.JSONDecodeError as e:
                print(f"[RelevanceScoring] ✗ JSON Parse Error in batch: {e}")
                print(f"[RelevanceScoring] Failed response: {response_text[:500]}")
                # Fall back to default scores
                for prop in properties:
                    prop["relevance_score"] = 5
                    prop["relevance_reason"] = f"Batch scoring failed: JSON error"
                return properties

            except Exception as e:
                error_type = type(e).__name__
                error_msg = str(e)

                if "ResourceExhausted" in error_type or "429" in error_msg or "quota" in error_msg.lower():
                    print(f"[RelevanceScoring] ⚠ Rate limit hit in batch (attempt {attempt + 1}/{max_retries})")

                    if attempt < max_retries - 1:
                        continue
                    else:
                        print(f"[RelevanceScoring] ✗ Rate limit exceeded after {max_retries} attempts")
                        for prop in properties:
                            prop["relevance_score"] = 5
                            prop["relevance_reason"] = "API rate limit exceeded"
                        return properties
                else:
                    print(f"[RelevanceScoring] ✗ Batch scoring error: {error_type}: {e}")
                    for prop in properties:
                        prop["relevance_score"] = 5
                        prop["relevance_reason"] = f"Batch scoring error"
                    return properties

        # Fallback
        for prop in properties:
            prop["relevance_score"] = 5
            prop["relevance_reason"] = "Failed after retries"
        return properties
