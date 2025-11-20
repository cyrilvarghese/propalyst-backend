"""
Supabase Service
================

Handles connections and queries to Supabase database.
"""

import os
from typing import List, Dict, Any, Optional
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()


class SupabaseService:
    """Service for interacting with Supabase database"""

    # Shared Supabase client instance (singleton pattern)
    _client: Optional[Client] = None

    @classmethod
    def _get_client(cls) -> Client:
        """Get or create shared Supabase client instance (singleton)"""
        if cls._client is None:
            supabase_url = os.getenv("SUPABASE_URL")
            supabase_key = os.getenv("SUPABASE_KEY")

            if not supabase_url or not supabase_key:
                raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in environment")

            cls._client = create_client(supabase_url, supabase_key)
            print("[Supabase] ✓ Created shared Supabase client instance")

        return cls._client

    @classmethod
    async def get_all_listings(cls, limit: int = 100, offset: int = 0) -> Dict[str, Any]:
        """
        Get all CREA WhatsApp listings with pagination

        Args:
            limit: Maximum number of records to return (default: 100)
            offset: Number of records to skip (default: 0)

        Returns:
            Dictionary with success status and listings data
        """
        try:
            client = cls._get_client()

            response = client.table("crea_wapp")\
                .select("*")\
                .order("message_date", desc=True)\
                .limit(limit)\
                .offset(offset)\
                .execute()

            listings = response.data if response.data else []

            print(f"[Supabase] ✓ Retrieved {len(listings)} listings (limit: {limit}, offset: {offset})")

            return {
                "success": True,
                "data": listings,
                "count": len(listings),
                "message": f"Retrieved {len(listings)} listings"
            }

        except Exception as e:
            print(f"[Supabase] ✗ Error retrieving listings: {e}")
            return {
                "success": False,
                "data": [],
                "count": 0,
                "message": f"Error retrieving listings: {str(e)}"
            }

    @classmethod
    async def get_listing_by_id(cls, listing_id: str) -> Dict[str, Any]:
        """
        Get a specific listing by ID

        Args:
            listing_id: UUID of the listing

        Returns:
            Dictionary with success status and listing data
        """
        try:
            client = cls._get_client()

            response = client.table("crea_wapp")\
                .select("*")\
                .eq("id", listing_id)\
                .execute()

            if response.data and len(response.data) > 0:
                listing = response.data[0]
                print(f"[Supabase] ✓ Found listing with ID: {listing_id}")
                return {
                    "success": True,
                    "data": listing,
                    "message": "Listing found"
                }
            else:
                print(f"[Supabase] ✗ Listing not found: {listing_id}")
                return {
                    "success": False,
                    "data": None,
                    "message": f"Listing with ID {listing_id} not found"
                }

        except Exception as e:
            print(f"[Supabase] ✗ Error retrieving listing: {e}")
            return {
                "success": False,
                "data": None,
                "message": f"Error retrieving listing: {str(e)}"
            }

    @classmethod
    async def search_listings(
        cls,
        agent_name: Optional[str] = None,
        location: Optional[str] = None,
        property_type: Optional[str] = None,
        configuration: Optional[str] = None,
        transaction_type: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        limit: int = 100
    ) -> Dict[str, Any]:
        """
        Search listings with filters

        Args:
            agent_name: Filter by agent name or company name (partial match)
            location: Filter by location (partial match)
            property_type: Filter by property type
            configuration: Filter by BHK configuration
            transaction_type: Filter by transaction type (Sale, Rent, etc.)
            min_price: Minimum price filter
            max_price: Maximum price filter
            limit: Maximum number of results

        Returns:
            Dictionary with success status and filtered listings
        """
        try:
            client = cls._get_client()

            # Start with base query
            query = client.table("crea_wapp").select("*")

            # Apply filters
            if agent_name:
                # Search in both agent_name and company_name fields
                query = query.or_(f"agent_name.ilike.%{agent_name}%,company_name.ilike.%{agent_name}%")

            if location:
                query = query.ilike("location", f"%{location}%")

            if property_type:
                query = query.eq("property_type", property_type)

            if configuration:
                query = query.eq("configuration", configuration)

            if transaction_type:
                query = query.eq("transaction_type", transaction_type)

            if min_price is not None:
                query = query.gte("price", min_price)

            if max_price is not None:
                query = query.lte("price", max_price)

            # Execute query
            response = query.order("message_date", desc=True).limit(limit).execute()

            listings = response.data if response.data else []

            print(f"[Supabase] ✓ Search returned {len(listings)} listings")

            return {
                "success": True,
                "data": listings,
                "count": len(listings),
                "message": f"Found {len(listings)} matching listings"
            }

        except Exception as e:
            print(f"[Supabase] ✗ Error searching listings: {e}")
            return {
                "success": False,
                "data": [],
                "count": 0,
                "message": f"Error searching listings: {str(e)}"
            }

    @classmethod
    async def search_raw_message(cls, query: str, limit: int = 100) -> Dict[str, Any]:
        """
        Search listings by raw message content (full-text search)

        Args:
            query: Search text to find in raw messages (case-insensitive)
            limit: Maximum number of results (default: 100)

        Returns:
            Dictionary with success status and matching listings
        """
        try:
            client = cls._get_client()

            # Search in raw_message field using ILIKE for case-insensitive partial match
            response = client.table("crea_wapp")\
                .select("*")\
                .ilike("raw_message", f"%{query}%")\
                .order("message_date", desc=True)\
                .limit(limit)\
                .execute()

            listings = response.data if response.data else []

            print(f"[Supabase] ✓ Raw message search for '{query}' returned {len(listings)} listings")

            return {
                "success": True,
                "data": listings,
                "count": len(listings),
                "message": f"Found {len(listings)} listings containing '{query}'"
            }

        except Exception as e:
            print(f"[Supabase] ✗ Error searching raw messages: {e}")
            return {
                "success": False,
                "data": [],
                "count": 0,
                "message": f"Error searching raw messages: {str(e)}"
            }

    @classmethod
    async def fuzzy_search_location(cls, location: str, limit: int = 100, similarity_threshold: float = 0.3) -> Dict[str, Any]:
        """
        Fuzzy search for location names using UNION of multiple search strategies

        Combines results from:
        1. Exact matches (location or raw_message contains the search term)
        2. Fuzzy similarity matches (handles typos like Sarjapura → Sarajapur)

        Results are merged, deduplicated, and sorted by relevance:
        - Exact matches appear first (score = 1.0)
        - Fuzzy matches follow (score = similarity_threshold to 1.0)

        Args:
            location: Location name to search for
            limit: Maximum number of results (default: 100)
            similarity_threshold: Minimum similarity score 0-1 (default: 0.3, lower = more lenient)

        Returns:
            Dictionary with success status and union of all matching listings
        """
        try:
            client = cls._get_client()
            from difflib import SequenceMatcher

            def similarity(a: str, b: str) -> float:
                """Calculate similarity between two strings (0-1)"""
                if not a or not b:
                    return 0.0
                return SequenceMatcher(None, a.lower(), b.lower()).ratio()

            # ========== STRATEGY 1: Exact ILIKE matches ==========
            print(f"[Supabase] Strategy 1: Exact ILIKE search for '{location}'...")
            exact_response = client.table("crea_wapp")\
                .select("*")\
                .or_(f"location.ilike.%{location}%,raw_message.ilike.%{location}%")\
                .order("message_date", desc=True)\
                .limit(limit * 2)\
                .execute()

            exact_listings = exact_response.data if exact_response.data else []
            print(f"[Supabase] ✓ Strategy 1 returned {len(exact_listings)} exact matches")

            # Store exact matches with score 1.0 (highest priority)
            results_map = {}
            for listing in exact_listings:
                results_map[listing['id']] = {
                    'listing': listing,
                    'score': 1.0,
                    'match_type': 'exact'
                }

            # ========== STRATEGY 2: Fuzzy similarity matching ==========
            print(f"[Supabase] Strategy 2: Fuzzy similarity search...")

            # Get broader set of listings for fuzzy matching
            all_response = client.table("crea_wapp")\
                .select("*")\
                .order("message_date", desc=True)\
                .limit(1000)\
                .execute()

            all_listings = all_response.data if all_response.data else []

            fuzzy_count = 0
            for listing in all_listings:
                listing_id = listing['id']

                # Skip if already found as exact match
                if listing_id in results_map:
                    continue

                best_score = 0.0

                # Check location field
                if listing.get('location'):
                    loc_similarity = similarity(location, listing['location'])
                    best_score = max(best_score, loc_similarity)

                # Check raw_message for location mentions
                # (Kept for location search since locations often appear in free text)
                if listing.get('raw_message'):
                    words = listing['raw_message'].split()
                    for word in words:
                        word_clean = ''.join(c for c in word if c.isalnum())
                        if len(word_clean) >= 4:  # Only check words with 4+ chars
                            word_similarity = similarity(location, word_clean)
                            best_score = max(best_score, word_similarity)

                # Add to results if meets threshold
                if best_score >= similarity_threshold:
                    results_map[listing_id] = {
                        'listing': listing,
                        'score': best_score,
                        'match_type': 'fuzzy'
                    }
                    fuzzy_count += 1

            print(f"[Supabase] ✓ Strategy 2 returned {fuzzy_count} fuzzy matches")

            # ========== UNION: Combine and sort results ==========
            # Sort by score (exact matches first, then by similarity)
            sorted_results = sorted(
                results_map.values(),
                key=lambda x: x['score'],
                reverse=True
            )

            # Extract listings up to limit
            final_listings = [r['listing'] for r in sorted_results[:limit]]

            total_count = len(final_listings)
            exact_count = sum(1 for r in sorted_results[:limit] if r['match_type'] == 'exact')
            fuzzy_count_final = total_count - exact_count

            print(f"[Supabase] ✓ UNION result: {total_count} total ({exact_count} exact + {fuzzy_count_final} fuzzy)")

            return {
                "success": True,
                "data": final_listings,
                "count": total_count,
                "message": f"Found {total_count} listings for '{location}' ({exact_count} exact, {fuzzy_count_final} fuzzy)",
                "metadata": {
                    "exact_matches": exact_count,
                    "fuzzy_matches": fuzzy_count_final,
                    "search_strategy": "union"
                }
            }

        except Exception as e:
            print(f"[Supabase] ✗ Error in fuzzy location search: {e}")
            return {
                "success": False,
                "data": [],
                "count": 0,
                "message": f"Error in fuzzy search: {str(e)}"
            }

    @classmethod
    async def fuzzy_search_agent_name(cls, agent_name: str, limit: int = 100, similarity_threshold: float = 0.3) -> Dict[str, Any]:
        """
        Fuzzy search for agent names using UNION of multiple search strategies

        Combines results from:
        1. Exact matches (agent_name or raw_message contains the search term)
        2. Fuzzy similarity matches (handles typos and name variations)

        Results are merged, deduplicated, and sorted by relevance:
        - Exact matches appear first (score = 1.0)
        - Fuzzy matches follow (score = similarity_threshold to 1.0)

        Args:
            agent_name: Agent name to search for
            limit: Maximum number of results (default: 100)
            similarity_threshold: Minimum similarity score 0-1 (default: 0.3, lower = more lenient)

        Returns:
            Dictionary with success status and union of all matching listings
        """
        try:
            client = cls._get_client()
            from difflib import SequenceMatcher

            def similarity(a: str, b: str) -> float:
                """Calculate similarity between two strings (0-1)"""
                if not a or not b:
                    return 0.0
                return SequenceMatcher(None, a.lower(), b.lower()).ratio()

            # ========== STRATEGY 1: Exact ILIKE matches ==========
            print(f"[Supabase] Strategy 1: Exact ILIKE search for agent '{agent_name}'...")
            exact_response = client.table("crea_wapp")\
                .select("*")\
                .or_(f"agent_name.ilike.%{agent_name}%,raw_message.ilike.%{agent_name}%")\
                .order("message_date", desc=True)\
                .limit(limit * 2)\
                .execute()

            exact_listings = exact_response.data if exact_response.data else []
            print(f"[Supabase] ✓ Strategy 1 returned {len(exact_listings)} exact matches")

            # Store exact matches with score 1.0 (highest priority)
            results_map = {}
            for listing in exact_listings:
                results_map[listing['id']] = {
                    'listing': listing,
                    'score': 1.0,
                    'match_type': 'exact'
                }

            # ========== STRATEGY 2: Fuzzy similarity matching ==========
            print(f"[Supabase] Strategy 2: Fuzzy similarity search...")

            # Get broader set of listings for fuzzy matching
            all_response = client.table("crea_wapp")\
                .select("*")\
                .order("message_date", desc=True)\
                .limit(1000)\
                .execute()

            all_listings = all_response.data if all_response.data else []

            fuzzy_count = 0
            for listing in all_listings:
                listing_id = listing['id']

                # Skip if already found as exact match
                if listing_id in results_map:
                    continue

                best_score = 0.0

                # Check agent_name field
                if listing.get('agent_name'):
                    agent_similarity = similarity(agent_name, listing['agent_name'])
                    best_score = max(best_score, agent_similarity)

                # Check company_name field
                if listing.get('company_name'):
                    company_similarity = similarity(agent_name, listing['company_name'])
                    best_score = max(best_score, company_similarity)

                # Note: raw_message removed from fuzzy matching for performance
                # (still searched in Strategy 1 via database ILIKE)

                # Add to results if meets threshold
                if best_score >= similarity_threshold:
                    results_map[listing_id] = {
                        'listing': listing,
                        'score': best_score,
                        'match_type': 'fuzzy'
                    }
                    fuzzy_count += 1

            print(f"[Supabase] ✓ Strategy 2 returned {fuzzy_count} fuzzy matches")

            # ========== UNION: Combine and sort results ==========
            sorted_results = sorted(
                results_map.values(),
                key=lambda x: x['score'],
                reverse=True
            )

            # Extract listings up to limit
            final_listings = [r['listing'] for r in sorted_results[:limit]]

            total_count = len(final_listings)
            exact_count = sum(1 for r in sorted_results[:limit] if r['match_type'] == 'exact')
            fuzzy_count_final = total_count - exact_count

            print(f"[Supabase] ✓ UNION result: {total_count} total ({exact_count} exact + {fuzzy_count_final} fuzzy)")

            return {
                "success": True,
                "data": final_listings,
                "count": total_count,
                "message": f"Found {total_count} listings for agent '{agent_name}' ({exact_count} exact, {fuzzy_count_final} fuzzy)",
                "metadata": {
                    "exact_matches": exact_count,
                    "fuzzy_matches": fuzzy_count_final,
                    "search_strategy": "union"
                }
            }

        except Exception as e:
            print(f"[Supabase] ✗ Error in fuzzy agent search: {e}")
            return {
                "success": False,
                "data": [],
                "count": 0,
                "message": f"Error in fuzzy agent search: {str(e)}"
            }

    @classmethod
    async def fuzzy_search_property(cls, property_query: str, limit: int = 100, similarity_threshold: float = 0.3) -> Dict[str, Any]:
        """
        Fuzzy search for properties using UNION of multiple search strategies

        Searches across property_type, configuration, and raw_message fields.
        Handles variations like "3BHK", "3 BHK", "three bhk", etc.

        Combines results from:
        1. Exact matches (property fields or raw_message contains the search term)
        2. Fuzzy similarity matches (handles typos and variations)

        Results are merged, deduplicated, and sorted by relevance:
        - Exact matches appear first (score = 1.0)
        - Fuzzy matches follow (score = similarity_threshold to 1.0)

        Args:
            property_query: Property search term (e.g., "3BHK", "Villa", "Apartment")
            limit: Maximum number of results (default: 100)
            similarity_threshold: Minimum similarity score 0-1 (default: 0.3, lower = more lenient)

        Returns:
            Dictionary with success status and union of all matching listings
        """
        try:
            client = cls._get_client()
            from difflib import SequenceMatcher

            def similarity(a: str, b: str) -> float:
                """Calculate similarity between two strings (0-1)"""
                if not a or not b:
                    return 0.0
                return SequenceMatcher(None, a.lower(), b.lower()).ratio()

            # ========== STRATEGY 1: Exact ILIKE matches ==========
            print(f"[Supabase] Strategy 1: Exact ILIKE search for property '{property_query}'...")
            exact_response = client.table("crea_wapp")\
                .select("*")\
                .or_(f"property_type.ilike.%{property_query}%,configuration.ilike.%{property_query}%,raw_message.ilike.%{property_query}%")\
                .order("message_date", desc=True)\
                .limit(limit * 2)\
                .execute()

            exact_listings = exact_response.data if exact_response.data else []
            print(f"[Supabase] ✓ Strategy 1 returned {len(exact_listings)} exact matches")

            # Store exact matches with score 1.0 (highest priority)
            results_map = {}
            for listing in exact_listings:
                results_map[listing['id']] = {
                    'listing': listing,
                    'score': 1.0,
                    'match_type': 'exact'
                }

            # ========== STRATEGY 2: Fuzzy similarity matching ==========
            print(f"[Supabase] Strategy 2: Fuzzy similarity search...")

            # Get broader set of listings for fuzzy matching
            all_response = client.table("crea_wapp")\
                .select("*")\
                .order("message_date", desc=True)\
                .limit(1000)\
                .execute()

            all_listings = all_response.data if all_response.data else []

            fuzzy_count = 0
            for listing in all_listings:
                listing_id = listing['id']

                # Skip if already found as exact match
                if listing_id in results_map:
                    continue

                best_score = 0.0

                # Check property_type field
                if listing.get('property_type'):
                    type_similarity = similarity(property_query, listing['property_type'])
                    best_score = max(best_score, type_similarity)

                # Check configuration field
                if listing.get('configuration'):
                    config_similarity = similarity(property_query, listing['configuration'])
                    best_score = max(best_score, config_similarity)

                # Check project_name field
                if listing.get('project_name'):
                    project_similarity = similarity(property_query, listing['project_name'])
                    best_score = max(best_score, project_similarity)

                # Note: raw_message removed from fuzzy matching for performance
                # (still searched in Strategy 1 via database ILIKE)

                # Add to results if meets threshold
                if best_score >= similarity_threshold:
                    results_map[listing_id] = {
                        'listing': listing,
                        'score': best_score,
                        'match_type': 'fuzzy'
                    }
                    fuzzy_count += 1

            print(f"[Supabase] ✓ Strategy 2 returned {fuzzy_count} fuzzy matches")

            # ========== UNION: Combine and sort results ==========
            sorted_results = sorted(
                results_map.values(),
                key=lambda x: x['score'],
                reverse=True
            )

            # Extract listings up to limit
            final_listings = [r['listing'] for r in sorted_results[:limit]]

            total_count = len(final_listings)
            exact_count = sum(1 for r in sorted_results[:limit] if r['match_type'] == 'exact')
            fuzzy_count_final = total_count - exact_count

            print(f"[Supabase] ✓ UNION result: {total_count} total ({exact_count} exact + {fuzzy_count_final} fuzzy)")

            return {
                "success": True,
                "data": final_listings,
                "count": total_count,
                "message": f"Found {total_count} listings for property '{property_query}' ({exact_count} exact, {fuzzy_count_final} fuzzy)",
                "metadata": {
                    "exact_matches": exact_count,
                    "fuzzy_matches": fuzzy_count_final,
                    "search_strategy": "union"
                }
            }

        except Exception as e:
            print(f"[Supabase] ✗ Error in fuzzy property search: {e}")
            return {
                "success": False,
                "data": [],
                "count": 0,
                "message": f"Error in fuzzy property search: {str(e)}"
            }

    @classmethod
    async def unified_search(
        cls,
        agent_name: Optional[str] = None,
        property_query: Optional[str] = None,
        location: Optional[str] = None,
        limit: int = 100,
        similarity_threshold: float = 0.3
    ) -> Dict[str, Any]:
        """
        Unified search across agent, property, and location with AND logic

        Uses HYBRID STRATEGY for optimal performance:
        1. Database-level exact matching (fast, uses indexes)
        2. Client-side fuzzy matching with set intersection (comprehensive)
        3. Union of results (deduplicated, sorted by relevance)

        Args:
            agent_name: Agent or company name filter
            property_query: Property type, configuration, or project filter
            location: Location name filter
            limit: Maximum results
            similarity_threshold: Fuzzy match threshold (0-1)

        Returns:
            Dictionary with success status and matched listings

        Example:
            # All 3 filters (AND condition)
            unified_search(agent_name="Tajamul", property_query="3BHK", location="Indiranagar")

            # 2 filters
            unified_search(property_query="Villa", location="Whitefield")

            # 1 filter
            unified_search(location="Koramangala")
        """
        try:
            from difflib import SequenceMatcher

            # Count active filters
            active_filters = sum([
                agent_name is not None,
                property_query is not None,
                location is not None
            ])

            if active_filters == 0:
                return {
                    "success": False,
                    "data": [],
                    "count": 0,
                    "message": "At least one search parameter is required"
                }

            print(f"[Supabase] Unified search with {active_filters} filter(s)")

            # ========== STRATEGY 1: Exact Database Matching (AND) ==========
            print(f"[Supabase] Strategy 1: Database-level exact matching...")

            client = cls._get_client()
            query = client.table("crea_wapp").select("*")

            # Build AND conditions for exact matches
            or_conditions = []
            if agent_name:
                or_conditions.append(f"agent_name.ilike.%{agent_name}%")
                or_conditions.append(f"company_name.ilike.%{agent_name}%")

            if property_query:
                or_conditions.append(f"property_type.ilike.%{property_query}%")
                or_conditions.append(f"configuration.ilike.%{property_query}%")
                or_conditions.append(f"project_name.ilike.%{property_query}%")

            if location:
                or_conditions.append(f"location.ilike.%{location}%")

            # Execute exact search
            if or_conditions:
                query = query.or_(",".join(or_conditions))

            exact_response = query.order("message_date", desc=True).limit(limit * 2).execute()
            exact_listings = exact_response.data if exact_response.data else []

            # Filter exact results for AND condition (client-side)
            filtered_exact = []
            for listing in exact_listings:
                matches = True

                if agent_name:
                    agent_match = (
                        (listing.get('agent_name') and agent_name.lower() in listing['agent_name'].lower()) or
                        (listing.get('company_name') and agent_name.lower() in listing['company_name'].lower())
                    )
                    matches = matches and agent_match

                if property_query:
                    property_match = (
                        (listing.get('property_type') and property_query.lower() in listing['property_type'].lower()) or
                        (listing.get('configuration') and property_query.lower() in listing['configuration'].lower()) or
                        (listing.get('project_name') and property_query.lower() in listing['project_name'].lower())
                    )
                    matches = matches and property_match

                if location:
                    location_match = listing.get('location') and location.lower() in listing['location'].lower()
                    matches = matches and location_match

                if matches:
                    filtered_exact.append(listing)

            print(f"[Supabase] ✓ Strategy 1 returned {len(filtered_exact)} exact matches (AND filtered)")

            results_map = {}
            for listing in filtered_exact:
                results_map[listing['id']] = {
                    'listing': listing,
                    'score': 1.0,
                    'match_type': 'exact'
                }

            # ========== STRATEGY 2: Fuzzy Matching with Intersection ==========
            # Only run fuzzy search if we have fewer than threshold results
            if len(filtered_exact) < limit:
                print(f"[Supabase] Strategy 2: Fuzzy matching with set intersection...")

                def similarity(a: str, b: str) -> float:
                    if not a or not b:
                        return 0.0
                    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

                # Get all listings for fuzzy matching
                all_response = client.table("crea_wapp")\
                    .select("*")\
                    .order("message_date", desc=True)\
                    .limit(1000)\
                    .execute()

                all_listings = all_response.data if all_response.data else []

                # Fuzzy match each filter separately
                agent_matches = set()
                property_matches = set()
                location_matches = set()

                for listing in all_listings:
                    listing_id = listing['id']

                    # Skip if already exact match
                    if listing_id in results_map:
                        continue

                    # Agent fuzzy matching
                    if agent_name:
                        agent_score = 0.0
                        if listing.get('agent_name'):
                            agent_score = max(agent_score, similarity(agent_name, listing['agent_name']))
                        if listing.get('company_name'):
                            agent_score = max(agent_score, similarity(agent_name, listing['company_name']))

                        if agent_score >= similarity_threshold:
                            agent_matches.add(listing_id)

                    # Property fuzzy matching
                    if property_query:
                        property_score = 0.0
                        if listing.get('property_type'):
                            property_score = max(property_score, similarity(property_query, listing['property_type']))
                        if listing.get('configuration'):
                            property_score = max(property_score, similarity(property_query, listing['configuration']))
                        if listing.get('project_name'):
                            property_score = max(property_score, similarity(property_query, listing['project_name']))

                        if property_score >= similarity_threshold:
                            property_matches.add(listing_id)

                    # Location fuzzy matching
                    if location:
                        location_score = 0.0
                        if listing.get('location'):
                            location_score = similarity(location, listing['location'])

                        if location_score >= similarity_threshold:
                            location_matches.add(listing_id)

                # SET INTERSECTION (AND logic)
                # Start with all listings, then intersect with each active filter
                fuzzy_intersection = set(listing['id'] for listing in all_listings)

                if agent_name:
                    fuzzy_intersection = fuzzy_intersection & agent_matches
                if property_query:
                    fuzzy_intersection = fuzzy_intersection & property_matches
                if location:
                    fuzzy_intersection = fuzzy_intersection & location_matches

                # Add fuzzy matches to results
                fuzzy_count = 0
                for listing in all_listings:
                    if listing['id'] in fuzzy_intersection and listing['id'] not in results_map:
                        # Calculate combined score
                        combined_score = 0.0
                        score_count = 0

                        if agent_name and listing['id'] in agent_matches:
                            score_count += 1
                            # Recalculate score for this listing
                            if listing.get('agent_name'):
                                combined_score += similarity(agent_name, listing['agent_name'])
                            if listing.get('company_name'):
                                combined_score += similarity(agent_name, listing['company_name'])

                        if property_query and listing['id'] in property_matches:
                            score_count += 1

                        if location and listing['id'] in location_matches:
                            score_count += 1

                        avg_score = combined_score / max(score_count, 1) if score_count > 0 else similarity_threshold

                        results_map[listing['id']] = {
                            'listing': listing,
                            'score': avg_score,
                            'match_type': 'fuzzy'
                        }
                        fuzzy_count += 1

                print(f"[Supabase] ✓ Strategy 2 returned {fuzzy_count} fuzzy matches (AND intersection)")

            # ========== UNION: Combine and sort results ==========
            sorted_results = sorted(
                results_map.values(),
                key=lambda x: x['score'],
                reverse=True
            )

            final_listings = [r['listing'] for r in sorted_results[:limit]]

            total_count = len(final_listings)
            exact_count = sum(1 for r in sorted_results[:limit] if r['match_type'] == 'exact')
            fuzzy_count = total_count - exact_count

            # Build filter summary
            filters_used = []
            if agent_name:
                filters_used.append(f"agent='{agent_name}'")
            if property_query:
                filters_used.append(f"property='{property_query}'")
            if location:
                filters_used.append(f"location='{location}'")

            filter_summary = " AND ".join(filters_used)

            print(f"[Supabase] ✓ UNION result: {total_count} total ({exact_count} exact + {fuzzy_count} fuzzy)")

            return {
                "success": True,
                "data": final_listings,
                "count": total_count,
                "message": f"Found {total_count} listings matching {filter_summary}",
                "metadata": {
                    "filters_applied": {
                        "agent_name": agent_name,
                        "property_query": property_query,
                        "location": location
                    },
                    "exact_matches": exact_count,
                    "fuzzy_matches": fuzzy_count,
                    "search_strategy": "hybrid_intersection"
                }
            }

        except Exception as e:
            print(f"[Supabase] ✗ Error in unified search: {e}")
            return {
                "success": False,
                "data": [],
                "count": 0,
                "message": f"Error in unified search: {str(e)}"
            }
