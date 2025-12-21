"""
Acknowledgment Node - LLM-based Response Generation
====================================================

Generates dynamic acknowledgment responses to user answers using an LLM.

This node:
1. Takes the pending answer and question ID from state
2. Calls the LLM to generate a contextual acknowledgment
3. Updates the conversational_message and last_response_text in state
4. Clears the pending fields
"""

from typing import Dict, Any, Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from pathlib import Path
import logging

from ..state import RealEstateAgentState

logger = logging.getLogger(__name__)


# ============================================================================
# PROMPT LOADING
# ============================================================================

class AcknowledgmentPromptLoader:
    """Loads and caches the acknowledgment prompt template"""

    PROMPT_FILE = Path(__file__).parent.parent.parent / "prompts" / "acknowledgment.txt"
    _cache: Optional[str] = None

    @classmethod
    def load(cls) -> str:
        """Load prompt template from file (with caching)"""
        if cls._cache is None:
            try:
                with open(cls.PROMPT_FILE, "r") as f:
                    cls._cache = f.read()
            except FileNotFoundError:
                logger.error(f"Prompt file not found: {cls.PROMPT_FILE}")
                raise
        return cls._cache


# ============================================================================
# LLM INITIALIZATION
# ============================================================================

def _get_llm():
    """Get or create ChatGoogleGenerativeAI instance for acknowledgments"""
    return ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        temperature=0.7,
        timeout=10,
    )


# ============================================================================
# ACKNOWLEDGMENT PROMPT
# ============================================================================

def _format_answer_display(question_id: str, answer: Any) -> str:
    """Format an answer for display in conversation context."""
    if question_id == "req_type":
        return "Buying" if answer == "buy" else "Selling"
    elif question_id == "proximity_location":
        return answer.replace("_", " ").title()
    elif question_id == "budget":
        if isinstance(answer, list) and len(answer) == 2:
            return f"₹{answer[0]:.1f}Cr - ₹{answer[1]:.1f}Cr"
        return str(answer)
    elif question_id == "property_area":
        if isinstance(answer, list) and len(answer) == 2:
            return f"{answer[0]:,} - {answer[1]:,} sq ft"
        return str(answer)
    elif question_id == "property_type":
        return answer.title()
    elif question_id == "special_requests":
        if isinstance(answer, list):
            return ", ".join([item.replace("_", " ").title() for item in answer])
        return str(answer)
    return str(answer)


