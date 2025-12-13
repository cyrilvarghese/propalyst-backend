"""
Localities Finding Module
===========================

Finds nearby localities using Google Search grounding with Gemini.
"""

import json
from typing import Dict, Any, Optional
from google import genai
from google.genai import types
from models.lead import NearbyLocality


class LocalitiesService:
    """Service for finding nearby localities using Google grounding search"""

    _gemini_client: Optional[genai.Client] = None

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
    async def find_nearby_localities(cls, location: str, limit: int = 5) -> Dict[str, Any]:
        """
        Find nearby localities using Google grounding search with Gemini.

        Uses Google Search grounding to find real, current nearby areas with distances.

        Args:
            location: Primary location to find nearby areas for
            limit: Maximum number of localities to return

        Returns:
            Dict with success, data (List[NearbyLocality]), message
        """
        try:
            print(f"[LocalitiesFinding] 🗺️ Finding nearby localities for {location} using Google grounding...")

            client = cls._get_gemini_client()

            # Configure Google Search grounding tool
            grounding_tool = types.Tool(google_search=types.GoogleSearch())

            # Create search prompt for nearby localities
            search_prompt = f"""Using current data, find {limit} localities and areas near {location} in Bangalore, India.

Include approximate distances in kilometers from the primary location.

Return ONLY valid JSON array (no markdown, no code blocks):
[
    {{"name": "Locality Name", "distance_km": 3.5}},
    {{"name": "Another Area", "distance_km": 2.1}}
]"""

            # Call Gemini with Google Search grounding
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=search_prompt,
                config=types.GenerateContentConfig(
                    tools=[grounding_tool],
                    temperature=0.1  # Low temperature for consistency
                )
            )

            # Extract and parse JSON from response
            response_text = response.text.strip()

            # Remove markdown code blocks if present
            if response_text.startswith("```json"):
                response_text = response_text[7:-3].strip()
            elif response_text.startswith("```"):
                response_text = response_text[3:-3].strip()

            # Parse JSON
            localities_list = json.loads(response_text)

            # Validate and create NearbyLocality objects
            nearby_localities = []
            for loc_data in localities_list[:limit]:
                try:
                    locality = NearbyLocality(**loc_data)
                    nearby_localities.append(locality)
                except Exception as e:
                    print(f"[LocalitiesFinding] ⚠️  Skipping invalid locality data: {loc_data}, error: {e}")
                    continue

            print(f"[LocalitiesFinding] ✓ Found {len(nearby_localities)} nearby localities for {location}")
            return {
                "success": True,
                "data": nearby_localities,
                "message": f"Found {len(nearby_localities)} nearby localities"
            }

        except json.JSONDecodeError as e:
            print(f"[LocalitiesFinding] ✗ Failed to parse localities JSON: {e}")
            return {
                "success": False,
                "data": [],
                "message": f"Failed to parse locality data: {str(e)}"
            }
        except Exception as e:
            print(f"[LocalitiesFinding] ✗ Error finding nearby localities: {e}")
            return {
                "success": False,
                "data": [],
                "message": f"Error finding localities: {str(e)}"
            }
