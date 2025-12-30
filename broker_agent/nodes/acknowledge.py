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
import google.generativeai as genai
from pathlib import Path
import logging
import json

from ..state import RealEstateAgentState
from ..utils import clean_llm_response

logger = logging.getLogger(__name__)


# ============================================================================
# PROMPT LOADING
# ============================================================================

class AcknowledgmentPromptLoader:
    """Loads and caches the acknowledgment prompt template"""

    # UPDATED: Using v2 prompt with broker persona
    PROMPT_FILE = Path(__file__).parent.parent.parent / "prompts" / "broker_acknowledgment_v2.txt"
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
                # Fallback to old prompt if v2 not found
                try:
                    fallback_path = Path(__file__).parent.parent.parent / "prompts" / "acknowledgment.txt"
                    with open(fallback_path, "r") as f:
                        cls._cache = f.read()
                        logger.warning("Using fallback acknowledgment.txt prompt")
                except FileNotFoundError:
                    raise
        return cls._cache


# ============================================================================
# LLM INITIALIZATION
# ============================================================================

def _get_model():
    """Get or create Gemini model instance for acknowledgments"""
    return genai.GenerativeModel(
        model_name="gemini-2.5-flash-lite-preview-09-2025",
        generation_config=genai.types.GenerationConfig(
            temperature=0.7,
        ),
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
    elif question_id == "taste_preference":
        if isinstance(answer, list):
            return f"{len(answer)} properties selected"
        return str(answer)
    return str(answer)


def get_question_id_to_state_key_mapping() -> Dict[str, str]:
    """
    Map question IDs (from questions.py) to state field names.

    Question IDs are what appears in current_question["id"].
    State keys are the fields stored in RealEstateAgentState.

    Returns:
        Dict mapping question IDs to state keys
    """
    return {
        "req_type": "req_type",
        "proximity_location": "proximity_location",
        "budget": "price_min/price_max",  # Special: stores two fields
        "property_area": "area_min/area_max",  # Special: stores two fields
        "property_type": "property_type",
        "special_requests": "special_features",
        "taste_preference": "taste_preference",
    }


def build_conversation_context(state: Optional[Dict[str, Any]]) -> str:
    """
    Build a formatted conversation context string from state.

    Formats all answered questions in a human-readable way for LLM prompts.

    Args:
        state (Optional[Dict]): The conversation state

    Returns:
        str: Formatted context (e.g., "- Transaction: buying\n- Budget: ₹50-100Cr\n...")
             Returns "(Starting conversation)" if no context available
    """
    if not state:
        return "(Starting conversation)"

    context_parts = []

    # Transaction type
    if state.get("req_type"):
        transaction = "buying" if state["req_type"] == "buy" else "renting"
        context_parts.append(f"- Transaction: {transaction}")

    # Location
    if state.get("proximity_location"):
        location = _format_answer_display("proximity_location", state["proximity_location"])
        context_parts.append(f"- Location preference: {location}")

    # Budget
    if state.get("price_min") and state.get("price_max"):
        price = f"₹{state['price_min']:.1f}Cr - ₹{state['price_max']:.1f}Cr"
        context_parts.append(f"- Budget: {price}")

    # Property area
    if state.get("area_min") and state.get("area_max"):
        area = f"{state['area_min']:,} - {state['area_max']:,} sq ft"
        context_parts.append(f"- Size: {area}")

    # Property type
    if state.get("property_type"):
        prop_type = _format_answer_display("property_type", state["property_type"])
        context_parts.append(f"- Type: {prop_type}")

    # Special features
    if state.get("special_features"):
        features = state["special_features"]
        if isinstance(features, list):
            features_str = ", ".join([f.replace("_", " ").title() for f in features])
            context_parts.append(f"- Features: {features_str}")

    if not context_parts:
        return "(Starting conversation)"

    return "\n".join(context_parts)


def _build_acknowledgment_prompt(
    question_id: str,
    answer: Any,
    context: Optional[Dict[str, Any]] = None,
    next_question: Optional[str] = None,
) -> str:
    """
    Build a prompt for the LLM to generate a natural acknowledgment.

    Uses broker persona prompt to generate conversational responses.
    Generates ONLY the acknowledgment - the next question comes separately.

    Args:
        question_id (str): Which question is being acknowledged
        answer (Any): The user's answer
        context (Optional[Dict]): Additional context from state with previous answers
        next_question (Optional[str]): What the next question will be (for better transitions)

    Returns:
        str: Prompt for the LLM
    """

    # Format the user's answer for display
    formatted_answer = _format_answer_display(question_id, answer)

    # Build conversation context summary
    conversation_context = ""
    if context:
        if context.get("req_type"):
            transaction = "buying" if context["req_type"] == "buy" else "selling"
            conversation_context += f"- Transaction: {transaction}\n"

        if context.get("proximity_location"):
            location = _format_answer_display("proximity_location", context["proximity_location"])
            conversation_context += f"- Location preference: {location}\n"

        if context.get("price_min") and context.get("price_max"):
            price = f"₹{context['price_min']:.1f}Cr - ₹{context['price_max']:.1f}Cr"
            conversation_context += f"- Budget: {price}\n"

        if context.get("area_min") and context.get("area_max"):
            area = f"{context['area_min']:,} - {context['area_max']:,} sq ft"
            conversation_context += f"- Size: {area}\n"

        if context.get("property_type"):
            prop_type = _format_answer_display("property_type", context["property_type"])
            conversation_context += f"- Type: {prop_type}\n"

    if not conversation_context:
        conversation_context = "(Starting conversation)"

    # Build next question hint for transitions
    next_hint = f"Next we'll ask about {next_question}." if next_question else ""

    # Load broker persona prompt template
    template = AcknowledgmentPromptLoader.load()

    # Fill in template with context
    prompt = template.format(
        user_answer=formatted_answer,
        conversation_context=conversation_context,
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
    2. Reads decision_guidance from state (set by router)
    3. Calls LLM with broker persona to generate natural acknowledgment
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
        "Got it. Where are you looking?"
    """

    # If no pending answer, just return state as-is
    if not state.get("pending_answer") or not state.get("pending_question_id"):
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

        # Build prompt for LLM with context
        formatted_answer = _format_answer_display(state["pending_question_id"], state["pending_answer"])

        # Build conversation context string using shared utility
        conversation_context = build_conversation_context(context)

        # Get the CURRENT question that's already in state (what will be asked next)
        current_q = state.get("current_question")
        next_question = None

        if current_q and current_q.get("id"):
            q_id = current_q.get("id")
            # Map question ID (from questions.py) to human-readable text
            # These IDs must match the "id" field in each question from questions.py
            question_labels = {
                "req_type": "transaction type (buy or sell)",
                "proximity_location": "your preferred location",
                "budget": "your budget range",
                "property_area": "the property size or area",
                "property_type": "the property type you prefer",
                "special_requests": "special features or amenities",
            }
            next_question = question_labels.get(q_id)

        # Log what's being sent to the LLM
        print(f"\n📝 PROMPT INPUT:")
        print(f"   User's Answer: {formatted_answer}")
        print(f"   Context: {conversation_context.strip()}")
        if next_question:
            print(f"   Next Question: {next_question}")

        prompt = _build_acknowledgment_prompt(
            state["pending_question_id"],
            state["pending_answer"],
            context=context,
            next_question=next_question,
        )

        # Call LLM to generate acknowledgment and micro-interactions
        model = _get_model()
        response = await model.generate_content_async(prompt)
        response_text = clean_llm_response(response.text, format_type="json")

        # Parse JSON response
        try:
            result = json.loads(response_text)
            acknowledgment_text = result.get("acknowledgment_text", "Got it.")
            additional_type = result.get("additional_type", "none")
            additional_text = result.get("additional_text", "")

            # Log LLM response
            print(f"\n✅ LLM RESPONSE:")
            print(f"   📢 Acknowledgment: {acknowledgment_text}")
            if additional_type != "none":
                print(f"   {additional_type.upper()}: {additional_text}")

            # Validate additional_type
            if additional_type not in ["nudge", "comment", "insight", "none"]:
                additional_type = "none"
                additional_text = ""

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM JSON response: {e}")
            acknowledgment_text = "Got it."
            additional_type = "none"
            additional_text = ""

        # Update state with acknowledgment and micro-interactions
        state = {
            **state,
            "conversational_message": acknowledgment_text,
            "last_response_text": acknowledgment_text,
            "additional_type": additional_type,
            "additional_text": additional_text if additional_type != "none" else None,
            "pending_answer": None,
            "pending_question_id": None,
        }

        return state

    except Exception as e:
        logger.error(f"Error generating acknowledgment: {e}")
        print(f"   ❌ Error: {e}")

        # Fallback to minimal acknowledgment if LLM fails
        fallback_text = "Got it. Moving forward..."
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

__all__ = [
    "generate_acknowledgment",
    "build_conversation_context",
    "get_question_id_to_state_key_mapping",
]
