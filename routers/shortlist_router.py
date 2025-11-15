"""
Shortlist Router
================

API endpoints for managing property shortlists.
"""

from fastapi import APIRouter, HTTPException
from models.shortlist import CreateShortlistRequest, ShortlistResponse
from services.shortlist_service import ShortlistService

router = APIRouter(
    prefix="/api/shortlist",
    tags=["Shortlist"]
)


@router.post("", response_model=ShortlistResponse)
async def create_shortlist(request: CreateShortlistRequest):
    """
    Create a new shortlist with properties

    Args:
        request: CreateShortlistRequest with description, source URL, and properties

    Returns:
        ShortlistResponse with created shortlist data
    """
    try:
        print(f"[API-Shortlist] Creating shortlist: {request.description[:50]}...")
        result = await ShortlistService.create_shortlist(
            description=request.description,
            source=request.source,
            properties=request.properties
        )
        return result
    except Exception as e:
        print(f"[API-Shortlist] ✗ Error creating shortlist: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error creating shortlist: {str(e)}")


@router.get("", response_model=ShortlistResponse)
async def get_all_shortlists():
    """
    Retrieve all shortlists

    Returns:
        ShortlistResponse with list of all shortlists
    """
    try:
        print(f"[API-Shortlist] Retrieving all shortlists")
        result = await ShortlistService.get_all_shortlists()
        return result
    except Exception as e:
        print(f"[API-Shortlist] ✗ Error retrieving shortlists: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving shortlists: {str(e)}")


@router.get("/{shortlist_id}", response_model=ShortlistResponse)
async def get_shortlist_by_id(shortlist_id: str):
    """
    Retrieve a specific shortlist by ID

    Args:
        shortlist_id: Unique identifier of the shortlist

    Returns:
        ShortlistResponse with shortlist data
    """
    try:
        print(f"[API-Shortlist] Retrieving shortlist: {shortlist_id}")
        result = await ShortlistService.get_shortlist_by_id(shortlist_id)

        if not result["success"]:
            raise HTTPException(status_code=404, detail=result["message"])

        return result
    except HTTPException:
        raise
    except Exception as e:
        print(f"[API-Shortlist] ✗ Error retrieving shortlist: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving shortlist: {str(e)}")


@router.delete("/{shortlist_id}", response_model=ShortlistResponse)
async def delete_shortlist(shortlist_id: str):
    """
    Delete a shortlist by ID

    Args:
        shortlist_id: Unique identifier of the shortlist to delete

    Returns:
        ShortlistResponse with success status
    """
    try:
        print(f"[API-Shortlist] Deleting shortlist: {shortlist_id}")
        result = await ShortlistService.delete_shortlist(shortlist_id)

        if not result["success"]:
            raise HTTPException(status_code=404, detail=result["message"])

        return result
    except HTTPException:
        raise
    except Exception as e:
        print(f"[API-Shortlist] ✗ Error deleting shortlist: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error deleting shortlist: {str(e)}")
