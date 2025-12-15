"""
Lead Service
============

Main orchestration service for creating leads from natural language queries.
Combines criteria extraction, property matching, and nearby locality finding.
"""

import uuid
from typing import Dict, Any, List
from datetime import datetime

from models.lead import CreateLeadResponse
from models.whatsapp_listing import WhatsAppListingData
from .extraction import CriteriaExtractionService
from .matching import PropertyMatchingService
from .localities import LocalitiesService
from .persistence import LeadPersistenceService


class LeadService:
    """Main orchestration service for lead creation and management"""

    @classmethod
    async def extract_detailed_criteria(cls, query: str) -> Dict[str, Any]:
        """Extract detailed criteria from natural language query"""
        return await CriteriaExtractionService.extract_detailed_criteria(query)

    @classmethod
    async def match_properties_from_criteria(cls, criteria, limit: int = 100) -> List[WhatsAppListingData]:
        """Match properties from Supabase based on criteria"""
        return await PropertyMatchingService.match_properties_from_criteria(criteria, limit)

    @classmethod
    async def find_nearby_localities(cls, location: str, limit: int = 5) -> Dict[str, Any]:
        """Find nearby localities for a location"""
        return await LocalitiesService.find_nearby_localities(location, limit)

    @classmethod
    async def create_lead(cls, query: str, name: str, contact_number: str) -> Dict[str, Any]:
        """
        Create a lead from natural language query.

        WORKFLOW:
        =========
        1. Extract criteria from query using Gemini LLM (25 fields total)
        2. Find nearby localities using Google Search grounding
        3. Match properties from Supabase whatsapp_listings_relevant table
        4. Generate unique lead ID and save to JSON file
        5. Return lead with extracted criteria, matched properties, and nearby localities

        Args:
            query: Natural language property search query
                   Example: "3BHK in Whitefield, budget 5 crores, possession in 6 months"
            name: Name of the lead (person's name)
            contact_number: Contact number of the lead

        Returns:
            Dict with success, data (CreateLeadResponse), message
        """
        try:
            print(f"[LeadService] 📝 Creating lead from query...")

            # STEP 1: Extract criteria from natural language
            extraction_result = await CriteriaExtractionService.extract_detailed_criteria(query)
            if not extraction_result["success"]:
                return extraction_result

            criteria_response = extraction_result["data"]
            criteria = criteria_response.matched_criteria

            # STEP 2: Find nearby localities if location is present
            if criteria.property.location:
                nearby_result = await LocalitiesService.find_nearby_localities(criteria.property.location)
                if nearby_result["success"] and nearby_result["data"]:
                    criteria_response.nearby_localities = nearby_result["data"]
                else:
                    print(f"[LeadService] ⚠️  Could not find nearby localities for {criteria.property.location}")

            # STEP 3: Match properties from Supabase
            matched_properties = await PropertyMatchingService.match_properties_from_criteria(criteria, limit=100)

            print(f"[LeadService] ✓ Matched {len(matched_properties)} properties")

            # STEP 4: Generate lead ID and timestamp
            lead_id = str(uuid.uuid4())
            created_at = datetime.now().isoformat()

            # STEP 5: Create lead response
            lead_data = CreateLeadResponse(
                lead_id=lead_id,
                query=query,
                name=name,
                contact_number=contact_number,
                extracted_criteria=criteria,
                missing_criteria=criteria_response.missing_criteria,
                matched_properties=[prop.dict() for prop in matched_properties],
                nearby_localities=criteria_response.nearby_localities,
                created_at=created_at,
                status="new"
            )

            # STEP 6: Save lead to JSON file
            lead_dict = {
                "id": lead_id,
                "query": query,
                "name": name,
                "contact_number": contact_number,
                "extracted_criteria": criteria.dict(),
                "missing_criteria": criteria_response.missing_criteria,
                "matched_properties": [prop.dict() for prop in matched_properties],
                "nearby_localities": [loc.dict() for loc in criteria_response.nearby_localities] if criteria_response.nearby_localities else [],
                "created_at": created_at,
                "status": "new"
            }
            LeadPersistenceService.save_lead(lead_dict)

            print(f"[LeadService] ✓ Created lead with ID: {lead_id}")
            return {
                "success": True,
                "data": lead_data,
                "message": f"Lead created with {len(matched_properties)} matched properties"
            }

        except Exception as e:
            print(f"[LeadService] ✗ Error creating lead: {e}")
            return {
                "success": False,
                "data": None,
                "message": f"Error creating lead: {str(e)}"
            }
