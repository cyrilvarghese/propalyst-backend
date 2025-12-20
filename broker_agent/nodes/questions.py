"""
Real Estate Agent Question Nodes
==================================

Each node asks a specific question and returns a ConversationalQuestion object.

Questions in order:
1. Transaction type (buy or sell)
2. Location
3. Price range
4. Property area size
5. Property type
6. Special features
"""

from broker_agent.state import RealEstateAgentState


# ============================================================================
# Q1: TRANSACTION TYPE (Buy or Sell)
# ============================================================================

async def ask_transaction_type(state: RealEstateAgentState) -> RealEstateAgentState:
    """
    Ask if user wants to buy or sell a property.

    Returns state with current_question set to transaction type.
    """

    # Skip if already answered
    if state.get("req_type"):
        return state

    question = {
        "id": "req_type",
        "question": "Are you looking to buy or sell a property?",
        "label": "Transaction Type",
        "controlType": "radio",
        "required": True,
        "data": {
            "options": [
                {"value": "buy", "label": "Buy", "icon": "ShoppingCart"},
                {"value": "sell", "label": "Sell", "icon": "Tag"},
            ],
        },
        "helpText": "Select whether you want to buy or sell a property",
    }

    return {
        **state,
        "current_question": question,
        "current_question_id": "req_type",
        "conversational_message": question["question"],
        "completed": False,
    }


# ============================================================================
# Q2: LOCATION
# ============================================================================

async def ask_location(state: RealEstateAgentState) -> RealEstateAgentState:
    """
    Ask for proximity-based location preference.

    Allows user to select a location type (work, school, home, hospital)
    and pin location on map to find nearby properties.
    """

    # Skip if already answered
    if state.get("proximity_location"):
        return state

    question = {
        "id": "proximity_location",
        "question": "Is there a work location or important place you want to be near?",
        "label": "Proximity Preference",
        "controlType": "location-proximity",
        "required": False,
        "data": {
            "options": [
                {"value": "my_work", "label": "My Work Location", "icon": "Briefcase"},
                {"value": "spouse_work", "label": "Spouse's Work", "icon": "Users"},
                {"value": "school", "label": "School/Childcare", "icon": "BookOpen"},
                {"value": "parents_home", "label": "Parents' Home", "icon": "Home"},
                {"value": "hospital", "label": "Hospital/Medical", "icon": "Heart"},
            ],
            "mapCenter": {"lat": 12.9716, "lng": 77.5946},  # Bangalore center
            "radiusKm": 25,
            "marketInsights": "Proximity to work reduces commute time significantly",
        },
        "helpText": "Select a location type and pin your location on the map to find nearby properties",
    }

    return {
        **state,
        "current_question": question,
        "current_question_id": "proximity_location",
        "conversational_message": question["question"],
        "completed": False,
    }


# ============================================================================
# Q3: PRICE RANGE
# ============================================================================

async def ask_price_range(state: RealEstateAgentState) -> RealEstateAgentState:
    """
    Ask for budget range in crores with price distribution histogram.

    Shows market insights with histogram of property distribution by price range.
    """

    # Skip if already answered
    if state.get("price_min") and state.get("price_max"):
        return state

    question = {
        "id": "budget",
        "question": "What's your budget range?",
        "label": "Budget Range",
        "controlType": "range-slider",
        "required": True,
        "data": {
            "chartTitle": "Price Distribution In Crores",
            "min": 0.5,
            "max": 5,
            "step": 0.1,
            "unit": "Cr",
            "defaultValue": [1.2, 2.5],
            "recommendedValue": [1.5, 2.0],
            "histogram": [
                {"range": "50L-75L", "count": 12, "minValue": 0.5, "maxValue": 0.75},
                {"range": "75L-1Cr", "count": 28, "minValue": 0.75, "maxValue": 1.0},
                {"range": "1-1.5Cr", "count": 65, "minValue": 1.0, "maxValue": 1.5},
                {"range": "1.5-2Cr", "count": 120, "minValue": 1.5, "maxValue": 2.0},
                {"range": "2-2.5Cr", "count": 95, "minValue": 2.0, "maxValue": 2.5},
                {"range": "2.5-3Cr", "count": 45, "minValue": 2.5, "maxValue": 3.0},
                {"range": "3-4Cr", "count": 30, "minValue": 3.0, "maxValue": 4.0},
                {"range": "4-5Cr", "count": 15, "minValue": 4.0, "maxValue": 5.0},
            ],
            "marketInsights": "Most 3BHK apartments in Indiranagar are priced between 1.5-2.5 Cr",
        },
        "helpText": "Drag to select your budget range. The chart shows property distribution.",
    }

    return {
        **state,
        "current_question": question,
        "current_question_id": "budget",
        "conversational_message": question["question"],
        "completed": False,
    }


