"""
Relevance scoring service using LLM to rank properties against user queries
"""
import os
import json
import time
import asyncio
from typing import Dict, Any
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()


class RelevanceScoringService:
    """Service for scoring property relevance using LLM"""

    def __init__(self):
        """Initialize Gemini API"""
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GEMINI_AI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY or GEMINI_AI_API_KEY not found in environment")

        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash-exp')

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

        prompt = f"""You are a real estate expert. Score how well this property matches the user's search query by analyzing each requirement.

User Query: "{user_query}"

Property Details:
{json.dumps(property_summary, indent=2)}

IMPORTANT: When evaluating fields, if information appears in EITHER the structured fields OR the description, consider it valid.
- If "facing" field OR description mentions the facing direction, use that for scoring
- If there are different values in both places, give benefit of doubt - if EITHER matches the user's query, mark it as a match

Evaluation Criteria - Analyze each parameter:

1. BEDROOMS/BHK:
   - Extract number of bedrooms from user query (e.g., "2bhk" = 2 bedrooms)
   - Exact match = high score, mismatch = significant penalty
   - Example: User wants 2 BHK but property is 5 BHK = major mismatch

2. AREA/SIZE:
   - Extract square footage from query (e.g., "200 square feet", "1200 sqft")
   - Within ±20% = good match, outside range = penalty
   - If not specified in query, don't penalize

3. FACING/DIRECTION:
   - Extract direction from query (e.g., "east facing", "north facing")
   - Exact match = bonus, opposite direction = penalty
   - If not specified in query, don't penalize

4. PARKING:
   - Extract parking requirements (e.g., "2 car parking", "covered parking")
   - Count covered and open parking separately
   - Exact match or more = good, less than required = penalty
   - If not specified in query, don't penalize

5. PRICE:
   - Extract budget from query if mentioned (e.g., "under 5 crores")
   - Within budget = good, significantly over = penalty
   - If not specified in query, don't penalize

6. LOCATION:
   - Check if user specified locality/area
   - Same locality = bonus, nearby = acceptable
   - If not specified in query, don't penalize

7. FURNISHING:
   - Extract furnishing preference (e.g., "furnished", "unfurnished")
   - Match = bonus, mismatch = minor penalty
   - If not specified in query, don't penalize

8. PROPERTY TYPE:
   - Check if user wants specific type (e.g., "villa", "apartment", "house")
   - Match = bonus, mismatch = minor penalty
   - If not specified in query, don't penalize

Scoring Guidelines:
- 10 = Perfect match on all specified requirements
- 8-9 = Matches all major requirements (bedrooms, area, facing), minor differences on others
- 6-7 = Matches some major requirements, misses others (e.g., correct facing but wrong bedrooms)
- 4-5 = Matches only 1-2 requirements, significant mismatches on major parameters
- 2-3 = Matches almost nothing, major mismatches on bedrooms, area, or facing
- 1 = Complete mismatch, opposite of what user wants

IMPORTANT: In your reason, be SPECIFIC about what matches and what doesn't:
- Start with matches: "Matches: east facing ✓, 2 car parking ✓"
- Then mismatches: "Mismatches: 5 BHK instead of 2 BHK ✗, 1200 sqft instead of 200 sqft ✗"
- Format: "Matches: [list matching criteria]. Mismatches: [list non-matching criteria]."

Respond ONLY with valid JSON in this exact format (no markdown, no additional text):
{{
  "relevance_score": 8,
  "relevance_reason": "Matches: east facing ✓, 2 parking spots ✓. Mismatches: 5 BHK instead of 2 BHK ✗, 1200 sqft vs 200 sqft ✗."
}}"""

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
                property_data["relevance_reason"] = scoring_result.get("relevance_reason", "")

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

        # Build batch prompt
        prompt = f"""You are a real estate expert. Score how well EACH property matches the user's search query.

User Query: "{user_query}"

Properties to evaluate:
{json.dumps(properties_summaries, indent=2)}

IMPORTANT: Evaluate EACH property separately. For each property, if information appears in EITHER the structured fields OR the description, consider it valid.

Evaluation Criteria - Analyze each parameter for EACH property:

1. BEDROOMS/BHK: Exact match = high score, mismatch = significant penalty
2. AREA/SIZE: Within ±20% = good match, outside range = penalty
3. FACING/DIRECTION: Exact match = bonus, opposite direction = penalty
4. PARKING: Exact match or more = good, less than required = penalty
5. PRICE: Within budget = good, significantly over = penalty
6. LOCATION: Same locality = bonus, nearby = acceptable
7. FURNISHING: Match = bonus, mismatch = minor penalty
8. PROPERTY TYPE: Match = bonus, mismatch = minor penalty

Scoring Guidelines (for EACH property):
- 10 = Perfect match on all specified requirements
- 8-9 = Matches all major requirements
- 6-7 = Matches some major requirements, misses others
- 4-5 = Matches only 1-2 requirements
- 2-3 = Matches almost nothing
- 1 = Complete mismatch

Respond ONLY with valid JSON array (no markdown, no additional text):
[
  {{
    "property_id": 0,
    "relevance_score": 8,
    "relevance_reason": "Matches: east facing ✓, 2 parking spots ✓. Mismatches: 5 BHK instead of 2 BHK ✗."
  }},
  {{
    "property_id": 1,
    "relevance_score": 3,
    "relevance_reason": "Matches: location ✓. Mismatches: wrong BHK ✗, wrong facing ✗, insufficient parking ✗."
  }}
]"""

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
                response = self.model.generate_content(prompt)
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
                    reason = result.get("relevance_reason", "")

                    # Validate score
                    if not isinstance(score, int) or score < 1 or score > 10:
                        score = 5

                    # Add to property
                    if 0 <= prop_id < len(properties):
                        properties[prop_id]["relevance_score"] = score
                        properties[prop_id]["relevance_reason"] = reason

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
