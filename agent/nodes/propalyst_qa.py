"""
Propalyst Q&A Nodes
===================

This module contains nodes for the Propalyst conversational flow.

Unlike ui_extractor.py (Project 1) which extracts UI components,
these nodes handle natural language Q&A for property search.

Two types of processing:
1. UI Generation: Decide which input component to show (TextInput, ButtonGroup, etc.)
2. Answer Parsing: Extract structured data from user's natural language answer

Flow:
-----
Node asks question → Shows UI component → User answers → Parse answer → Update state
"""

import re
import os
import json
from typing import Dict, Any
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from ..state import PropalystState, UIComponent


def get_llm():
    """
    Initialize and return the LLM instance (same pattern as ui_extractor.py).

    Uses environment variables:
    - OPENAI_API_KEY: Your OpenAI API key
    - LLM_MODEL: Model name (default: gpt-4o-mini)
    - LLM_TEMPERATURE: Temperature setting (default: 0.3 for validation)
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError(
            "OPENAI_API_KEY not found in environment variables. "
            "Please set it in your .env file."
        )

    model = os.getenv("LLM_MODEL", "gpt-4o-mini")
    temperature = float(os.getenv("LLM_TEMPERATURE", "0.3"))

    return ChatOpenAI(
        api_key=api_key,
        model=model,
        temperature=temperature,
        model_kwargs={"response_format": {"type": "json_object"}}
    )


# ============================================================================
# LLM VALIDATION
# ============================================================================

async def validate_answer_with_llm(field: str, user_input: str, state: PropalystState) -> Dict[str, Any]:
    """
    Use LLM to intelligently validate and extract user answers.

    Args:
        field: Which field is being answered (work_location, has_kids, etc.)
        user_input: Raw user input
        state: Current state (for context)

    Returns:
        {
            "valid": bool,
            "extracted_value": Any or None,
            "message": str (contextual response from LLM)
        }
    """

    # Build field-specific validation prompts
    if field == "work_location":
        prompt = f"""You are helping a user find rental properties in Bangalore, India.

The user said: "{user_input}"

Is this a valid Bangalore neighborhood/area/location?

Valid examples: Whitefield, Koramangala, Indiranagar, MG Road, HSR Layout, Electronic City, Marathahalli, BTM Layout, Jayanagar, JP Nagar, Malleshwaram, Rajajinagar, Yelahanka, etc.

Invalid examples: ABCD, xyz, random text, numbers, non-Bangalore locations

Respond in JSON format:
{{
    "valid": true or false,
    "extracted_value": "Proper Case Location Name" or null,
    "message": "Your contextual response"
}}

If VALID:
- Set valid=true
- Set extracted_value to the proper case name (e.g., "whitefield" → "Whitefield")
- Message: Acknowledge naturally with a positive comment about the area (e.g., "Great! Whitefield is a tech hub with excellent connectivity.")

