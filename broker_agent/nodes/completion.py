"""
Real Estate Agent Completion Node
===================================

Handles the completion state when all questions have been answered.
"""

from broker_agent.state import RealEstateAgentState


async def mark_conversation_complete(state: RealEstateAgentState) -> RealEstateAgentState:
    """
    Mark the conversation as complete and generate summary.

    This node runs when all questions have been answered.
    It returns a final message summarizing the user's preferences.
    """

    if state.get("completed"):
        return state

    # Build summary message
    summary_parts = []

    if state.get("transaction_type"):
        transaction = state["transaction_type"].capitalize()
        summary_parts.append(f"You're looking to {transaction.lower()} a property")

    if state.get("location"):
        summary_parts.append(f"in {state['location']}")

    if state.get("price_min") and state.get("price_max"):
        summary_parts.append(f"with budget ₹{state['price_min']}-{state['price_max']} lakhs")

    if state.get("area_min") and state.get("area_max"):
        summary_parts.append(f"and size {state['area_min']}-{state['area_max']} sq ft")

    if state.get("property_type"):
        summary_parts.append(f"property type: {state['property_type']}")

    summary = ". ".join(summary_parts) + "."

    features = state.get("special_features", [])
    features_text = ""
    if features:
        features_text = f"\n\nYour preferred features: {', '.join(features)}"

    final_message = f"Perfect! {summary}{features_text}\n\nOur team will search for properties matching your criteria and get back to you soon!"

    return {
        **state,
        "completed": True,
        "conversational_message": final_message,
        "current_question": None,
    }


__all__ = ["mark_conversation_complete"]
