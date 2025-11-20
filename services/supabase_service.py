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
                if listing.get('raw_message'):
                    words = listing['raw_message'].split()
                    for word in words:
                        word_clean = ''.join(c for c in word if c.isalnum())
                        if len(word_clean) >= 4:
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
