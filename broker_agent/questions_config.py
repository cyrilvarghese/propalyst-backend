"""
Questions Configuration
=======================

Centralized configuration for all conversation questions.
This file defines the question sequence, UI controls, and state mappings.

To add a new question:
1. Add a QuestionDefinition dict to QUESTIONS_CONFIG list
2. Add corresponding state field to state.py
3. Create question node function in nodes/questions.py (optional, uses generic handler if not specified)
4. Update service.py field mapping if custom logic needed

The system will automatically:
- Route through questions in order
- Map answers to state fields
- Generate UI from control_type and control_data
"""

from broker_agent.state import QuestionDefinition

# ============================================================================
# QUESTIONS CONFIGURATION
# ============================================================================

QUESTIONS_CONFIG = [
    QuestionDefinition(
        id="req_type",
        order=1,
        state_field="req_type",
        question="Are you looking to buy or sell a property?",
        label="Transaction Type",
        control_type="radio",
        required=True,
        control_data={
            "options": [
                {"value": "buy", "label": "Buy", "icon": "ShoppingCart"},
                {"value": "sell", "label": "Sell", "icon": "Tag"},
            ],
        },
        help_text="Select whether you want to buy or sell a property",
        node_fn="ask_transaction_type",
    ),
    QuestionDefinition(
        id="proximity_location",
        order=2,
        state_field="proximity_location",
        question="Is there a work location or important place you want to be near?",
        label="Proximity Preference",
        control_type="location-proximity",
        required=False,
        control_data={
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
        help_text="Select a location to find nearby properties",
        node_fn="ask_location",
    ),
    QuestionDefinition(
        id="budget",
        order=3,
        state_field="price_range",
        state_field_min="price_min",
        state_field_max="price_max",
        question="What's your budget range?",
        label="Budget Range",
        control_type="range-slider",
        required=True,
        control_data={
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
        help_text="Drag to select your budget range. The chart shows property distribution.",
        node_fn="ask_price_range",
    ),
    QuestionDefinition(
        id="property_area",
        order=4,
        state_field="property_area_range",
        state_field_min="area_min",
        state_field_max="area_max",
        question="What size property are you looking for? (in sq ft)",
        label="Property Area",
        control_type="range-slider",
        required=True,
        control_data={
            "min": 500,
            "max": 5000,
            "step": 100,
            "labels": ["Min Area", "Max Area"],
            "defaultValues": [1000, 2500],
            "unit": "sq ft",
        },
        help_text="Slide to set your preferred property size range",
        node_fn="ask_property_area",
    ),
    QuestionDefinition(
        id="bedroom_count",
        order=5,
        state_field="bedroom_count",
        question="How many bedrooms are you looking for?",
        label="Bedroom Count",
        control_type="radio",
        required=True,
        control_data={
            "options": [
                {"value": 1, "label": "1 BHK", "icon": "Door"},
                {"value": 2, "label": "2 BHK", "icon": "Doors"},
                {"value": 3, "label": "3 BHK", "icon": "Building"},
                {"value": 4, "label": "4 BHK", "icon": "Mansion"},
                {"value": 5, "label": "5+ BHK", "icon": "Castle"},
            ],
        },
        help_text="Select the number of bedrooms you need",
        node_fn="ask_bedroom_count",
    ),
    QuestionDefinition(
        id="property_type",
        order=6,
        state_field="property_type",
        question="What type of property are you interested in?",
        label="Property Type",
        control_type="toggle-group",
        required=True,
        control_data={
            "options": [
                {"value": "apartment", "label": "Apartment", "icon": "Building"},
                {"value": "house", "label": "House", "icon": "Home"},
                {"value": "villa", "label": "Villa", "icon": "Castle"},
                {"value": "penthouse", "label": "Penthouse", "icon": "Star"},
                {"value": "townhouse", "label": "Townhouse", "icon": "Buildings"},
                {"value": "plot", "label": "Plot", "icon": "LandPlot"},
            ],
        },
        help_text="Select the type of property you're looking for",
        node_fn="ask_property_type",
    ),
    QuestionDefinition(
        id="special_features",
        order=7,
        state_field="special_features",
        question="Any special preferences?",
        label="Special Requests",
        control_type="tags",
        required=False,
        control_data={
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
        help_text="Add any special features or preferences you're looking for",
        node_fn="ask_special_features",
    ),
    QuestionDefinition(
        id="taste_preference",
        order=8,
        state_field="taste_preference",
        question="Let's understand your taste! Swipe through these properties",
        label="Taste Selection",
        control_type="taste-selection",
        required=False,
        control_data={
            "properties": [
                {
                    "id": "1",
                    "property_type": "apartment",
                    "message_type": "supply_sale",
                    "bedroom_count": 3,
                    "area_sqft": 1610,
                    "price": 12800000,
                    "price_text": "₹ 1.28 Cr.",
                    "location": "Indiranagar",
                    "project_name": "Prestige Montecarlo",
                    "furnishing_status": "semi_furnished",
                    "facing_direction": "garden",
                    "special_features": ["garden_facing", "negotiable"],
                    "agent_name": "TREND SHELTERS Shamran",
                    "agent_contact": "+91 9686115795",
                    "raw_message": "🏡 3 BHK With 2 Balconies Facing Garden\n📏 1,610 Sq ft\n🪚 Semi Furnished\n💰 ₹ 1.28 Cr.\n📶 Available: Immediate",
                    "image_url": "https://images.unsplash.com/photo-1545324418-cc1a3fa10c00?q=80&w=800&auto=format&fit=crop"
                },
                {
                    "id": "2",
                    "property_type": "apartment",
                    "message_type": "supply_rent",
                    "bedroom_count": 3,
                    "area_sqft": 1900,
                    "price": 85000,
                    "price_text": "₹85k plus maintenance",
                    "location": "Indiranagar",
                    "project_name": "SJR Primecorp Vogue",
                    "furnishing_status": "fully_furnished",
                    "facing_direction": "east",
                    "special_features": ["metro_nearby", "available_immediate"],
                    "agent_name": "Not provided",
                    "agent_contact": "Contact via WhatsApp",
                    "raw_message": "3 bathrooms, 3 balcony\nRent 85k plus maintenance\nDeposit: 5 months rent\nFloor no - 5\nAvailable immediate",
                    "image_url": "https://images.unsplash.com/photo-1522708323590-d24dbb6b0267?q=80&w=800&auto=format&fit=crop"
                },
                {
                    "id": "3",
                    "property_type": "apartment",
                    "message_type": "supply_rent",
                    "bedroom_count": 3,
                    "area_sqft": 1800,
                    "price": 55000,
                    "price_text": "₹55k",
                    "location": "HAL 3rd Stage",
                    "project_name": "Adarsh Palm Retreat",
                    "furnishing_status": "semi_furnished",
                    "facing_direction": "east",
                    "special_features": ["clubhouse", "swimming_pool", "parking"],
                    "agent_name": "Tashi Properties",
                    "agent_contact": "7026070800 / 9916251225",
                    "raw_message": "3 BHK semi furnished\n1800 sqft\nClubhouse & Swimming pool\n₹55k per month",
                    "image_url": "https://images.unsplash.com/photo-1497366216548-37526070297c?q=80&w=800&auto=format&fit=crop"
                },
                {
                    "id": "4",
                    "property_type": "apartment",
                    "message_type": "supply_sale",
                    "bedroom_count": 2,
                    "area_sqft": 1200,
                    "price": 8500000,
                    "price_text": "₹85 Lakhs",
                    "location": "Indiranagar 2nd Stage",
                    "project_name": "Sobha Dream Acres",
                    "furnishing_status": "fully_furnished",
                    "facing_direction": "north",
                    "special_features": ["club_house", "swimming_pool"],
                    "agent_name": "Prakash Realty",
                    "agent_contact": "+91 9876543210",
                    "raw_message": "2 BHK fully furnished\n1200 sqft\nClub house & Swimming pool\n₹85 Lakhs",
                    "image_url": "https://images.unsplash.com/photo-1512917774080-9991f1c4c750?q=80&w=800&auto=format&fit=crop"
                },
                {
                    "id": "5",
                    "property_type": "apartment",
                    "message_type": "supply_rent",
                    "bedroom_count": 2,
                    "area_sqft": 1150,
                    "price": 35000,
                    "price_text": "₹35k",
                    "location": "Indiranagar",
                    "project_name": "Brigade Millennium",
                    "furnishing_status": "semi_furnished",
                    "facing_direction": "south",
                    "special_features": ["gym", "security"],
                    "agent_name": "Sunita Properties",
                    "agent_contact": "+91 9988776655",
                    "raw_message": "2 BHK semi furnished\n1150 sqft\nGym & 24/7 Security\n₹35k per month",
                    "image_url": "https://images.unsplash.com/photo-1502672260266-1c1ef2d93688?q=80&w=800&auto=format&fit=crop"
                },
            ],
        },
        help_text="Indicate thumbs up/down on properties to help us understand your preferences",
        node_fn="ask_taste_preference",
    ),
]


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_question_by_id(question_id: str) -> QuestionDefinition | None:
    """Get question configuration by ID"""
    for q in QUESTIONS_CONFIG:
        if q.id == question_id:
            return q
    return None


def get_question_by_order(order: int) -> QuestionDefinition | None:
    """Get question configuration by order"""
    for q in QUESTIONS_CONFIG:
        if q.order == order:
            return q
    return None


def get_all_questions() -> list[QuestionDefinition]:
    """Get all questions sorted by order"""
    return sorted(QUESTIONS_CONFIG, key=lambda q: q.order)


def get_question_ids_sorted() -> list[str]:
    """Get all question IDs in order"""
    return [q.id for q in get_all_questions()]


def get_state_field_for_question(question_id: str) -> str | None:
    """Get the state field(s) for a question"""
    q = get_question_by_id(question_id)
    if not q:
        return None
    return q.state_field


def get_state_fields_for_question(question_id: str) -> list[str]:
    """Get all state fields for a question (handles range questions with min/max)"""
    q = get_question_by_id(question_id)
    if not q:
        return []

    fields = [q.state_field]
    if q.state_field_min:
        fields[0] = q.state_field_min
        fields.append(q.state_field_max)
    return fields


__all__ = [
    "QUESTIONS_CONFIG",
    "get_question_by_id",
    "get_question_by_order",
    "get_all_questions",
    "get_question_ids_sorted",
    "get_state_field_for_question",
    "get_state_fields_for_question",
]