# ============================================================================
# Q4: PROPERTY AREA/SIZE
# ============================================================================

async def ask_property_area(state: RealEstateAgentState) -> RealEstateAgentState:
    """
    Ask for desired property size/area in square feet.

    Collects minimum and maximum area preferences.
    """

    # Skip if already answered
    if state.get("area_min") and state.get("area_max"):
        return state

    question = {
        "id": "property_area",
        "question": "What size property are you looking for? (in sq ft)",
        "label": "Property Area",
        "controlType": "range-slider",
        "required": True,
        "data": {
            "min": 500,
            "max": 5000,
            "step": 100,
            "labels": ["Min Area", "Max Area"],
            "defaultValues": [1000, 2500],
            "unit": "sq ft",
        },
        "helpText": "Slide to set your preferred property size range",
    }

    return {
        **state,
        "current_question": question,
        "current_question_id": "property_area",
        "conversational_message": question["question"],
        "completed": False,
    }


# ============================================================================
# Q5: PROPERTY TYPE
# ============================================================================

async def ask_property_type(state: RealEstateAgentState) -> RealEstateAgentState:
    """
    Ask what type of property user is looking for.

    Common property types: apartment, house, villa, penthouse, townhouse
    """

    # Skip if already answered
    if state.get("property_type"):
        return state

    question = {
        "id": "property_type",
        "question": "What type of property are you interested in?",
        "label": "Property Type",
        "controlType": "toggle-group",
        "required": True,
        "data": {
            "options": [
                {"value": "apartment", "label": "Apartment", "icon": "Building"},
                {"value": "house", "label": "House", "icon": "Home"},
                {"value": "villa", "label": "Villa", "icon": "Castle"},
                {"value": "penthouse", "label": "Penthouse", "icon": "Star"},
                {"value": "townhouse", "label": "Townhouse", "icon": "Buildings"},
                {"value": "plot", "label": "Plot", "icon": "LandPlot"},
            ],
        },
        "helpText": "Select the type of property you're looking for",
    }

    return {
        **state,
        "current_question": question,
        "current_question_id": "property_type",
        "conversational_message": question["question"],
        "completed": False,
    }


# ============================================================================
# Q6: SPECIAL FEATURES
# ============================================================================

async def ask_special_features(state: RealEstateAgentState) -> RealEstateAgentState:
    """
    Ask about special requests and preferences.

    Allows user to type custom preferences or select from suggestions.
    Uses tag input for flexible preference collection.
    """

    # Skip if already answered
    if state.get("special_features"):
        return state

    question = {
        "id": "special_requests",
        "question": "Any special preferences?",
        "label": "Special Requests",
        "controlType": "tags",
        "required": False,
        "data": {
            "placeholder": "Type a preference (e.g., north-facing, pet-friendly)",
            "suggestions": [
                "north-facing",
                "pet-friendly",
                "new-property",
                "old-property",
                "vastu-compliant",
                "garden",
                "parking",
            ],
            "marketInsights": "North-facing and pet-friendly properties are increasingly in demand",
        },
        "helpText": "Add any special features or preferences you're looking for",
    }

    return {
        **state,
        "current_question": question,
        "current_question_id": "special_requests",
        "conversational_message": question["question"],
        "completed": False,
    }


# ============================================================================
# EXPORT
# ============================================================================

__all__ = [
    "ask_transaction_type",
    "ask_location",
    "ask_price_range",
    "ask_property_area",
    "ask_property_type",
    "ask_special_features",
]
