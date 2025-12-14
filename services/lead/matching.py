"""
Property Matching Module
=========================

Matches WhatsApp listings from Supabase based on extracted lead criteria.
"""

from typing import Dict, Any, List
from datetime import datetime
from pathlib import Path
from models.lead import DetailedCriteria
from models.whatsapp_listing import WhatsAppListingData


class PropertyMatchingService:
    """Service for matching properties from Supabase based on lead criteria"""

    @staticmethod
    async def match_properties_from_criteria(
        criteria: DetailedCriteria,
        limit: int = 100
    ) -> List[WhatsAppListingData]:
        """
        Match WhatsApp listings from Supabase based on lead criteria.

        FILTER LOGIC OVERVIEW:
        =====================

        AND Filters (All must match):
        - BHK: Exact match on bedroom_count
        - Price: ±20% tolerance (convert crores to rupees)
        - Property Type: Exact match (apartment, villa, etc.)
        - req_type: Maps to message_type (supply_sale, demand_buy, etc.)
        - Furnishing Status: Exact match (furnished, unfurnished, etc.)

        OR Filters (Match ANY):
        - Multiple Locations: Match if property is in ANY of the specified locations
        - Special Features: Match if property has ANY of the requested features
        - Property Status Keywords: Match ANY status keyword in text

        Location Matching:
        - Single location: Simple fuzzy match in raw_message
        - Multiple locations: OR logic - match if in ANY location

        Security:
        - Uses parameterized queries via Supabase client (no SQL injection risk)
        - All user input is validated by Pydantic before reaching this method

        Args:
            criteria: Extracted lead criteria from LLM (validated by Pydantic)
            limit: Max properties to return (default: 100)

        Returns:
            List of matched property dictionaries from whatsapp_listings_relevant table
        """
        try:
            from services.supabase_client import get_supabase_client

            print(f"[PropertyMatching] 🔍 Matching properties for criteria...")

            # Initialize Supabase client and query builder
            client = get_supabase_client()
            query = client.table("whatsapp_listings_relevant").select("*")

            # Track filters for debugging
            filters_applied = []
            query_log = []

            # Log header
            query_log.append(f"=== Property Matching Query Debug Log ===")
            query_log.append(f"Timestamp: {datetime.now().isoformat()}")
            query_log.append(f"\nInput Criteria:")
            query_log.append(f"  BHK: {criteria.property.bhk}")
            query_log.append(f"  Budget: {criteria.property.budget_min}-{criteria.property.budget_max} Cr")
            query_log.append(f"  Type: {criteria.property.property_type}")
            query_log.append(f"  req_type: {criteria.property.req_type}")
            query_log.append(f"  Furnishing: {criteria.property.furnishing_status}")
            query_log.append(f"  Location: {criteria.property.location}")
            query_log.append(f"  Locations: {criteria.property.locations}")
            query_log.append(f"  Status: {criteria.property.property_status}")
            query_log.append(f"  Features: {criteria.property.special_features}")
            query_log.append(f"\n")

            # FILTER 1: BHK (Exact match - AND logic)
            if criteria.property.bhk:
                query = query.eq("bedroom_count", criteria.property.bhk)
                filters_applied.append(f"bedroom_count = {criteria.property.bhk}")

            # FILTER 2: Price Range with ±20% Tolerance (AND logic)
            if criteria.property.budget_min or criteria.property.budget_max:
                budget_min_rupees = (criteria.property.budget_min or 0) * 10_000_000
                budget_max_rupees = (criteria.property.budget_max or float('inf')) * 10_000_000

                price_min = budget_min_rupees * 0.8
                price_max = budget_max_rupees * 1.2

                if budget_min_rupees > 0:
                    query = query.gte("price", price_min)
                    filters_applied.append(f"price >= {price_min}")
                if budget_max_rupees != float('inf'):
                    query = query.lte("price", price_max)
                    filters_applied.append(f"price <= {price_max}")

            # FILTER 3: Property Type (Exact match - AND logic)
            if criteria.property.property_type:
                query = query.eq("property_type", criteria.property.property_type.lower())
                filters_applied.append(f"property_type = '{criteria.property.property_type.lower()}'")

            # FILTER 4: Requirement Type (Inverted match - AND logic)
            # User's req_type is what they want TO DO
            # message_type in DB is what the PROPERTY OWNER offers
            # So we need to invert: demand_buy → supply_sale, supply_rent → demand_rent, etc.
            if criteria.property.req_type:
                # Map user requirement to matching listing type
                req_type_mapping = {
                    "demand_buy": "supply_sale",      # User wants to buy → Show sale listings
                    "demand_rent": "supply_rent",    # User wants to rent → Show rental listings
                    "supply_sale": "demand_buy",     # User wants to sell → Show buyer demands
                    "supply_rent": "demand_rent"     # User wants to rent out → Show rental demands
                }
                matching_message_type = req_type_mapping.get(criteria.property.req_type, criteria.property.req_type)
                query = query.eq("message_type", matching_message_type)
                filters_applied.append(f"message_type = '{matching_message_type}'")

            # FILTER 5: Furnishing Status (Exact match - AND logic)
            if criteria.property.furnishing_status:
                query = query.eq("furnishing_status", criteria.property.furnishing_status)
                filters_applied.append(f"furnishing_status = '{criteria.property.furnishing_status}'")

            # FILTER 6: Location(s) - Fuzzy Match with OR Logic
            locations_to_search = criteria.property.locations if criteria.property.locations else (
                [criteria.property.location] if criteria.property.location else []
            )

            if locations_to_search:
                if len(locations_to_search) == 1:
                    query = query.ilike("raw_message", f"%{locations_to_search[0]}%")
                    filters_applied.append(f"raw_message ILIKE '%{locations_to_search[0]}%'")
                else:
                    or_conditions = ",".join([f'raw_message.ilike.%{loc}%' for loc in locations_to_search])
                    query = query.or_(or_conditions)

                    sql_or_parts = " OR ".join([f"raw_message ILIKE '%{loc}%'" for loc in locations_to_search])
                    filters_applied.append(f"({sql_or_parts})")

            # NOTE: Property Status is optional
            # If LLM extracted a property_status, it's informational only
            # We don't filter by it - all properties are included regardless of status
            # Future: Can be added as optional filter if user explicitly requests status matching

            # FILTER 8: Special Features - Match ANY (OR logic)
            if criteria.property.special_features:
                feature_conditions = []
                feature_sql_parts = []
                for feature in criteria.property.special_features:
                    if "bedroom" in feature.lower() and ("ground" in feature.lower() or "floor" in feature.lower()):
                        continue

                    search_term = feature.replace("_", " ").split()[0]
                    feature_conditions.append(f'raw_message.ilike.%{search_term}%')
                    feature_sql_parts.append(f"raw_message ILIKE '%{search_term}%'")

                if feature_conditions:
                    or_conditions = ",".join(feature_conditions)
                    query = query.or_(or_conditions)
                    filters_applied.append(f"({' OR '.join(feature_sql_parts)})")

            # QUERY EXECUTION
            query = query.order("message_date", desc=True).limit(limit)

            # BUILD DEBUG LOG
            query_log.append(f"\n=== VALID POSTGRESQL QUERY (Run in Supabase SQL Editor) ===")
            query_log.append(f"SELECT * FROM whatsapp_listings_relevant")

            if filters_applied:
                query_log.append(f"WHERE")
                for i, filter_str in enumerate(filters_applied):
                    prefix = "  AND " if i > 0 else "      "
                    query_log.append(f"{prefix}{filter_str}")
            else:
                query_log.append(f"-- (No filters applied - will return all records)")

            query_log.append(f"ORDER BY message_date DESC")
            query_log.append(f"LIMIT {limit};")
            query_log.append(f"=== END QUERY ===\n")

            # EXECUTE QUERY
            response = query.execute()
            raw_properties = response.data if response.data else []

            # LOG RAW RESULTS FROM SUPABASE
            query_log.append(f"\nRaw results from Supabase: {len(raw_properties)} properties")

            # Convert raw dicts to WhatsAppListingData Pydantic models
            matched_properties = []
            invalid_count = 0
            for prop_dict in raw_properties:
                try:
                    prop = WhatsAppListingData(**prop_dict)
                    matched_properties.append(prop)
                except Exception as e:
                    invalid_count += 1
                    print(f"[PropertyMatching] ⚠️  Skipping invalid property: {prop_dict.get('id')}, error: {e}")
                    continue

            # LOG RESULTS
            query_log.append(f"Valid properties after validation: {len(matched_properties)} properties")
            if invalid_count > 0:
                query_log.append(f"Skipped invalid properties: {invalid_count}")
            query_log.append(f"{'='*50}\n")

            log_file = Path(__file__).parent.parent.parent / "data" / "query_debug.log"
            with open(log_file, 'w', encoding='utf-8') as f:
                f.write("\n".join(query_log) + "\n")

            print(f"[PropertyMatching] ✓ Found {len(matched_properties)} properties (query logged to {log_file})")

            return matched_properties

        except Exception as e:
            print(f"[PropertyMatching] ✗ Error matching properties: {e}")
            return []
