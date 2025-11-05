"""
UI Extractor Node
==================

This node uses an LLM to understand natural language UI requests
and extract structured component configurations.

Key Concepts:
-------------
1. Node = Function that processes state
2. Takes AgentState as input
3. Returns updated AgentState as output
4. Uses LLM for natural language understanding
5. Extracts structured JSON from LLM response

Example Flow:
-------------
Input state:  { "user_input": "checkbox with options A, B, C" }
                     ↓
              [LLM Processing]
                     ↓
Output state: {
                "user_input": "checkbox with options A, B, C",
                "component": {
                  "type": "CheckboxGroup",
                  "props": { "options": ["A", "B", "C"] }
                },
                "message": "Here's a checkbox group"
              }
"""

import json
import os
from typing import Dict, Any
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from ..state import AgentState, UIComponent, get_component_schemas_text


# ============================================================================
# LLM SETUP
# ============================================================================

def get_llm():
    """
    Initialize and return the LLM instance.

    Uses environment variables:
    - OPENAI_API_KEY: Your OpenAI API key
    - LLM_MODEL: Model name (default: gpt-3.5-turbo)
    - LLM_TEMPERATURE: Temperature setting (default: 0.7)

    Returns:
        ChatOpenAI: Configured LLM instance

    Raises:
        ValueError: If OPENAI_API_KEY is not set
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError(
            "OPENAI_API_KEY not found in environment variables. "
            "Please set it in your .env file."
        )

    model = os.getenv("LLM_MODEL", "gpt-5-nano-2025-08-07")
    temperature = float(os.getenv("LLM_TEMPERATURE", "0.7"))

    print(f"🤖 Using OpenAI: {model}")

    return ChatOpenAI(
        api_key=api_key,
        model=model,
        temperature=temperature
    )


# ============================================================================
# PROMPT ENGINEERING
# ============================================================================

def create_extraction_prompt(user_input: str) -> list:
    """
    Creates the prompt messages for the LLM.

    This is critical for getting good results!

    The prompt:
    1. Explains the task clearly
    2. Lists available components with examples
    3. Specifies exact JSON format expected
    4. Provides the user's request

    Args:
        user_input (str): The user's UI component request

    Returns:
        list: List of LangChain message objects

    Example:
        >>> messages = create_extraction_prompt("button")
        >>> # LLM will see system instructions + user request
    """

    # System message: Instructions for the LLM
    system_prompt = f"""You are a UI component extraction specialist.

Your task: Extract structured component information from natural language requests.

{get_component_schemas_text()}

IMPORTANT RULES:
1. Return ONLY valid JSON, no other text
2. JSON must have "type" and "props" fields
3. "type" must be one of: Button, TextArea, CheckboxGroup, Slider
4. "props" must match the schema for that component type
5. If the request is unclear, make reasonable assumptions
6. For sliders, if defaultValue not specified, use the midpoint

RESPONSE FORMAT (JSON only):
{{
  "type": "ComponentType",
  "props": {{
    "prop1": "value1",
    "prop2": "value2"
  }}
}}

Examples:

Input: "show me a button"
Output: {{"type": "Button", "props": {{"label": "Click Me", "variant": "primary"}}}}

Input: "text area with placeholder 'Enter name'"
Output: {{"type": "TextArea", "props": {{"placeholder": "Enter name", "rows": 4}}}}

Input: "checkbox with options Apple, Banana, Orange"
Output: {{"type": "CheckboxGroup", "props": {{"options": ["Apple", "Banana", "Orange"], "label": "Select fruits"}}}}

Input: "slider from 0 to 100"
Output: {{"type": "Slider", "props": {{"min": 0, "max": 100, "defaultValue": 50, "label": "Select a value"}}}}

Now extract the component from the user's request."""

    # Human message: The actual user request
    human_prompt = f"Extract component from: {user_input}"

    return [
        SystemMessage(content=system_prompt),
        HumanMessage(content=human_prompt)
    ]


# ============================================================================
# JSON PARSING
# ============================================================================

