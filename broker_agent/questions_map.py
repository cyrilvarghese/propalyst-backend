"""
Questions Map - Question Lookup Dictionary
=============================================

Centralized mapping of question IDs to their full details.
Used by router to pass rich context to the acknowledge node.

This prevents hallucination by giving the LLM the actual question text,
not just the topic name.
"""

from typing import Dict, Any

# Map question_id → full question details
# Note: Keys must match the question_id values used by the router
QUESTIONS_MAP: Dict[str, Dict[str, Any]] = {
    "req_type": {
        "id": "req_type",
        "text": "Are you looking to buy or sell a property?",
        "label": "Transaction Type",
        "description": "Whether the user wants to buy or sell",
    },
    "proximity_location": {
        "id": "proximity_location",
        "text": "Is there a work location or important place you want to be near?",
        "label": "Proximity Preference",
        "description": "Location preference based on proximity to work or other important places",
    },
    "budget": {
        "id": "budget",
        "text": "What's your budget range?",
        "label": "Budget Range",
        "description": "Budget range in crores",
    },
    "property_area": {
        "id": "property_area",
        "text": "What size property are you looking for? (in sq ft)",
        "label": "Property Area",
        "description": "Desired property size in square feet",
    },
    "property_type": {
        "id": "property_type",
        "text": "What type of property are you interested in?",
        "label": "Property Type",
        "description": "Type of property (apartment, house, villa, etc.)",
    },
    "special_requests": {
        "id": "special_requests",
        "text": "Any special preferences?",
        "label": "Special Requests",
        "description": "Special features or preferences",
    },
}


def get_question(question_id: str) -> Dict[str, Any]:
    """
    Get question details by ID.

    Args:
        question_id (str): Question identifier (e.g., "budget", "property_area")

    Returns:
        Dict[str, Any]: Question details with text, label, description

    Examples:
        >>> get_question("budget")
        {
            "id": "budget",
            "text": "What's your budget range?",
            "label": "Budget Range",
            "description": "Budget range in crores"
        }

        >>> get_question("unknown")
        {
            "id": "unknown",
            "text": "Unknown question",
            "label": "Unknown",
            "description": "No description available"
        }
    """
    if question_id in QUESTIONS_MAP:
        return QUESTIONS_MAP[question_id]

    # Fallback for unmapped question IDs
    return {
        "id": question_id,
        "text": "Unknown question",
        "label": "Unknown",
        "description": "No description available",
    }


__all__ = ["QUESTIONS_MAP", "get_question"]
