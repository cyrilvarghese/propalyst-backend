"""
Locality Distribution Router
=============================

API endpoints for locality distribution statistics.
Provides aggregated property distribution data per locality.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, Dict, Any
from services.distributions.service import LocalityDistributionService


router = APIRouter(
    prefix="/api/distributions",
    tags=["Distributions"]
)


@router.get("/localities")
async def get_locality_distributions(
    location: Optional[str] = Query(None, description="Optional location filter (case-insensitive partial match)"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of localities to return")
) -> Dict[str, Any]:
    """
    Get distribution statistics per locality

    Returns aggregated property distributions for each locality including:
    - **Price ranges**: 2-5Cr, 5-8Cr, 8-10Cr, 10-12Cr, 12-15Cr, 15Cr+
    - **Area ranges**: 0-500, 500-1000, 1000-1500, 1500-2000, 2000-3000, 3000-4000, 4000-5000, 5000+ sqft
    - **Property types**: Apartment, Villa, Independent House, Plot
    - **Bedroom counts**: 1BHK, 2BHK, 3BHK, 4BHK

    Query Parameters:
    - **location**: Optional location filter (e.g., "indiranagar" returns "Indiranagar", "koramangala", etc.)
    - **limit**: Max localities to return (1-1000, default: 100)

    Returns:
        ```json
        {
            "success": true,
            "data": {
                "distributions": {
                    "Indiranagar": {
                        "price": [
                            {"name": "5-8Cr", "count": 2},
                            {"name": "8-10Cr", "count": 3}
                        ],
                        "area": [
                            {"name": "0-500", "count": 1}
                        ],
                        "propertyType": [
                            {"name": "Apartment", "count": 5}
                        ],
                        "bedroom": [
                            {"name": "2BHK", "count": 3}
                        ]
                    }
                }
            },
            "count": 1,
            "message": "Retrieved distributions for 1 localities"
        }
        ```

    Examples:
        - GET /api/distributions/localities - Get all localities
        - GET /api/distributions/localities?location=indiranagar - Filter by location
        - GET /api/distributions/localities?limit=50 - Limit results
        - GET /api/distributions/localities?location=white&limit=5 - Fuzzy search + limit
    """
    try:
        print(f"[API-Distribution] Fetching locality distributions (location={location}, limit={limit})")

        result = await LocalityDistributionService.get_distributions(
            location=location,
            limit=limit
        )

        if not result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=result.get("message", "Failed to retrieve distributions")
            )

        return result

    except HTTPException:
        raise
    except Exception as e:
        print(f"[API-Distribution] ✗ Error retrieving distributions: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving distributions: {str(e)}"
        )