def parse_llm_response(response_text: str) -> Dict[str, Any]:
    """
    Parse the LLM response and extract JSON.

    LLMs sometimes add extra text, so we need to:
    1. Find the JSON object in the response
    2. Parse it safely
    3. Validate the structure

    Args:
        response_text (str): Raw response from LLM

    Returns:
        dict: Parsed component configuration

    Raises:
        ValueError: If JSON is invalid or missing required fields

    Example:
        >>> text = '{"type": "Button", "props": {"label": "Click"}}'
        >>> result = parse_llm_response(text)
        >>> print(result)
        {'type': 'Button', 'props': {'label': 'Click'}}
    """
    try:
        # Try to find JSON in the response
        # LLM might return: "Here's the component: {json}"
        # We need to extract just the {json} part

        text = response_text.strip()

        # Find first { and last }
        start = text.find('{')
        end = text.rfind('}') + 1

        if start == -1 or end == 0:
            raise ValueError("No JSON object found in response")

        json_str = text[start:end]
        data = json.loads(json_str)

        # Validate required fields
        if "type" not in data:
            raise ValueError("Missing 'type' field in component")

        if "props" not in data:
            raise ValueError("Missing 'props' field in component")

        return data

    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in response: {e}")


# ============================================================================
# NODE FUNCTION (The actual LangGraph node)
# ============================================================================

async def extract_ui_component(state: AgentState) -> AgentState:
    """
    LangGraph node that extracts UI component info from user input.

    This is the main node function that:
    1. Takes current state
    2. Calls LLM to extract component info
    3. Parses the response
    4. Returns updated state

    Args:
        state (AgentState): Current state with user_input

    Returns:
        AgentState: Updated state with component information

    Flow:
        Input:  { "user_input": "button" }
                      ↓
                [Call LLM]
                      ↓
                [Parse JSON]
                      ↓
        Output: {
                  "user_input": "button",
                  "component": { "type": "Button", "props": {...} },
                  "message": "Here's a button"
                }

    Example:
        >>> state = {"user_input": "slider from 0 to 100"}
        >>> new_state = await extract_ui_component(state)
        >>> print(new_state["component"])
        UIComponent(type="Slider", props={"min": 0, "max": 100, ...})
    """

    print(f"\n🔍 [UI Extractor] Processing: {state['user_input']}")

    try:
        # Step 1: Get LLM instance
        llm = get_llm()

        # Step 2: Create prompt
        messages = create_extraction_prompt(state["user_input"])

        # Step 3: Call LLM
        print("📤 [UI Extractor] Calling LLM...")
        response = await llm.ainvoke(messages)
        response_text = response.content

        print(f"📥 [UI Extractor] LLM Response: {response_text}")

        # Step 4: Parse response
        component_data = parse_llm_response(response_text)

        # Step 5: Create UIComponent model
        component = UIComponent(**component_data)

        print(f"✅ [UI Extractor] Extracted: {component.type}")

        # Step 6: Return updated state
        return AgentState(
            user_input=state["user_input"],
            component=component,
            message=f"Here's a {component.type} component",
            error=None
        )

    except Exception as e:
        # Handle any errors gracefully
        error_message = f"Failed to extract component: {str(e)}"
        print(f"❌ [UI Extractor] Error: {error_message}")

        return AgentState(
            user_input=state["user_input"],
            component=None,
            message="",
            error=error_message
        )


# ============================================================================
# SYNCHRONOUS WRAPPER (for testing)
# ============================================================================

def extract_ui_component_sync(state: AgentState) -> AgentState:
    """
    Synchronous wrapper for testing purposes.

    LangGraph can work with both sync and async functions,
    but async is preferred for production.

    Args:
        state (AgentState): Current state

    Returns:
        AgentState: Updated state

    Example:
        >>> state = {"user_input": "button"}
        >>> result = extract_ui_component_sync(state)
        >>> print(result["component"].type)
        "Button"
    """
    import asyncio

    # Run the async function in a sync context
    return asyncio.run(extract_ui_component(state))


# ============================================================================
# EXPORT
# ============================================================================

__all__ = [
    "extract_ui_component",
    "extract_ui_component_sync",
    "get_llm",
    "create_extraction_prompt",
    "parse_llm_response"
]