If INVALID:
- Set valid=false
- Set extracted_value=null
- Message: Politely say you don't recognize it and give 3-4 example areas they could try."""

    elif field == "has_kids":
        prompt = f"""Extract a yes/no answer from the user's response.

User said: "{user_input}"

Determine if they have kids or not.

Examples:
- "Yes" → true
- "No" → false
- "I have 2 kids" → true
- "Yeah I do" → true
- "Nope" → false
- "Don't have any" → false

Respond in JSON:
{{
    "valid": true,
    "extracted_value": true or false,
    "message": "Natural acknowledgment"
}}

Message examples:
- If true: "Perfect! Having kids means we'll prioritize areas with good schools and family-friendly amenities."
- If false: "Got it! We'll focus on areas that match your lifestyle preferences."

Always set valid=true for this field since any response can be interpreted."""

    elif field == "commute_time_max":
        prompt = f"""Extract commute time in minutes from user input.

User said: "{user_input}"

Convert to minutes (integer).

Examples:
- "30 minutes" → 30
- "45 min" → 45
- "1 hour" → 60
- "around 20" → 20
- "half an hour" → 30

Respond in JSON:
{{
    "valid": true or false,
    "extracted_value": integer (minutes) or null,
    "message": "Contextual acknowledgment"
}}

If you can extract a reasonable time (5-120 minutes): valid=true
If unclear or unreasonable: valid=false, ask for clarification

Message should acknowledge the commute preference naturally."""

    elif field == "property_type":
        prompt = f"""Determine property type from user input.

User said: "{user_input}"

Map to one of: "Villa", "Apartment", "Row House"

Mappings:
- Villa: villa, independent house, house, standalone
- Apartment: apartment, flat, condo
- Row House: row house, townhouse, duplex

Respond in JSON:
{{
    "valid": true or false,
    "extracted_value": "Villa" or "Apartment" or "Row House" or null,
    "message": "Natural acknowledgment"
}}

If you can map it: valid=true
If unclear: valid=false, ask user to choose from the 3 types

Message should acknowledge their choice with a brief positive comment."""

    elif field == "budget_max":
        prompt = f"""Extract monthly rental budget in rupees from user input.

User said: "{user_input}"

Convert to integer (rupees).

Examples:
- "80000" → 80000
- "80k" → 80000
- "1.5 lakh" → 150000
- "₹75000" → 75000
- "50 thousand" → 50000

Respond in JSON:
{{
    "valid": true or false,
    "extracted_value": integer (rupees) or null,
    "message": "Contextual acknowledgment"
}}

If you can extract a reasonable budget (10000-500000): valid=true
If unclear: valid=false, ask for clarification

Message should acknowledge the budget naturally."""

    else:
        # Fallback for unknown field
        return {
            "valid": False,
            "extracted_value": None,
            "message": f"Unknown field: {field}"
        }

    try:
        # Get LLM instance
        llm = get_llm()

        # Create LangChain messages
        messages = [
            SystemMessage(content="You are a helpful assistant validating user input for a property search app. Always respond with valid JSON."),
            HumanMessage(content=prompt)
        ]

        # Call LLM using LangChain (async)
        response = await llm.ainvoke(messages)
        result = json.loads(response.content)
        return result

    except Exception as e:
        print(f"   ⚠️  LLM validation error: {e}")
        # Fallback to accepting the input
        return {
            "valid": True,
            "extracted_value": user_input,
            "message": "Thank you! Let's continue."
        }


# ============================================================================
# ANSWER PARSING HELPERS (Legacy - kept as fallback)
# ============================================================================

def parse_work_location(user_input: str) -> str:
    """
    Parse work location from user input.

    Simple approach: Just return what user typed.
    We trust user to enter a valid location name.

    Args:
        user_input: Raw user input (e.g., "Whitefield", "Koramangala", "MG Road")

    Returns:
        str: Cleaned location name

    Examples:
        >>> parse_work_location("Whitefield")
        "Whitefield"
        >>> parse_work_location("  koramangala  ")
        "Koramangala"
    """
    return user_input.strip().title()  # Capitalize first letter


def parse_kids_answer(user_input: str) -> bool:
    """
    Parse yes/no answer about kids.

    Args:
        user_input: Raw user input (e.g., "Yes", "No", "Yeah", "Nope")

    Returns:
        bool: True if user has kids, False otherwise

    Examples:
        >>> parse_kids_answer("Yes")
        True
        >>> parse_kids_answer("no")
        False
        >>> parse_kids_answer("Yeah I do")
        True
    """
    normalized = user_input.lower().strip()

    # Positive indicators
    if any(word in normalized for word in ["yes", "yeah", "yep", "yup", "true", "have"]):
        return True

    # Negative indicators
    if any(word in normalized for word in ["no", "nope", "nah", "false", "don't", "do not"]):
        return False

    # Default: assume no
    return False


