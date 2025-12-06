"""
Properties Service
==================

Service for properties table operations with agent information.

Handles:
    - Fetching properties with pagination and filters
    - Searching properties by text query
    - Getting single property by ID

Data Source:
    - properties_with_agent VIEW (properties LEFT JOIN profiles)
    - Automatically includes agent details from profiles table

Agent Information (from profiles table via VIEW):
    - agent_name (profiles.full_name)
    - agent_contact (profiles.phone)
    - agent_email (profiles.email)
    - agent_company (profiles.company_name)
    - agent_avatar (profiles.avatar_url)
    - agent_vanity_url (profiles.vanity_url)
"""

from typing import Dict, Any, Optional
from services.supabase_client import get_supabase_client


class PropertiesService:
    """Service for properties table operations"""

    @classmethod
    async def get_properties(
        cls,
        limit: int = 100,
        offset: int = 0,
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Get properties from properties_with_agent view with pagination and filters

        Queries the properties_with_agent database view which automatically includes
        agent details from profiles table via LEFT JOIN.

        Args:
            limit: Maximum number of properties to return (default: 100)
            offset: Number of properties to skip for pagination (default: 0)
            filters: Optional dictionary of filters:
                - property_type: str (exact match on property_type field)
                - city: str (case-insensitive partial match on city field)
                - bedrooms: int (exact match on bedrooms field)
                - price_min: float (minimum price filter)
                - price_max: float (maximum price filter)

        Returns:
            Dictionary with success status and properties data:
            {
                "success": bool,
                "data": list of properties with agent details,
                "count": int,
                "message": str,
                "metadata": {"source": str, "filters_applied": dict}
            }

        Example:
            # Get first 50 properties
            result = await PropertiesService.get_properties(limit=50)

            # Get 3BHK properties in Bangalore
            result = await PropertiesService.get_properties(
                limit=100,
                filters={"city": "Bangalore", "bedrooms": 3}
            )

            # Get properties in price range
            result = await PropertiesService.get_properties(
                filters={"price_min": 5000000, "price_max": 10000000}
            )
        """
        try:
            client = get_supabase_client()

            # Query the view (includes agent info automatically via JOIN)
            query = client.table("properties_with_agent").select("*")

            # Apply filters if provided
            if filters:
                if filters.get("property_type"):
                    query = query.eq("property_type", filters["property_type"])

                if filters.get("city"):
                    query = query.ilike("city", f"%{filters['city']}%")

                if filters.get("bedrooms"):
                    query = query.eq("bedrooms", filters["bedrooms"])

                if filters.get("price_min"):
                    query = query.gte("price", filters["price_min"])

                if filters.get("price_max"):
                    query = query.lte("price", filters["price_max"])

            # Pagination and ordering
            query = query.order("created_at", desc=True).limit(limit).offset(offset)

            response = query.execute()

            properties = response.data if response.data else []

            filter_desc = f" with filters: {filters}" if filters else ""
            print(f"[PropertiesService] ✓ Retrieved {len(properties)} properties{filter_desc}")

            return {
                "success": True,
                "data": properties,
                "count": len(properties),
                "message": f"Retrieved {len(properties)} properties",
                "metadata": {
                    "source": "properties_with_agent",
                    "filters_applied": filters or {}
                }
            }

        except Exception as e:
            print(f"[PropertiesService] ✗ Error retrieving properties: {e}")
            return {
                "success": False,
                "data": [],
                "count": 0,
                "message": f"Error retrieving properties: {str(e)}",
                "error": str(e)
            }

    @classmethod
    async def search_properties(
        cls,
        query: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Search properties from properties_with_agent view

        Searches in multiple fields: title, description, city, area
        Uses case-insensitive pattern matching (ILIKE)
        Supports additional filters for refined results

        Args:
            query: Search text (searches in title, description, city, area fields)
            limit: Maximum number of results (default: 100)
            offset: Pagination offset (default: 0)
            filters: Optional dictionary of filters:
                - property_type: str (exact match)
                - bedrooms: int (exact match)
                - price_min: float (minimum price)
                - price_max: float (maximum price)

        Returns:
            Dictionary with success status and matching properties:
            {
                "success": bool,
                "data": list of matching properties,
                "count": int,
                "message": str
            }

        Search Logic:
            - Searches in: title, description, city, area (OR logic)
            - Applies filters with AND logic
            - Results sorted by created_at (newest first)

        Examples:
            # Search for "whitefield"
            result = await PropertiesService.search_properties(query="whitefield")

            # Search for "3bhk whitefield" with filters
            result = await PropertiesService.search_properties(
                query="whitefield",
                filters={"bedrooms": 3, "property_type": "apartment"}
            )

            # Get all properties (no query)
            result = await PropertiesService.search_properties(limit=100)
        """
        try:
            client = get_supabase_client()

            # Start with properties_with_agent view
            query_builder = client.table("properties_with_agent").select("*")

            # Apply text search if provided
            if query:
                # Search in title, description, city, area using OR logic
                # Each field checked with case-insensitive ILIKE
                search_filter = f"title.ilike.%{query}%,description.ilike.%{query}%,city.ilike.%{query}%,area.ilike.%{query}%"
                query_builder = query_builder.or_(search_filter)

            # Apply filters if provided (AND logic with search)
            if filters:
                if filters.get("property_type"):
                    query_builder = query_builder.eq("property_type", filters["property_type"])

                if filters.get("bedrooms"):
                    query_builder = query_builder.eq("bedrooms", filters["bedrooms"])

                if filters.get("price_min"):
                    query_builder = query_builder.gte("price", filters["price_min"])

                if filters.get("price_max"):
                    query_builder = query_builder.lte("price", filters["price_max"])

            # Pagination and ordering
            query_builder = query_builder.order("created_at", desc=True).limit(limit).offset(offset)

            response = query_builder.execute()

            properties = response.data if response.data else []

            query_desc = f" for query '{query}'" if query else ""
            filter_desc = f" with filters {filters}" if filters else ""
            print(f"[PropertiesService] ✓ Found {len(properties)} properties{query_desc}{filter_desc}")

            return {
                "success": True,
                "data": properties,
                "count": len(properties),
                "message": f"Found {len(properties)} properties"
            }

        except Exception as e:
            print(f"[PropertiesService] ✗ Error searching properties: {e}")
            return {
                "success": False,
                "data": [],
                "count": 0,
                "message": f"Error searching properties: {str(e)}",
                "error": str(e)
            }

    @classmethod
    async def get_property_by_id(cls, property_id: str) -> Dict[str, Any]:
        """
        Get a single property by ID from properties_with_agent view

        Args:
            property_id: UUID of the property

        Returns:
            Dictionary with success status and property data:
            {
                "success": bool,
                "data": property dict with agent details or None,
                "message": str
            }

        Example:
            result = await PropertiesService.get_property_by_id("uuid-here")
            if result["success"]:
                property_data = result["data"]
        """
        try:
            client = get_supabase_client()

            response = client.table("properties_with_agent")\
                .select("*")\
                .eq("id", property_id)\
                .execute()

            if response.data and len(response.data) > 0:
                property_data = response.data[0]
                print(f"[PropertiesService] ✓ Found property: {property_id}")
                return {
                    "success": True,
                    "data": property_data,
                    "message": "Property found"
                }
            else:
                print(f"[PropertiesService] ✗ Property not found: {property_id}")
                return {
                    "success": False,
                    "data": None,
                    "message": f"Property with ID {property_id} not found"
                }

        except Exception as e:
            print(f"[PropertiesService] ✗ Error retrieving property: {e}")
            return {
                "success": False,
                "data": None,
                "message": f"Error retrieving property: {str(e)}"
            }
