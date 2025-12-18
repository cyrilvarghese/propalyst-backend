"""
Lead Criteria Extraction Module
================================

Extracts detailed lead criteria from natural language queries using Gemini LLM.
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from google import genai
from models.lead import (
    DetailedCriteria,
    PropertyCriteria,
    ProximityPreferences,
    UserJourney,
    ExtractDetailedCriteriaResponse
)


class CriteriaExtractionService:
    """Service for extracting lead criteria from natural language using Gemini LLM"""

    # File paths
    PROMPT_FILE = Path(__file__).parent.parent.parent / "prompts" / "lead" / "criteria_extraction.txt"

    # Cache
    _prompt_cache: Optional[str] = None
    _gemini_client: Optional[genai.Client] = None

    @classmethod
    def _load_prompt(cls) -> str:
        """Load prompt from file (with caching)"""
        if cls._prompt_cache is None:
            with open(cls.PROMPT_FILE, 'r', encoding='utf-8') as f:
                cls._prompt_cache = f.read()
        return cls._prompt_cache

    @classmethod
    def _get_gemini_client(cls) -> genai.Client:
        """Get singleton Gemini client"""
        if cls._gemini_client is None:
            import os
            api_key = os.getenv("GEMINI_AI_API_KEY")
            if not api_key:
                raise ValueError("GEMINI_AI_API_KEY not found in environment")
            cls._gemini_client = genai.Client(api_key=api_key)
        return cls._gemini_client

    @classmethod
    def _detect_missing_criteria(cls, criteria: DetailedCriteria) -> List[str]:
        """Detect which criteria are missing from extraction"""
        missing = []

        # Check property criteria
        if criteria.property.bhk is None:
            missing.append("bhk")
        if criteria.property.budget_min is None and criteria.property.budget_max is None:
            missing.append("budget")

        # Check area (all variants: area_sqft, plot_size, built_up_area)
        has_any_area = any([
            criteria.property.area_sqft_min,
            criteria.property.area_sqft_max,
            criteria.property.plot_size_min,
            criteria.property.plot_size_max,
            criteria.property.built_up_area_min,
            criteria.property.built_up_area_max
        ])
        if not has_any_area:
            missing.append("area")

        if criteria.property.property_type is None:
            missing.append("property_type")
        if criteria.property.property_age is None:
            missing.append("property_age")

        # Check location (both single and multiple variants)
        if not criteria.property.location and not criteria.property.locations:
            missing.append("location")

        if criteria.property.req_type is None:
            missing.append("req_type")

        # Note: property_status and special_features are optional, don't flag as missing

        # Check proximity (only if all are false)
        if not any([
            criteria.proximity.near_school,
            criteria.proximity.near_airport,
            criteria.proximity.near_hospital,
            criteria.proximity.near_shopping_mall
        ]):
            missing.append("proximity_preferences")

        # Check user journey
        if criteria.user_journey.possession_timeline is None:
            missing.append("possession_timeline")
        if criteria.user_journey.time_in_market is None:
            missing.append("time_in_market")
        if criteria.user_journey.agents_contacted is None:
            missing.append("agents_contacted")

        return missing

    @classmethod
    async def extract_detailed_criteria(cls, query: str) -> Dict[str, Any]:
        """
        Extract detailed criteria from natural language query using Gemini.

        Args:
            query: Natural language property search query

        Returns:
            Dict with success, data (ExtractDetailedCriteriaResponse), message
        """
        try:
            print(f"[CriteriaExtraction] 🔍 Extracting criteria from: {query[:100]}...")

            # Load prompt and format with query
            prompt_template = cls._load_prompt()
            extraction_prompt = prompt_template.format(query=query)

            # Call Gemini API
            client = cls._get_gemini_client()
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=extraction_prompt
            )

            # Parse JSON from response
            json_text = response.text.strip()
            if json_text.startswith("```json"):
                json_text = json_text[7:-3].strip()
            elif json_text.startswith("```"):
                json_text = json_text[3:-3].strip()

            criteria_dict = json.loads(json_text)

            # Validate with Pydantic models
            property_criteria = PropertyCriteria(**criteria_dict["property"])
            proximity_prefs = ProximityPreferences(**criteria_dict["proximity"])
            user_journey = UserJourney(**criteria_dict["user_journey"])

            # POST-PROCESSING: Apply deterministic defaults for consistency
            # Fix 1: Always set req_type to 'demand_buy' if not extracted
            if property_criteria.req_type is None:
                property_criteria.req_type = "demand_buy"
                print(f"[CriteriaExtraction] ⚙️  Defaulted req_type to 'demand_buy'")

            # Fix 2: For single budget values, ensure both min and max are set
            # "budget 5 crores" should apply ±20% range (4-6 crores)
            if property_criteria.budget_max is not None and property_criteria.budget_min is None:
                property_criteria.budget_min = property_criteria.budget_max
                print(f"[CriteriaExtraction] ⚙️  Set budget_min = budget_max ({property_criteria.budget_max}cr) for ±20% range")

            criteria = DetailedCriteria(
                property=property_criteria,
                proximity=proximity_prefs,
                user_journey=user_journey
            )

            # Detect missing criteria
            missing = cls._detect_missing_criteria(criteria)

            response_data = ExtractDetailedCriteriaResponse(
                matched_criteria=criteria,
                missing_criteria=missing,
                nearby_localities=[]  # Will be populated by LocalitiesService
            )

            print(f"[CriteriaExtraction] ✓ Extracted {len(criteria_dict['property'])} property fields, {len(missing)} missing criteria")
            return {
                "success": True,
                "data": response_data,
                "message": f"Extracted criteria with {len(missing)} missing fields"
            }

        except Exception as e:
            print(f"[CriteriaExtraction] ✗ Error extracting criteria: {e}")
            return {
                "success": False,
                "data": None,
                "message": f"Error extracting criteria: {str(e)}"
            }