def parse_commute_time(user_input: str) -> int:
    """
    Parse commute time from user input.

    Extracts numbers from text like:
    - "30 minutes"
    - "around 45 min"
    - "1 hour" (converts to 60)

    Args:
        user_input: Raw user input

    Returns:
        int: Commute time in minutes

    Examples:
        >>> parse_commute_time("30 minutes")
        30
        >>> parse_commute_time("1 hour")
        60
        >>> parse_commute_time("45")
        45
    """
    normalized = user_input.lower().strip()

    # Check for hours
    hour_match = re.search(r'(\d+)\s*h(?:our|r)?', normalized)
    if hour_match:
        hours = int(hour_match.group(1))
        return hours * 60

    # Extract first number
    number_match = re.search(r'(\d+)', normalized)
    if number_match:
        return int(number_match.group(1))

    # Default: 30 minutes
    return 30


def parse_property_type(user_input: str) -> str:
    """
    Parse property type from user input.

    Maps user input to standard property types:
    - Villa
    - Apartment
    - Row House

    Args:
        user_input: Raw user input

    Returns:
        str: Standard property type

    Examples:
        >>> parse_property_type("Villa")
        "Villa"
        >>> parse_property_type("apartment")
        "Apartment"
        >>> parse_property_type("independent house")
        "Villa"
    """
    normalized = user_input.lower().strip()

    # Map variations
    if any(word in normalized for word in ["villa", "independent", "house"]):
        return "Villa"
    elif any(word in normalized for word in ["row", "townhouse"]):
        return "Row House"
    else:
        return "Apartment"  # Default


def parse_budget(user_input: str) -> int:
    """
    Parse budget from user input.

    Handles formats like:
    - "80000"
    - "80k"
    - "1.5 lakh"
    - "₹75000"

    Args:
        user_input: Raw user input

    Returns:
        int: Budget in rupees

    Examples:
        >>> parse_budget("80000")
        80000
        >>> parse_budget("80k")
        80000
        >>> parse_budget("1.5 lakh")
        150000
    """
    normalized = user_input.lower().strip()

    # Remove currency symbols
    normalized = normalized.replace('₹', '').replace('rs', '').strip()

    # Handle "lakh" (1 lakh = 100,000)
    lakh_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:lakh|lac)', normalized)
    if lakh_match:
        lakhs = float(lakh_match.group(1))
        return int(lakhs * 100000)

    # Handle "k" (thousand)
    k_match = re.search(r'(\d+)\s*k', normalized)
    if k_match:
        thousands = int(k_match.group(1))
        return thousands * 1000

    # Extract plain number
    number_match = re.search(r'(\d+)', normalized)
    if number_match:
        return int(number_match.group(1))

    # Default: 50000
    return 50000


# ============================================================================
# Q&A NODES
# ============================================================================

async def ask_work_location(state: PropalystState) -> PropalystState:
    """
    Q1: Ask where user works.

    If already answered, skip this node.
    For text questions like this, NO UI component needed - use chat box only.
    """

    # Already answered? Skip
    if state.get("work_location"):
        print(f"   ✅ Already have work_location: {state['work_location']}")
        return state

    print("   📍 Asking for work location (chat box only)...")

    # Check if there's an error message from validation (invalid input)
    existing_message = state.get("message", "")
    error = state.get("error", None)

    # If there's an error message from LLM validation, preserve it!
    if error and existing_message and len(existing_message) > 20:
        message = existing_message
        print(f"   💬 Using LLM error message: {message}")
    else:
        # No error, use initial greeting
        message = "Hi! Let me help you find your perfect home. Where do you work?"
        print(f"   📝 Using initial message")

    return {
        **state,
        "component": None,  # No UI component - use chat box
        "message": message,
        "current_step": 1
    }


