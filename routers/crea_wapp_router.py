"""
CREA WhatsApp Listings Router
==============================

API endpoints for querying CREA WhatsApp listings from Supabase.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from models.crea_wapp import CreaWappResponse, MessageFormatRequest, MessageFormatResponse
from services.supabase_service import SupabaseService
from services.message_formatting_service import MessageFormattingService

router = APIRouter(
    prefix="/api/crea",
    tags=["CREA WhatsApp Listings"]
)


@router.get("/listings", response_model=CreaWappResponse)
async def get_all_listings(
    limit: int = Query(100, description="Maximum number of records to return"),
    offset: int = Query(0, description="Number of records to skip for pagination")
):
    """
    Get all CREA WhatsApp listings with pagination

    Args:
        limit: Maximum number of records (default: 100, max: 1000)
        offset: Number of records to skip (default: 0)

    Returns:
        CreaWappResponse with list of listings

    Example:
        GET /api/crea/listings?limit=50&offset=0
    """
    try:
        print(f"[API-CREA] Retrieving listings (limit: {limit}, offset: {offset})")

        # Validate limit
        if limit > 1000:
            limit = 1000

        result = await SupabaseService.get_all_listings(limit=limit, offset=offset)
        return result

    except Exception as e:
        print(f"[API-CREA] ✗ Error retrieving listings: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving listings: {str(e)}")


@router.get("/listings/search", response_model=CreaWappResponse)
async def search_listings(
    agent_name: Optional[str] = Query(None, description="Filter by agent name or company (partial match)"),
    location: Optional[str] = Query(None, description="Filter by location (partial match)"),
    property_type: Optional[str] = Query(None, description="Filter by property type"),
    configuration: Optional[str] = Query(None, description="Filter by BHK configuration"),
    listing_type: Optional[str] = Query(None, description="Filter by listing type (Sale, Rent, Requirement)"),
    transaction_type: Optional[str] = Query(None, description="Filter by transaction type (Sale, Rent, etc.)"),
    min_price: Optional[float] = Query(None, description="Minimum price filter"),
    max_price: Optional[float] = Query(None, description="Maximum price filter"),
    limit: int = Query(100, description="Maximum number of results")
):
    """
    Search listings with filters (exact match, no fuzzy)

    Query parameters allow filtering by multiple criteria with AND logic.

    Args:
        agent_name: Agent or company name (partial match, e.g., 'Tajamul', 'TREND SHELTERS')
        location: Property location (supports partial matching, e.g., 'Indiranagar')
        property_type: Property type (e.g., 'Apartment', 'Villa', 'Plot')
        configuration: BHK configuration (e.g., '3 BHK', '4 BHK')
        listing_type: Listing type (e.g., 'Sale', 'Rent', 'Requirement')
        transaction_type: Transaction type (e.g., 'Sale', 'Rent')
        min_price: Minimum price in numeric format
        max_price: Maximum price in numeric format
        limit: Maximum results to return

    Returns:
        CreaWappResponse with filtered listings

    Examples:
        # Search by agent
        GET /api/crea/listings/search?agent_name=Tajamul

        # With listing type
        GET /api/crea/listings/search?listing_type=Rent&location=Indiranagar

        # Multiple filters (AND condition)
        GET /api/crea/listings/search?agent_name=TREND%20SHELTERS&location=Indiranagar&configuration=3%20BHK&listing_type=Sale

        # With price range
        GET /api/crea/listings/search?location=Indiranagar&listing_type=Sale&min_price=5000000&max_price=10000000
    """
    try:
        print(f"[API-CREA] Searching listings with filters:")
        print(f"[API-CREA] - agent_name: {agent_name}")
        print(f"[API-CREA] - location: {location}")
        print(f"[API-CREA] - property_type: {property_type}")
        print(f"[API-CREA] - configuration: {configuration}")
        print(f"[API-CREA] - listing_type: {listing_type}")
        print(f"[API-CREA] - transaction_type: {transaction_type}")
        print(f"[API-CREA] - price range: {min_price} - {max_price}")

        result = await SupabaseService.search_listings(
            agent_name=agent_name,
            location=location,
            property_type=property_type,
            configuration=configuration,
            listing_type=listing_type,
            transaction_type=transaction_type,
            min_price=min_price,
            max_price=max_price,
            limit=limit
        )

        return result

    except Exception as e:
        print(f"[API-CREA] ✗ Error searching listings: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error searching listings: {str(e)}")


@router.get("/listings/search/message", response_model=CreaWappResponse)
async def search_raw_message(
    query: str = Query(..., description="Search text to find in raw messages"),
    limit: int = Query(100, description="Maximum number of results")
):
    """
    Search listings by raw message content (full-text search)

    Searches for the query string within the raw_message field.
    Useful for finding specific keywords, agent names, or property details.

    Args:
        query: Search text to find in messages (case-insensitive)
        limit: Maximum number of results (default: 100)

    Returns:
        CreaWappResponse with matching listings

    Examples:
        # Find all messages mentioning "Indiranagar"
        GET /api/crea/listings/search/message?query=Indiranagar

        # Find messages about "3 BHK"
        GET /api/crea/listings/search/message?query=3%20BHK

        # Find specific agent messages
        GET /api/crea/listings/search/message?query=Porchlight%20Realty
    """
    try:
        print(f"[API-CREA] Searching raw messages for: '{query}'")

        result = await SupabaseService.search_raw_message(query=query, limit=limit)
        return result

    except Exception as e:
        print(f"[API-CREA] ✗ Error searching raw messages: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error searching raw messages: {str(e)}")


@router.get("/listings/search/location", response_model=CreaWappResponse)
async def fuzzy_search_location(
    location: str = Query(..., description="Location name to search (handles typos and variations)"),
    limit: int = Query(100, description="Maximum number of results")
):
    """
    Fuzzy search for properties by location (typo-tolerant)

    Handles common spelling variations and typos in location names.
    For example, searching for "Sarjapura" will also return results for "Sarajapur" and "Sarjapur".

    Args:
        location: Location name (e.g., "Sarjapura", "Indiranagar")
        limit: Maximum number of results (default: 100)

    Returns:
        CreaWappResponse with matching listings

    Examples:
        # Search for Sarjapura (also matches Sarajapur, Sarjapur)
        GET /api/crea/listings/search/location?location=Sarjapura

        # Search for Indiranagar (also matches Indira Nagar, Indranagar)
        GET /api/crea/listings/search/location?location=Indiranagar

        # Search for Whitefield (also matches White Field)
        GET /api/crea/listings/search/location?location=Whitefield
    """
    try:
        print(f"[API-CREA] Fuzzy searching location: '{location}'")

        result = await SupabaseService.fuzzy_search_location(location=location, limit=limit)
        return result

    except Exception as e:
        print(f"[API-CREA] ✗ Error in fuzzy location search: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error in fuzzy location search: {str(e)}")


@router.get("/listings/{listing_id}", response_model=CreaWappResponse)
async def get_listing_by_id(listing_id: str):
    """
    Get a specific listing by ID

    IMPORTANT: This route must be defined AFTER all /listings/search/* routes
    to avoid FastAPI matching "search" as a listing_id parameter.

    Args:
        listing_id: UUID of the listing

    Returns:
        CreaWappResponse with single listing data

    Example:
        GET /api/crea/listings/550e8400-e29b-41d4-a716-446655440000
    """
    try:
        print(f"[API-CREA] Retrieving listing: {listing_id}")

        result = await SupabaseService.get_listing_by_id(listing_id)

        if not result["success"]:
            raise HTTPException(status_code=404, detail=result["message"])

        # Wrap single listing in array for consistent response format
        return {
            "success": True,
            "data": [result["data"]] if result["data"] else [],
            "count": 1 if result["data"] else 0,
            "message": result["message"]
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[API-CREA] ✗ Error retrieving listing: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving listing: {str(e)}")


@router.post("/get-whatsapp-message", response_model=MessageFormatResponse)
async def format_broker_message(request: MessageFormatRequest):
    """
    Format a raw property listing into a friendly WhatsApp outreach message

    Takes a broker's property listing and generates a professional message expressing
    interest on behalf of your client. Perfect for reaching out to brokers with matching properties.

    Args:
        request: MessageFormatRequest containing:
            - raw_message: The broker's property listing (required)
            - agent_name: Name of the broker to address in greeting (default: "Naresh")
            - tone: Message tone - "professional_friendly", "casual", or "formal" (default: "professional_friendly")
            - include_emojis: Whether to include emojis (default: true)

    Returns:
        MessageFormatResponse with formatted WhatsApp message

    Example:
        POST /api/crea/format-message
        {
            "raw_message": "*Apartment for Rent!!!!!!*\\n🏢 Project Name : built by...",
            "agent_name": "Tajamul",
            "tone": "professional_friendly",
            "include_emojis": true
        }

        Response:
        {
            "success": true,
            "formatted_message": "Hi Tajamul! 👋\\n\\nI came across your 4 BHK apartment...",
            "original_message": "...",
            "message": "Message formatted successfully"
        }
    """
    try:
        print(f"[API-CREA] Formatting message (tone: {request.tone}, emojis: {request.include_emojis})")

        # Format the message using Gemini LLM
        formatted_text = await MessageFormattingService.format_message(
            raw_message=request.raw_message,
            agent_name=request.agent_name,
            tone=request.tone,
            include_emojis=request.include_emojis
        )

        print(f"[API-CREA] ✓ Message formatted successfully")

        return MessageFormatResponse(
            success=True,
            formatted_message=formatted_text,
            original_message=request.raw_message,
            message="Message formatted successfully"
        )

    except Exception as e:
        print(f"[API-CREA] ✗ Error formatting message: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error formatting message: {str(e)}")


@router.get("/listings/search/agent", response_model=CreaWappResponse)
async def fuzzy_search_agent(
    agent_name: str = Query(..., description="Agent name to search (handles typos and variations)"),
    limit: int = Query(100, description="Maximum number of results")
):
    """
    Fuzzy search for properties by agent name (typo-tolerant)

    Searches across agent_name, company_name, and raw_message fields.
    Handles common spelling variations and typos in agent/company names.

    Args:
        agent_name: Agent or company name (e.g., "Tajamul", "TREND SHELTERS")
        limit: Maximum number of results (default: 100)

    Returns:
        CreaWappResponse with matching listings

    Examples:
        # Search for agent Tajamul
        GET /api/crea/listings/search/agent?agent_name=Tajamul

        # Search for company (also matches variations)
        GET /api/crea/listings/search/agent?agent_name=TREND%20SHELTERS

        # Handles typos
        GET /api/crea/listings/search/agent?agent_name=Tajmul
    """
    try:
        print(f"[API-CREA] Fuzzy searching agent: '{agent_name}'")

        result = await SupabaseService.fuzzy_search_agent_name(agent_name=agent_name, limit=limit)
        return result

    except Exception as e:
        print(f"[API-CREA] ✗ Error in fuzzy agent search: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error in fuzzy agent search: {str(e)}")


@router.get("/listings/search/property", response_model=CreaWappResponse)
async def fuzzy_search_property(
    property_query: str = Query(..., description="Property search term (type, configuration, or project name)"),
    limit: int = Query(100, description="Maximum number of results")
):
    """
    Fuzzy search for properties by type, configuration, or project (typo-tolerant)

    Searches across property_type, configuration, project_name, and raw_message fields.
    Handles variations like "3BHK", "3 BHK", "three bhk", "Apartment", "Villa", etc.

    Args:
        property_query: Property search term (e.g., "3BHK", "Villa", "Apartment", "Prestige")
        limit: Maximum number of results (default: 100)

    Returns:
        CreaWappResponse with matching listings

    Examples:
        # Search for 3 BHK (matches "3BHK", "3 BHK", etc.)
        GET /api/crea/listings/search/property?property_query=3BHK

        # Search for property type
        GET /api/crea/listings/search/property?property_query=Villa

        # Search for project name
        GET /api/crea/listings/search/property?property_query=Prestige

        # Handles typos
        GET /api/crea/listings/search/property?property_query=Apartmnt
    """
    try:
        print(f"[API-CREA] Fuzzy searching property: '{property_query}'")

        result = await SupabaseService.fuzzy_search_property(property_query=property_query, limit=limit)
        return result

    except Exception as e:
        print(f"[API-CREA] ✗ Error in fuzzy property search: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error in fuzzy property search: {str(e)}")


@router.get("/search", response_model=CreaWappResponse)
async def unified_search(
    agent_name: Optional[str] = Query(None, description="Agent or company name filter"),
    property_query: Optional[str] = Query(None, description="Property type, configuration, or project filter"),
    location: Optional[str] = Query(None, description="Location filter"),
    limit: int = Query(100, description="Maximum number of results")
):
    """
    Unified search with AND logic across agent, property, and location

    Accepts 1, 2, or 3 search parameters. All provided parameters are combined with AND logic.
    Uses hybrid strategy: exact database matching + fuzzy matching for comprehensive results.

    Args:
        agent_name: Filter by agent or company name (optional)
        property_query: Filter by property type, configuration, or project (optional)
        location: Filter by location (optional)
        limit: Maximum results (default: 100)

    Returns:
        CreaWappResponse with listings matching ALL provided filters

    Examples:
        # All 3 filters (AND condition)
        GET /api/crea/search?agent_name=Tajamul&property_query=3BHK&location=Indiranagar

        # 2 filters
        GET /api/crea/search?property_query=Villa&location=Whitefield

        # 1 filter
        GET /api/crea/search?location=Koramangala

        # With limit
        GET /api/crea/search?agent_name=TREND%20SHELTERS&limit=50
    """
    try:
        # Validate at least one parameter is provided
        if not any([agent_name, property_query, location]):
            raise HTTPException(
                status_code=400,
                detail="At least one search parameter is required (agent_name, property_query, or location)"
            )

        print(f"[API-CREA] Unified search: agent={agent_name}, property={property_query}, location={location}")

        result = await SupabaseService.unified_search(
            agent_name=agent_name,
            property_query=property_query,
            location=location,
            limit=limit
        )

        return result

    except HTTPException:
        raise
    except Exception as e:
        print(f"[API-CREA] ✗ Error in unified search: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error in unified search: {str(e)}")


# ============================================================================
# Agent Summary Endpoints
# ============================================================================

@router.get("/agents/summary")
async def get_all_agents_summary(
    limit: int = Query(100, description="Maximum number of agents to return"),
    offset: int = Query(0, description="Number of agents to skip for pagination")
):
    """
    Get aggregated summary for all agents

    Returns one row per agent with all their activity aggregated including:
    - Total posts, first/last seen dates
    - Listing type breakdown (sale, rent, requirements)
    - Property types and locations
    - Price and size statistics
    - BHK configurations

    Args:
        limit: Maximum number of agents (default: 100)
        offset: Number of agents to skip (default: 0)

    Returns:
        List of agent summaries

    Example:
        GET /api/crea/agents/summary?limit=50&offset=0
    """
    try:
        print(f"[API-CREA] Retrieving agent summaries (limit: {limit}, offset: {offset})")

        result = await SupabaseService.get_agent_summaries(limit=limit, offset=offset)

        return result

    except Exception as e:
        print(f"[API-CREA] ✗ Error retrieving agent summaries: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving agent summaries: {str(e)}")


@router.get("/agents/summary/{agent_contact}")
async def get_agent_summary_by_contact(agent_contact: str):
    """
    Get aggregated summary for a specific agent by contact number

    Returns comprehensive statistics for the agent including:
    - Total posts, activity date range
    - Listing type breakdown
    - Property types, locations, configurations
    - Price and size ranges
    - Sample raw messages

    Args:
        agent_contact: Agent phone number (e.g., +919876543210)

    Returns:
        Agent summary data

    Example:
        GET /api/crea/agents/summary/+919876543210
    """
    try:
        print(f"[API-CREA] Retrieving summary for agent: {agent_contact}")

        result = await SupabaseService.get_agent_summary_by_contact(agent_contact)

        if not result or not result.get("data"):
            raise HTTPException(status_code=404, detail=f"No data found for agent {agent_contact}")

        return result

    except HTTPException:
        raise
    except Exception as e:
        print(f"[API-CREA] ✗ Error retrieving agent summary: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving agent summary: {str(e)}")
