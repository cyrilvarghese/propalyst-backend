"""
Gemini Search Provider
======================

Property search using Google Gemini API with Search Grounding.

Official documentation: https://ai.google.dev/gemini-api/docs/google-search#python
"""

import json
from typing import List
from google import genai
from google.genai import types

from models.search import PropertySearchParams, PropertyResult, GroundingSource
from .base import BaseSearchProvider


class GeminiSearchProvider(BaseSearchProvider):
    """
    Search provider using Google Gemini API with grounding.

    Features:
    - Real-time Google Search grounding for current property listings
    - LLM-based parameter extraction and inference
    - Citations and source tracking
    """

    def __init__(self, api_key: str):
        super().__init__(api_key)
        self.client = genai.Client(api_key=api_key)
        self.model = "gemini-2.0-flash-exp"  # Latest model with grounding support

    async def extract_parameters(self, query: str) -> PropertySearchParams:
        """
        Extract structured parameters from natural language query using Gemini.

        Example:
        Input: "3bhk property near indiranagar 100ft road with budget 4-7 crores"
        Output: PropertySearchParams(
            property_type="3BHK",
            category="residential",
            location="Indiranagar",
            budget_min=4.0,
            budget_max=7.0,
            keywords=["100ft road"]
        )
        """

        extraction_prompt = f"""You are a property search parameter extractor for Bangalore, India.

Extract structured search parameters from this query:
"{query}"

Apply these inference rules:
1. If "BHK" mentioned (1BHK, 2BHK, 3BHK, etc.) → category is "residential"
2. If "office", "shop", "commercial" mentioned → category is "commercial"
3. Extract location names (Bangalore neighborhoods/areas)
4. Parse budget:
   - "lakhs" = multiply by 0.01 crores
   - "crores" = use as is
   - "4-7 crores" → budget_min=4, budget_max=7
5. Extract additional keywords (like "100ft road", "near metro", etc.)

Return ONLY valid JSON matching this exact schema:
{{
    "property_type": "3BHK" or null,
    "category": "residential" or "commercial",
    "location": "Indiranagar" or null,
    "budget_min": 4.0 or null,
    "budget_max": 7.0 or null,
    "keywords": ["100ft road"] or [],
    "city": "Bangalore"
}}

JSON output:"""

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=extraction_prompt
            )

            # Parse JSON from response
            json_text = response.text.strip()
            if json_text.startswith("```json"):
                json_text = json_text[7:-3].strip()
            elif json_text.startswith("```"):
                json_text = json_text[3:-3].strip()

            params_dict = json.loads(json_text)
            return PropertySearchParams(**params_dict)

        except Exception as e:
            print(f"⚠️ Parameter extraction failed: {e}")
            # Fallback: basic parameters
            return PropertySearchParams(
                keywords=[query],
                city="Bangalore"
            )

    def _build_search_query(self, params: PropertySearchParams, source: str = "") -> str:
        """
        Build optimized search query using Google Search operators.

        Google Search Operators Used:
        - site: - Restrict to specific property websites
        - intitle: - Find keywords in page titles
        - "quotes" - Exact phrase matching
        - OR - Search multiple variants
        - .. - Number range (for prices)

        Example:
        Input: PropertySearchParams(property_type="3BHK", location="Indiranagar", budget_max=7)
        Output: site:magicbricks.com "3BHK" "residential" "Indiranagar" "Bangalore"
        """
        query_parts = []

        # Add site: operator based on source
        site_map = {
            "magicbricks": "magicbricks.com",
            "housing": "housing.com",
            "99acres": "99acres.com",
            "nobroker": "nobroker.com",
            "commonfloor": "commonfloor.com",
            "squareyards": "squareyards.com"
        }

        # Handle multiple sources with OR operator
        if source:
            source_list = [s.strip() for s in source.split(',') if s.strip()]
            site_queries = []
            for src in source_list:
                if src in site_map:
                    site_queries.append(f"site:{site_map[src]}")

            if site_queries:
                # Combine multiple sites with OR operator
                query_parts.append(f"({' OR '.join(site_queries)})")

        # Use exact phrases for better matching
        if params.property_type:
            query_parts.append(f'"{params.property_type}"')

        if params.category:
            query_parts.append(f'"{params.category}"')

        # Property for sale keyword
        query_parts.append('"for sale" OR "buy"')

        # Location with exact match
        if params.location:
            query_parts.append(f'"{params.location}"')

        if params.city:
            query_parts.append(f'"{params.city}"')

        # Budget range (if specified)
        if params.budget_min and params.budget_max:
            # Convert crores to lakhs for better search matching
            min_lakhs = int(params.budget_min * 100)
            max_lakhs = int(params.budget_max * 100)
            query_parts.append(f'"{min_lakhs}..{max_lakhs} lakh" OR "{params.budget_min}..{params.budget_max} crore"')
        elif params.budget_max:
            max_lakhs = int(params.budget_max * 100)
            query_parts.append(f'"under {max_lakhs} lakh" OR "under {params.budget_max} crore"')

        # Add keywords (exact phrases)
        if params.keywords:
            for keyword in params.keywords:
                query_parts.append(f'"{keyword}"')

        return " ".join(query_parts)

    async def search(self, params: PropertySearchParams, source: str = "") -> List[PropertyResult]:
        """
        Search for properties using Gemini with Google Search grounding.

        This method:
        1. Builds optimized search query from parameters (with site: operator)
        2. Uses Gemini's grounding tool to search Google in real-time
        3. Extracts property results from grounded response
        """

        search_query = self._build_search_query(params, source)
        print(f"🔍 Search query with operators: {search_query}")

        # Configure Google Search grounding tool
        grounding_tool = types.Tool(google_search=types.GoogleSearch())

        try:
            # Generate response with grounding
            response = self.client.models.generate_content(
                model=self.model,
                contents=f"""Find and list property listings matching this search:
{search_query}

For each property, extract:
- Title/heading
- Price (if available)
- Location
- Brief description
- Source URL

Format as a list of properties.""",
                config=types.GenerateContentConfig(
                    tools=[grounding_tool]
                )
            )

            # Extract grounding sources (citations)
            sources = self._extract_grounding_sources(response)
            print(f"📚 Found {len(sources)} grounding sources")

            # Parse results from response
            results = self._parse_property_results(response, sources, params)
            print(f"🏠 Found {len(results)} properties")

            return results

        except Exception as e:
            print(f"❌ Search failed: {e}")
            return []

    def _extract_grounding_sources(self, response) -> List[GroundingSource]:
        """
        Extract grounding sources (citations) from Gemini response.

        Gemini provides groundingMetadata with:
        - groundingChunks: List of sources used
        - groundingSupports: Mappings between text and sources
        """
        sources = []

        try:
            # Access grounding metadata if available
            if hasattr(response, 'candidates') and response.candidates:
                candidate = response.candidates[0]
                if hasattr(candidate, 'grounding_metadata'):
                    metadata = candidate.grounding_metadata

                    # Extract grounding chunks (sources)
                    if hasattr(metadata, 'grounding_chunks'):
                        for chunk in metadata.grounding_chunks:
                            if hasattr(chunk, 'web'):
                                sources.append(GroundingSource(
                                    title=getattr(chunk.web, 'title', 'Unknown'),
                                    url=getattr(chunk.web, 'uri', ''),
                                    snippet=None
                                ))

        except Exception as e:
            print(f"⚠️ Could not extract grounding sources: {e}")

        return sources

    def _parse_property_results(
        self,
        response,
        sources: List[GroundingSource],
        params: PropertySearchParams
    ) -> List[PropertyResult]:
        """
        Parse property results from Gemini response text.

        This is a simple parser - in production, you might use:
        - More structured output
        - JSON mode
        - Function calling
        """
        results = []

        try:
            response_text = response.text

            # For now, create mock results based on sources
            # In production, Gemini would structure this better
            for i, source in enumerate(sources[:10]):  # Limit to 10 results
                results.append(PropertyResult(
                    title=source.title,
                    url=source.url,
                    snippet=f"Property listing from {source.url}",
                    price=None,  # Would be extracted from response
                    location=params.location,
                    property_type=params.property_type,
                    source="google_search"
                ))

        except Exception as e:
            print(f"⚠️ Could not parse results: {e}")

        return results