async def ask_kids(state: PropalystState) -> PropalystState:
    """
    Q2: Ask if user has kids.

    Shows ButtonGroup with Yes/No options.
    """

    # Already answered? Skip
    if state.get("has_kids") is not None:
        print(f"   ✅ Already have has_kids: {state['has_kids']}")
        return state

    print("   👶 Asking about kids...")

    # The question to ask
    question = "Do you have kids?"

    # Check if there's a previous LLM acknowledgment message
    prev_message = state.get("message", "")

    # If there's a previous message (LLM acknowledgment), send both separated by "|||"
    if prev_message and len(prev_message) > 10 and "Do you" not in prev_message:
        # Combine: acknowledgment ||| question
        combined_message = f"{prev_message}|||{question}"
        print(f"   💬 Sending both: acknowledgment + question")
    else:
        combined_message = question
        print(f"   📝 Message: {question}")

    # Append question message to conversation history
    messages = state.get("messages", [])
    messages = messages + [{"role": "agent", "content": question}]

    return {
        **state,
        "component": UIComponent(
            type="ButtonGroup",
            props={
                "field": "has_kids",
                "options": ["Yes", "No"]
            }
        ),
        "message": combined_message,
        "messages": messages,
        "current_step": 2
    }


async def ask_commute(state: PropalystState) -> PropalystState:
    """
    Q3: Ask about ideal commute time.

    Shows ButtonGroup with preset time options.
    Context-aware: Uses work_location in message.
    """

    # Already answered? Skip
    if state.get("commute_time_max"):
        print(f"   ✅ Already have commute_time_max: {state['commute_time_max']}")
        return state

    print("   🚗 Asking about commute time...")

    # The question to ask
    work_location = state.get("work_location", "work")
    question = f"What's your ideal commute time to {work_location}?"

    # Check if there's a previous LLM acknowledgment message
    prev_message = state.get("message", "")

    # If there's a previous message (LLM acknowledgment), send both separated by "|||"
    if prev_message and len(prev_message) > 10 and "commute" not in prev_message.lower():
        # Combine: acknowledgment ||| question
        combined_message = f"{prev_message}|||{question}"
        print(f"   💬 Sending both: acknowledgment + question")
    else:
        combined_message = question
        print(f"   📝 Message: {question}")

    # Append question message to conversation history
    messages = state.get("messages", [])
    messages = messages + [{"role": "agent", "content": question}]

    return {
        **state,
        "component": UIComponent(
            type="ButtonGroup",
            props={
                "field": "commute_time_max",
                "options": ["15 min", "30 min", "45 min", "60 min"]
            }
        ),
        "message": combined_message,
        "messages": messages,
        "current_step": 3
    }


async def ask_property_type(state: PropalystState) -> PropalystState:
    """
    Q4: Ask about property type preference.

    Shows ButtonGroup with property types.
    """

    # Already answered? Skip
    if state.get("property_type"):
        print(f"   ✅ Already have property_type: {state['property_type']}")
        return state

    print("   🏠 Asking about property type...")

    # The question to ask
    question = "What type of property are you looking for?"

    # Check if there's a previous LLM acknowledgment message
    prev_message = state.get("message", "")

    # If there's a previous message (LLM acknowledgment), send both separated by "|||"
    if prev_message and len(prev_message) > 10 and "property" not in prev_message.lower():
        # Combine: acknowledgment ||| question
        combined_message = f"{prev_message}|||{question}"
        print(f"   💬 Sending both: acknowledgment + question")
    else:
        combined_message = question
        print(f"   📝 Message: {question}")

    # Append question message to conversation history
    messages = state.get("messages", [])
    messages = messages + [{"role": "agent", "content": question}]

    return {
        **state,
        "component": UIComponent(
            type="ButtonGroup",
            props={
                "field": "property_type",
                "options": ["Villa", "Apartment", "Row House"]
            }
        ),
        "message": combined_message,
        "messages": messages,
        "current_step": 4
    }


