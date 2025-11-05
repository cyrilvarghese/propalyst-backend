"""
LangGraph State Definition
===========================

This module defines the state structure for our LangGraph workflow.

Key Concepts:
-------------
1. TypedDict: Defines the shape of state that flows through the graph
2. Pydantic Models: Used for validation and serialization
3. State is immutable: Nodes return NEW state, don't modify existing

Why we need state:
------------------
- State carries data through the workflow
- Each node reads from state and returns updated state
- LangGraph manages state transitions automatically
"""

from typing import TypedDict, Optional, Dict, Any, List
from pydantic import BaseModel, Field


# ============================================================================
# PYDANTIC MODELS (for validation and serialization)
# ============================================================================

class UIComponent(BaseModel):
    """
    Represents a UI component that will be rendered on the frontend.

    Attributes:
        type (str): The component type (e.g., "Button", "Slider", "CheckboxGroup")
        props (dict): Component-specific properties (e.g., label, min, max, options)

    Example:
        {
            "type": "Button",
            "props": {
                "label": "Click Me",
                "variant": "primary"
            }
        }
    """
    type: str = Field(
        ...,
        description="Component type: Button, TextArea, CheckboxGroup, Slider"
    )
    props: Dict[str, Any] = Field(
        default_factory=dict,
        description="Component-specific properties"
    )

    class Config:
        # Allow extra fields in props (flexible for different component types)
        extra = "allow"


# ============================================================================
# LANGGRAPH STATE (TypedDict)
# ============================================================================

class AgentState(TypedDict):
    """
    The state that flows through our LangGraph workflow.

    This TypedDict defines all possible fields in the state.
    Not all fields need to be present at all times.

    Flow:
    -----
    1. START: State initialized with user_input
       { "user_input": "button", "component": None, "message": "", "error": None }

    2. After extract_ui_component node:
       {
         "user_input": "button",
         "component": { "type": "Button", "props": {...} },
         "message": "Here's a button component",
         "error": None
       }

    3. END: State contains final component configuration

    Fields:
    -------
    user_input (str):
        The raw text input from the user
        Example: "checkbox with options A, B, C"

    component (UIComponent | None):
        The extracted UI component configuration
        None if extraction failed or not yet processed
        Example: UIComponent(type="CheckboxGroup", props={"options": ["A", "B", "C"]})

    message (str):
        Human-readable message to show to the user
        Example: "Here's a checkbox group with your options"

    error (str | None):
        Error message if something went wrong
        None if no error
        Example: "Could not understand the component request"
    """

    # Required fields
    user_input: str

    # Optional fields (may be None initially)
    component: Optional[UIComponent]
    message: str
    error: Optional[str]


# ============================================================================
# PROPALYST STATE (Project 2 - Multi-step conversation)
# ============================================================================

class PropalystState(TypedDict):
    """
    State for Propalyst Q&A conversation flow.

    This extends the basic AgentState for multi-step conversations where:
    1. User answers 5 questions (Q1-Q5)
    2. Agent calculates suitable areas
    3. User refines search
    4. Agent shows properties

    Fields:
    -------
    session_id (str):
        Unique session identifier for state persistence
        Example: "uuid-1234-5678"

    # User Data Model (Answers to Q1-Q5)
    work_location (str | None):
        Where user works (Q1)
        Example: "Whitefield"

    has_kids (bool | None):
        Whether user has kids (Q2)
        Example: True

    commute_time_max (int | None):
        Maximum acceptable commute time in minutes (Q3)
        Example: 30

    property_type (str | None):
        Type of property user wants (Q4)
        Example: "Apartment"

    budget_max (int | None):
        Maximum monthly budget in rupees (Q5)
        Example: 80000

    # Calculated Data (Agent computes after Q5)
    recommended_areas (List[Dict] | None):
        Areas that match user criteria
        Example: [
            {"name": "Marathahalli", "commute_minutes": 15, "property_count": 23},
            {"name": "Whitefield", "commute_minutes": 0, "property_count": 18}
        ]

    selected_area (str | None):
        Area user selected from recommendations
        Example: "Marathahalli"

    # Conversation Flow
    messages (List[Dict]):
        Conversation history
        Example: [
            {"role": "agent", "content": "Where do you work?"},
            {"role": "user", "content": "Whitefield"}
        ]

    current_step (int):
        Which step in the flow (1-9)
        1-5: Questions, 6: Show areas, 7: Refine budget, etc.

    # Output (same as AgentState)
    component (Optional[UIComponent]):
        Current UI component to render

    message (str):
        Message to show user

    error (Optional[str]):
        Error message if any
    """

    # Session
    session_id: str

    # User data model
    work_location: Optional[str]
    has_kids: Optional[bool]
    commute_time_max: Optional[int]
    property_type: Optional[str]
    budget_max: Optional[int]

    # Calculated data
    recommended_areas: Optional[List[Dict[str, Any]]]
    selected_area: Optional[str]
    calculated: Optional[bool]  # Flag: has calculation been done?

    # Conversation
    messages: List[Dict[str, str]]
    current_step: int

    # UI output
    component: Optional[UIComponent]
    message: str
    error: Optional[str]


