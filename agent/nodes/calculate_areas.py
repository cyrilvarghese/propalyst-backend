"""
Calculate Recommended Areas Node
==================================

This node calculates recommended areas based on user preferences.
Triggered after all 5 questions (Q1-Q5) are answered.

The node:
1. Extracts user preferences from state
2. Applies filtering logic (mock for now)
3. Returns top recommended areas
"""

from typing import List, Dict, Any
from ..state import PropalystState


def calculate_recommended_areas(state: PropalystState) -> PropalystState:
    """
    Calculate recommended areas based on user preferences.

    This is triggered after Q5 (budget) is answered.

    Args:
        state: Current PropalystState with all Q1-Q5 answers filled

    Returns:
        Updated state with recommended_areas populated

    Example:
        Input state:
        {
            "work_location": "Whitefield",
            "has_kids": True,
            "commute_time_max": 20,
            "property_type": "Villa",
            "budget_max": 75000,
            "calculated": False
        }

        Output state:
        {
            ...same as input...,
            "recommended_areas": [
                {"areaName": "Whitefield", ...},
                {"areaName": "Marathahalli", ...}
            ],
            "calculated": True
        }
    """

    print("\n🏘️  CALCULATE AREAS NODE")
    print("   Calculating recommended areas based on preferences...")

    # Extract user preferences
    work_location = state.get("work_location", "")
    has_kids = state.get("has_kids", False)
    commute_time_max = state.get("commute_time_max", 30)
    property_type = state.get("property_type", "")
    budget_max = state.get("budget_max", 100000)

    print(f"   Work: {work_location}")
    print(f"   Kids: {has_kids}")
    print(f"   Commute: {commute_time_max} min")
    print(f"   Type: {property_type}")
    print(f"   Budget: ₹{budget_max:,}")

    # Mock area database
    # Later: Replace with real API/database query
    all_areas = [
        {
            "areaName": "Whitefield",
            "image": "https://images.unsplash.com/photo-1600607687939-ce8a6c25118c?q=80&w=2053",
            "childFriendlyScore": 9,
            "schoolsNearby": 12,
            "averageCommute": "15-20 min",
            "budgetRange": "₹60K - ₹85K",
            "highlights": ["IT Hub", "Great Schools", "Metro Access"]
        },
        {
            "areaName": "Marathahalli",
            "image": "https://images.unsplash.com/photo-1600596542815-ffad4c1539a9?q=80&w=2075",
            "childFriendlyScore": 8,
            "schoolsNearby": 10,
            "averageCommute": "20-25 min",
            "budgetRange": "₹50K - ₹75K",
            "highlights": ["Good Connectivity", "Family Friendly", "Shopping"]
        },
        {
            "areaName": "Indiranagar",
            "image": "https://images.unsplash.com/photo-1613490493576-7fde63acd811?q=80&w=2071",
            "childFriendlyScore": 7,
            "schoolsNearby": 8,
            "averageCommute": "25-30 min",
            "budgetRange": "₹70K - ₹90K",
            "highlights": ["Upscale Area", "Parks", "Cafes & Restaurants"]
        },
        {
            "areaName": "Brookefield",
            "image": "https://images.unsplash.com/photo-1600585154340-be6161a56a0c?q=80&w=2070",
            "childFriendlyScore": 9,
            "schoolsNearby": 15,
            "averageCommute": "10-15 min",
            "budgetRange": "₹55K - ₹80K",
            "highlights": ["Close to Whitefield", "Quiet", "Premium Schools"]
        },
        {
            "areaName": "Koramangala",
            "image": "https://images.unsplash.com/photo-1512917774080-9991f1c4c750?q=80&w=2070",
            "childFriendlyScore": 7,
            "schoolsNearby": 9,
            "averageCommute": "30-35 min",
            "budgetRange": "₹65K - ₹95K",
            "highlights": ["Vibrant", "Startups", "Nightlife"]
        },
        {
            "areaName": "HSR Layout",
            "image": "https://images.unsplash.com/photo-1580587771525-78b9dba3b914?q=80&w=2074",
            "childFriendlyScore": 8,
            "schoolsNearby": 11,
            "averageCommute": "25-30 min",
            "budgetRange": "₹55K - ₹80K",
            "highlights": ["Parks", "Shopping", "Well-planned"]
        }
    ]

    # Simple filtering logic (mock for now)
    # Later: Implement real scoring/filtering algorithm
    recommended = all_areas[:6]  # Return all 6 for now

    print(f"   ✅ Found {len(recommended)} recommended areas")

    # Return updated state
    return {
        **state,
        "recommended_areas": recommended,
        "calculated": True,
        "message": f"Based on your preferences, here are {len(recommended)} recommended areas",
        "current_step": state.get("current_step", 5) + 1
    }


__all__ = ["calculate_recommended_areas"]
