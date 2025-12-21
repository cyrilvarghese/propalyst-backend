"""
Real Estate Agent State Definition
====================================

Defines the state structure for the real estate agent conversation flow.

The agent probes for:
1. Transaction type (buy or sell)
2. Location (where the property should be)
3. Price range (minimum and maximum budget)
4. Area (property size in sq ft)
5. Property type (apartment, house, villa, etc.)
6. Special features (preferences and requirements)
"""

from typing import TypedDict, Optional, List, Dict, Any
from pydantic import BaseModel, Field


# ============================================================================
# PYDANTIC MODELS (for validation and serialization)
# ============================================================================

class PropertyPreference(BaseModel):
    """Represents a single property preference/feature"""
    id: str = Field(..., description="Unique preference ID")
    label: str = Field(..., description="Display label")
    icon: Optional[str] = Field(None, description="Icon name for UI")
    selected: bool = Field(default=False, description="Whether this preference is selected")


class ConversationalQuestion(BaseModel):
    """A conversational question to ask the user"""
    id: str = Field(..., description="Question identifier")
    question: str = Field(..., description="The question text")
    label: str = Field(..., description="Short label for the question")
    controlType: str = Field(..., description="UI control type (radio, slider, text, etc.)")
    required: bool = Field(default=True, description="Whether answer is required")
    data: Dict[str, Any] = Field(default_factory=dict, description="Control-specific data")
    helpText: Optional[str] = Field(None, description="Help text for the user")


# ============================================================================
# LANGGRAPH STATE (TypedDict)
# ============================================================================

class RealEstateAgentState(TypedDict):
    """
    State for the real estate agent conversation flow.

    Multi-step conversation where agent asks about:
    1. Transaction type (buy or sell)
    2. Location (preferred area)
    3. Price range (budget)
    4. Area (property size)
    5. Property type (apartment, villa, house, etc.)
    6. Special features (requirements and preferences)

    Fields:
    -------
    session_id (str):
        Unique session identifier for state persistence
        Example: "uuid-1234-5678"

    # TRANSACTION DATA
    transaction_type (str | None):
        Buy or Sell (Q1)
        Example: "buy"

    proximity_location (str | None):
        Preferred proximity-based location (Q2)
        Example: "my_work"

    price_min (float | None):
        Minimum budget in lakhs (Q3)
        Example: 50.0

    price_max (float | None):
        Maximum budget in lakhs (Q3)
        Example: 100.0

    area_min (int | None):
        Minimum property size in sq ft (Q4)
        Example: 1000

    area_max (int | None):
        Maximum property size in sq ft (Q4)
        Example: 2500

    property_type (str | None):
        Type of property (Q5)
        Example: "apartment"
        Options: ["apartment", "house", "villa", "penthouse", "townhouse"]

    special_features (List[str] | None):
        Selected special features/preferences (Q6)
        Example: ["gym", "pool", "parking", "garden"]

    # AGENT STATE
    current_question_id (str | None):
        Which question is currently being asked
        Example: "location"

    questions_completed (List[str]):
        List of question IDs that have been answered
        Example: ["transaction_type", "location"]

    # CONVERSATION TRACKING
    messages (List[Dict]):
        Full conversation history
        Example: [
            {"role": "user", "content": "I want to buy"},
            {"role": "agent", "content": "Great! Where..."}
        ]

    # OUTPUT
    current_question (Dict | None):
        Current question as ConversationalQuestion object

    conversational_message (str):
        Message to display to user
        Example: "Perfect! What's your budget range?"

    completed (bool):
        Whether all questions have been answered

    error (str | None):
        Error message if validation failed

    pending_answer (Any | None):
        The answer waiting to be acknowledged by LLM
        Example: "buy" or [50.0, 100.0]

    pending_question_id (str | None):
        Which question the pending_answer is for
        Example: "req_type"

    last_response_text (str | None):
        LLM-generated acknowledgment for the last answer
        Example: "Great! Buying a property is a significant investment..."
    """

    # Session
    session_id: str

    # Transaction Data
    req_type: Optional[str]
    proximity_location: Optional[str]
    price_min: Optional[float]
    price_max: Optional[float]
    area_min: Optional[int]
    area_max: Optional[int]
    property_type: Optional[str]
    special_features: Optional[List[str]]

    # Agent State
    current_question_id: Optional[str]
    questions_completed: List[str]

    # Conversation
    messages: List[Dict[str, str]]

    # Output
    current_question: Optional[Dict[str, Any]]
    conversational_message: str
    completed: bool
    error: Optional[str]

    # LLM Acknowledgment
    pending_answer: Optional[Any]
    pending_question_id: Optional[str]
    last_response_text: Optional[str]

    # Last Processed (for API response)
    last_processed_answer: Optional[Any]
    last_processed_question_id: Optional[str]


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def create_real_estate_state(session_id: str) -> RealEstateAgentState:
    """
    Creates initial real estate agent state for a new session.

    Args:
        session_id (str): Unique session identifier

    Returns:
        RealEstateAgentState: Fresh state with all fields initialized

    Example:
        >>> state = create_real_estate_state("session-123")
        >>> state["session_id"]
        "session-123"
        >>> state["transaction_type"]
        None
    """
    return RealEstateAgentState(
        session_id=session_id,
        req_type=None,
        proximity_location=None,
        price_min=None,
        price_max=None,
        area_min=None,
        area_max=None,
        property_type=None,
        special_features=None,
        current_question_id=None,
        questions_completed=[],
        messages=[],
        current_question=None,
        conversational_message="",
        completed=False,
        error=None,
        pending_answer=None,
        pending_question_id=None,
        last_response_text=None,
        last_processed_answer=None,
        last_processed_question_id=None,
    )


# ============================================================================
# EXPORT
# ============================================================================

__all__ = [
    "RealEstateAgentState",
    "ConversationalQuestion",
    "PropertyPreference",
    "create_real_estate_state",
]