def _build_acknowledgment_prompt(
    question_id: str,
    answer: Any,
    context: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Build a prompt for the LLM to generate a natural acknowledgment.

    Uses the prompt template from prompts/acknowledgment.txt and fills in
    the conversation context and answer details.

    Args:
        question_id (str): Which question is being acknowledged
        answer (Any): The user's answer
        context (Optional[Dict]): Additional context from state with previous answers

    Returns:
        str: Prompt for the LLM
    """

    # Build conversation summary from context
    conversation_so_far = ""
    if context:
        if context.get("req_type"):
            transaction = "buying" if context["req_type"] == "buy" else "selling"
            conversation_so_far += f"- Looking to: {transaction}\n"

        if context.get("proximity_location"):
            location = _format_answer_display("proximity_location", context["proximity_location"])
            conversation_so_far += f"- Proximity preference: {location}\n"

        if context.get("price_min") and context.get("price_max"):
            price = f"₹{context['price_min']:.1f}Cr - ₹{context['price_max']:.1f}Cr"
            conversation_so_far += f"- Budget: {price}\n"

        if context.get("area_min") and context.get("area_max"):
            area = f"{context['area_min']:,} - {context['area_max']:,} sq ft"
            conversation_so_far += f"- Property size: {area}\n"

        if context.get("property_type"):
            prop_type = _format_answer_display("property_type", context["property_type"])
            conversation_so_far += f"- Property type: {prop_type}\n"

    # Default to starting conversation if no history
    if not conversation_so_far:
        conversation_so_far = "(Starting conversation)"

    formatted_answer = _format_answer_display(question_id, answer)

    # Question-specific context for natural transitions
    next_question_hints = {
        "req_type": "After understanding their transaction intent, the next step is understanding location preferences.",
        "proximity_location": "After understanding location preference, the next step is discussing budget.",
        "budget": "After understanding budget, the next step is the property size/area requirements.",
        "property_area": "After understanding size, the next step is the type of property they prefer.",
        "property_type": "After understanding property type, the next step is understanding any special features they want.",
        "special_requests": "All key preferences have been discussed. Time to wrap up and show matching properties.",
    }

    next_hint = next_question_hints.get(question_id, "")

    # Load prompt template from file
    template = AcknowledgmentPromptLoader.load()

    # Fill in template variables
    prompt = template.format(
        conversation_so_far=conversation_so_far,
        formatted_answer=formatted_answer,
        next_hint=next_hint,
    )

    return prompt


# ============================================================================
# ACKNOWLEDGMENT NODE
# ============================================================================

async def generate_acknowledgment(state: RealEstateAgentState) -> RealEstateAgentState:
    """
    Generate an LLM acknowledgment for the pending answer.

    This node:
    1. Takes the pending_answer and pending_question_id from state
    2. Calls ChatOpenAI to generate a dynamic, natural acknowledgment
    3. Considers all previous answers to make it contextual
    4. Updates conversational_message with the acknowledgment
    5. Stores it in last_response_text
    6. Clears pending fields

    Args:
        state (RealEstateAgentState): Current conversation state with pending answer

    Returns:
        RealEstateAgentState: Updated state with acknowledgment text

    Example:
        >>> state = create_real_estate_state("session-123")
        >>> state["pending_answer"] = "buy"
        >>> state["pending_question_id"] = "req_type"
        >>> result = await generate_acknowledgment(state)
        >>> print(result["last_response_text"])
        "Looking to buy? That's great - let's find you something perfect..."
    """

    print(f"\n🤖 LLM: Generating acknowledgment...")
    print(f"   Question: {state.get('pending_question_id')}")
    print(f"   Answer: {state.get('pending_answer')}")

    # If no pending answer, just return state as-is
    if not state.get("pending_answer") or not state.get("pending_question_id"):
        print("   ⚠️ No pending answer to acknowledge, returning as-is")
        return state

    try:
        # Build full conversation context for LLM
        context = {
            "req_type": state.get("req_type"),
            "proximity_location": state.get("proximity_location"),
            "price_min": state.get("price_min"),
            "price_max": state.get("price_max"),
            "area_min": state.get("area_min"),
            "area_max": state.get("area_max"),
            "property_type": state.get("property_type"),
            "special_features": state.get("special_features"),
        }

        # Build prompt for LLM with full context
        prompt = _build_acknowledgment_prompt(
            state["pending_question_id"],
            state["pending_answer"],
            context=context,
        )

        # Call LLM to generate acknowledgment
        llm = _get_llm()
        response = await llm.ainvoke(prompt)
        acknowledgment_text = response.content.strip()

        print(f"   ✅ Generated: {acknowledgment_text[:80]}...")

        # Update state with acknowledgment
        state = {
            **state,
            "conversational_message": acknowledgment_text,
            "last_response_text": acknowledgment_text,
            "pending_answer": None,
            "pending_question_id": None,
        }

        return state

    except Exception as e:
        logger.error(f"Error generating acknowledgment: {e}")
        print(f"   ❌ Error: {e}")

        # Fallback to minimal acknowledgment if LLM fails
        fallback_text = "Got it! Moving forward..."
        state = {
            **state,
            "conversational_message": fallback_text,
            "last_response_text": fallback_text,
            "pending_answer": None,
            "pending_question_id": None,
            "error": f"Acknowledgment generation failed: {str(e)}",
        }

        return state


# ============================================================================
# EXPORT
# ============================================================================

__all__ = ["generate_acknowledgment"]