def create_propalyst_state(session_id: str) -> PropalystState:
    """
    Creates initial Propalyst state for a new session.

    Args:
        session_id (str): Unique session identifier

    Returns:
        PropalystState: Fresh state with all fields initialized

    Example:
        >>> state = create_propalyst_state("session-123")
        >>> state["session_id"]
        "session-123"
        >>> state["work_location"]
        None
    """
    return PropalystState(
        session_id=session_id,
        work_location=None,
        has_kids=None,
        commute_time_max=None,
        property_type=None,
        budget_max=None,
        recommended_areas=None,
        selected_area=None,
        calculated=False,
        messages=[],
        current_step=1,
        component=None,
        message="",
        error=None
    )


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def create_initial_state(user_input: str) -> AgentState:
    """
    Creates the initial state for the workflow.

    Args:
        user_input (str): The user's UI component request

    Returns:
        AgentState: Initial state with user_input set, other fields empty

    Example:
        >>> state = create_initial_state("button")
        >>> print(state)
        {
            "user_input": "button",
            "component": None,
            "message": "",
            "error": None
        }
    """
    return AgentState(
        user_input=user_input,
        component=None,
        message="",
        error=None
    )


def create_error_state(user_input: str, error_message: str) -> AgentState:
    """
    Creates an error state when something goes wrong.

    Args:
        user_input (str): The original user input
        error_message (str): Description of the error

    Returns:
        AgentState: State with error field populated

    Example:
        >>> state = create_error_state("invalid", "Could not parse component")
        >>> print(state["error"])
        "Could not parse component"
    """
    return AgentState(
        user_input=user_input,
        component=None,
        message="",
        error=error_message
    )


# ============================================================================
# COMPONENT SCHEMAS (for LLM prompt)
# ============================================================================

# These define what components are available and their props
# The LLM will use these to generate valid component configurations

COMPONENT_SCHEMAS = {
    "Button": {
        "type": "Button",
        "props": {
            "label": "string (the button text)",
            "variant": "string (optional: 'primary', 'secondary', 'outline')"
        },
        "example": {
            "type": "Button",
            "props": {
                "label": "Click Me",
                "variant": "primary"
            }
        }
    },
    "TextArea": {
        "type": "TextArea",
        "props": {
            "placeholder": "string (optional placeholder text)",
            "rows": "number (optional, default: 4)"
        },
        "example": {
            "type": "TextArea",
            "props": {
                "placeholder": "Enter your text here...",
                "rows": 6
            }
        }
    },
    "CheckboxGroup": {
        "type": "CheckboxGroup",
        "props": {
            "options": "array of strings (the checkbox options)",
            "label": "string (optional label for the group)"
        },
        "example": {
            "type": "CheckboxGroup",
            "props": {
                "options": ["Apple", "Banana", "Orange"],
                "label": "Select fruits"
            }
        }
    },
    "Slider": {
        "type": "Slider",
        "props": {
            "min": "number (minimum value)",
            "max": "number (maximum value)",
            "defaultValue": "number (optional, default: midpoint)",
            "label": "string (optional label)"
        },
        "example": {
            "type": "Slider",
            "props": {
                "min": 0,
                "max": 100,
                "defaultValue": 50,
                "label": "Select a value"
            }
        }
    }
}


def get_component_schemas_text() -> str:
    """
    Returns a formatted string of component schemas for use in LLM prompts.

    This helps the LLM understand what components are available
    and how to structure the props.

    Returns:
        str: Formatted component schemas

    Example output:
        ```
        Available components:

        1. Button
           Props:
           - label: string (the button text)
           - variant: string (optional: 'primary', 'secondary', 'outline')
           Example:
           {
             "type": "Button",
             "props": { "label": "Click Me", "variant": "primary" }
           }

        2. TextArea
           ...
        ```
    """
    schemas_text = "Available components:\n\n"

    for i, (name, schema) in enumerate(COMPONENT_SCHEMAS.items(), 1):
        schemas_text += f"{i}. {name}\n"
        schemas_text += "   Props:\n"

        for prop_name, prop_desc in schema["props"].items():
            schemas_text += f"   - {prop_name}: {prop_desc}\n"

        schemas_text += f"   Example: {schema['example']}\n\n"

    return schemas_text


# ============================================================================
# EXPORT
# ============================================================================

__all__ = [
    "AgentState",
    "UIComponent",
    "PropalystState",
    "create_initial_state",
    "create_error_state",
    "create_propalyst_state",
    "COMPONENT_SCHEMAS",
    "get_component_schemas_text"
]
