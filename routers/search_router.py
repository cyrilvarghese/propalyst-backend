"""
Property Search Router
======================

API endpoints for property search functionality.
"""

import os
from fastapi import APIRouter, HTTPException

from models.search import PropertySearchRequest, SearchResponse
from providers.gemini_search import GeminiSearchProvider


router = APIRouter(
    prefix="/api",
    tags=["Property Search"]
)


@router.post("/property-search")
async def property_search(request: PropertySearchRequest):
    """
    Search for properties using natural language with Gemini grounding.

    Request:
        {
            "query": "3bhk near indiranagar budget 4-7 crores",
            "sources": "magicbricks,housing",
            "provider": "gemini"
        }

    Response: SearchResponse with results, extracted_params, sources
    """
    print("\n" + "🚀"*40)
    print("PROPERTY SEARCH ENDPOINT HIT")
    print(f"REQUEST OBJECT TYPE: {type(request)}")
    print(f"REQUEST DICT: {request.dict()}")
    print(f"  Query: '{request.query}'")
    print(f"  Sources: '{request.sources}'")
    print(f"  Provider: '{request.provider}'")
    print("🚀"*40 + "\n")

    try:
        print("Step 1: Checking for GEMINI_API_KEY...")
        # Get Google API key from environment
        gemini_api_key = os.getenv("GEMINI_API_KEY")
        print(f"  API Key found: {bool(gemini_api_key)}")
        if not gemini_api_key:
            raise HTTPException(
                status_code=500,
                detail="GEMINI_API_KEY not configured in environment"
            )

        # Initialize provider based on request
        if request.provider == "gemini":
            provider = GeminiSearchProvider(api_key=gemini_api_key)
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Provider '{request.provider}' not supported yet. Only 'gemini' is available."
            )

        # Step 1: Extract parameters from natural language query
        print("\n" + "="*80)
        print(f"🔍 QUERY: {request.query}")
        print("="*80)

        params = await provider.extract_parameters(request.query)

        print("\n📊 EXTRACTED PARAMETERS:")
        print(f"  - Property Type: {params.property_type}")
        print(f"  - Category: {params.category}")
        print(f"  - Location: {params.location}")
        print(f"  - Budget: {params.budget_min} - {params.budget_max} crores")
        print(f"  - Keywords: {params.keywords}")
        print(f"  - City: {params.city}")

        # Step 2: Search with grounding (pass sources for site: operator)
        print(f"\n🔎 SEARCHING with source filters: {request.sources}")
        results = await provider.search(params, source=request.sources)

        # Step 3: Extract grounding sources (if available)
        sources = []  # Will be populated by provider

        # Build response
        response = SearchResponse(
            results=results,
            extracted_params=params,
            sources=sources,
            total_results=len(results),
            provider=request.provider
        )

        # Log results going to frontend
        print("\n" + "="*80)
        print("📤 RESPONSE TO FRONTEND:")
        print("="*80)
        print(f"Total Results: {len(results)}")
        print("\nProperty Listings:")
        for i, result in enumerate(results, 1):
            print(f"\n  [{i}] {result.title}")
            print(f"      URL: {result.url}")
            print(f"      Location: {result.location}")
            print(f"      Type: {result.property_type}")
            print(f"      Price: {result.price}")
            print(f"      Snippet: {result.snippet[:100]}..." if result.snippet and len(result.snippet) > 100 else f"      Snippet: {result.snippet}")

        print("\n" + "="*80)
        print(f"✅ Response ready to send to frontend")
        print("="*80 + "\n")

        return response

    except HTTPException as he:
        print(f"\n❌ HTTP Exception caught:")
        print(f"   Status: {he.status_code}")
        print(f"   Detail: {he.detail}\n")
        raise
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR:")
        print(f"   Type: {type(e).__name__}")
        print(f"   Message: {str(e)}")
        import traceback
        print(f"   Traceback:\n{traceback.format_exc()}\n")
        raise HTTPException(
            status_code=500,
            detail=f"Search failed: {str(e)}"
        )