async def ask_budget(state: PropalystState) -> PropalystState:
    """
    Q5: Ask about monthly budget.

    Shows Slider component for budget selection.
    """

    # Already answered? Skip
    if state.get("budget_max"):
        print(f"   ✅ Already have budget_max: {state['budget_max']}")
        return state

    print("   💰 Asking about budget...")

    # The question to ask
    question = "What's your monthly rental budget?"

    # Check if there's a previous LLM acknowledgment message
    prev_message = state.get("message", "")

    # If there's a previous message (LLM acknowledgment), send both separated by "|||"
    if prev_message and len(prev_message) > 10 and "budget" not in prev_message.lower():
        # Combine: acknowledgment ||| question
        combined_message = f"{prev_message}|||{question}"
        print(f"   💬 Sending both: acknowledgment + question")
    else:
        combined_message = question
        print(f"   📝 Message: {question}")

    # Append question message to conversation history
    messages = state.get("messages", [])
    messages = messages + [{"role": "agent", "content": question}]

    return {
        **state,
        "component": UIComponent(
            type="Slider",
            props={
                "field": "budget_max",
                "min": 20000,
                "max": 150000,
                "step": 5000,
                "defaultValue": 75000,
                "label": "What's your monthly budget?",
                "format": "₹{value}"
            }
        ),
        "message": combined_message,
        "messages": messages,
        "current_step": 5
    }


# ============================================================================
# ANSWER PROCESSING
# ============================================================================

async def process_user_answer(state: PropalystState, field: str, user_input: str) -> PropalystState:
    """
    Process user's answer with intelligent LLM validation.

    This function:
    1. Validates the answer using LLM (semantic understanding)
    2. If invalid: Returns error message, doesn't update state (user stays on same question)
    3. If valid: Extracts value, updates state, moves to next question

    Args:
        state: Current state
        field: Which field is being answered (e.g., "work_location", "has_kids")
        user_input: Raw user input

    Returns:
        Updated state with parsed value (if valid) or error message (if invalid)

    Examples:
        Valid input:
        >>> state = process_user_answer(state, "work_location", "Whitefield")
        >>> state["work_location"]  # ✅ "Whitefield"

        Invalid input:
        >>> state = process_user_answer(state, "work_location", "ABCD")
        >>> state["work_location"]  # ❌ Still None
        >>> state["message"]  # "I don't recognize 'ABCD'..."
    """

    print(f"   🔄 Processing answer for field: {field}")
    print(f"   📝 User input: {user_input}")

    # ✨ NEW: Validate with LLM first
    print(f"   🤖 Validating with LLM...")
    validation = await validate_answer_with_llm(field, user_input, state)

    if not validation["valid"]:
        # ❌ Invalid answer - don't update state, return error message
        print(f"   ❌ Invalid answer!")
        print(f"   💬 LLM message: {validation['message']}")

        return {
            **state,
            "message": validation["message"],
            "error": "Invalid input - please try again"
        }

    # ✅ Valid answer - extract value and update state
    value = validation["extracted_value"]
    llm_message = validation["message"]

    print(f"   ✅ Valid! Extracted value: {value}")
    print(f"   💬 LLM message: {llm_message}")

    # Update state based on field
    if field == "work_location":
        state["work_location"] = value
    elif field == "has_kids":
        state["has_kids"] = value
    elif field == "commute_time_max":
        state["commute_time_max"] = value
    elif field == "property_type":
        state["property_type"] = value
    elif field == "budget_max":
        state["budget_max"] = value
    else:
        print(f"   ⚠️  Unknown field: {field}")
        return state

    # Add to message history
    messages = list(state.get("messages", []))
    # Add user's answer
    messages.append({"role": "user", "content": user_input})
    # Add LLM acknowledgment
    messages.append({"role": "agent", "content": llm_message})

    # Use LLM-generated contextual message
    return {
        **state,
        "messages": messages,
        "message": llm_message,
        "error": None  # Clear any previous errors
    }


# ============================================================================
# EXPORT
# ============================================================================

__all__ = [
    "ask_work_location",
    "ask_kids",
    "ask_commute",
    "ask_property_type",
    "ask_budget",
    "process_user_answer"
]
