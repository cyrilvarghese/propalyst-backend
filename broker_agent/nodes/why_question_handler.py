"""
Why Question Handler Node
===========================

Handles asking "why" follow-up questions from the pending_whys queue.

This node:
1. Pops one question_id from pending_whys
2. Sets up state to ask why about that topic
3. Marks that we're asking a why question
4. Triggers the acknowledge node to generate the why question
"""

from typing import Dict, Any, Optional
import logging

from ..state import RealEstateAgentState

logger = logging.getLogger(__name__)

# Map question_id to state key where the answer is stored
QUESTION_ID_TO_STATE_KEY: Dict[str, str] = {
    "req_type": "req_type",
    "proximity_location": "proximity_location",
    "budget": "price_min",  # Use price_min as representative
    "property_area": "area_min",  # Use area_min as representative
    "property_type": "property_type",
    "special_features": "special_features",
}


async def handle_why_question(state: RealEstateAgentState) -> RealEstateAgentState:
    """
    Ask a "why" question about a pending topic from the queue.

    Flow:
    1. Check if pending_whys queue is empty
    2. Pop first question_id from pending_whys
    3. Get the user's original answer for this question from state
    4. Set pending fields to trigger acknowledge node
    5. Mark that we're asking a why question (prevents nested whys)
    6. Return updated state (acknowledge node will be called next)

    Args:
        state (RealEstateAgentState): Current conversation state with pending_whys queue

    Returns:
        RealEstateAgentState: Updated state ready for acknowledge node to generate why question
    """

    pending_whys = list(state.get("pending_whys", []))

    # If no pending whys, shouldn't be here - return as-is
    if not pending_whys:
        logger.warning("why_question_handler called with empty pending_whys")
        return state

    # Pop first why question to ask
    why_question_id = pending_whys.pop(0)
    print(f"🤔 Asking why about: {why_question_id}")
    print(f"   Remaining pending_whys: {pending_whys}")

    # Get the user's original answer for this question
    state_key = QUESTION_ID_TO_STATE_KEY.get(why_question_id)
    original_answer = state.get(state_key) if state_key else None

    if not original_answer:
        logger.warning(f"Could not find original answer for {why_question_id}")
        # Skip this why and continue to next
        state["pending_whys"] = pending_whys
        return state

    # Set up state to ask why about this answer
    # This triggers acknowledge node to generate a why question
    # Get the reason if it was stored by the router
    why_reasons = state.get("why_reasons", {})
    why_reason = why_reasons.get(why_question_id, "")

    state = {
        **state,
        "pending_whys": pending_whys,
        "pending_answer": original_answer,
        "pending_question_id": why_question_id,
        "is_asking_why": True,  # Flag that we're asking a why (not answering a why)
        "decision_guidance": {
            "ask_why": True,  # Tell acknowledge node to ask why
            "topic": why_question_id,
            "why_reason": why_reason,  # The multiple paths this answer could take
            "why_mode": True,  # Indicate we're in why-asking mode
        },
    }

    print(f"✅ Set up to ask why about {why_question_id}")
    print(f"   Original answer: {original_answer}")
    print(f"   Why reason: {why_reason if why_reason else '(no specific reason stored)'}")
    print(f"   is_asking_why: True (prevent nested whys)")

    return state


__all__ = ["handle_why_question"]
