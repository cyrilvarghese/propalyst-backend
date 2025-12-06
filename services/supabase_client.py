"""
Shared Supabase Client
======================

Singleton pattern for Supabase client instance.
Used by all domain-specific services (Properties, WhatsApp, Agents, etc.)

Purpose:
    - Single Supabase client instance shared across all services
    - Avoids creating multiple connections
    - Centralized configuration and error handling

Usage:
    from services.supabase_client import get_supabase_client

    class YourService:
        @classmethod
        async def your_method(cls):
            client = get_supabase_client()
            response = client.table("your_table").select("*").execute()
"""

import os
from typing import Optional
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

# Module-level singleton instance
_client: Optional[Client] = None


def get_supabase_client() -> Client:
    """
    Get or create shared Supabase client instance (singleton pattern)

    Creates client on first call, returns cached instance on subsequent calls.
    Thread-safe for async operations.

    Returns:
        Supabase Client instance

    Raises:
        ValueError: If SUPABASE_URL or SUPABASE_KEY environment variables not set

    Example:
        client = get_supabase_client()
        response = client.table("properties").select("*").execute()
    """
    global _client

    if _client is None:
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")

        if not supabase_url or not supabase_key:
            raise ValueError(
                "SUPABASE_URL and SUPABASE_KEY must be set in environment variables. "
                "Check your .env file."
            )

        _client = create_client(supabase_url, supabase_key)
        print("[SupabaseClient] ✓ Created shared Supabase client instance")

    return _client


def reset_client() -> None:
    """
    Reset the singleton client instance (useful for testing)

    Warning: Only use this for testing purposes or when you need to
    recreate the client with different credentials.
    """
    global _client
    _client = None
    print("[SupabaseClient] ⚠ Reset client instance")
