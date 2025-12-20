"""
Real Estate Agent - Interactive API Demo
=========================================

Interactive script that demonstrates the broker agent API.
Shows JSON responses at each step of the conversation.

Run with: python interactive_broker_agent_demo.py
"""

import asyncio
import json
from broker_agent.service import RealEstateAgentService
from broker_agent.state import create_real_estate_state


def print_header(title: str):
    """Print a formatted header"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")


def print_json(data, label: str = ""):
    """Pretty print JSON data"""
    if label:
        print(f"\n📋 {label}:")
    print(json.dumps(data, indent=2, default=str))


def print_state(state, label: str = ""):
    """Print relevant state fields as JSON"""
    relevant_state = {
        "session_id": state.get("session_id"),
        "current_question_id": state.get("current_question_id"),
        "transaction_type": state.get("transaction_type"),
        "location": state.get("location"),
        "price_min": state.get("price_min"),
        "price_max": state.get("price_max"),
        "area_min": state.get("area_min"),
        "area_max": state.get("area_max"),
        "property_type": state.get("property_type"),
        "special_features": state.get("special_features"),
        "completed": state.get("completed"),
    }
    print_json(relevant_state, label)


async def main():
    """Interactive demo of the broker agent"""

    print_header("REAL ESTATE AGENT - INTERACTIVE API DEMO")

    # ========================================================================
    # STEP 1: CREATE SESSION
    # ========================================================================

    print("📍 STEP 1: Creating a new session...")
    print("-" * 80)

    session_id = RealEstateAgentService.create_session()
    print(f"✅ Session created: {session_id}\n")

    state = RealEstateAgentService.create_initial_state(session_id)
    print_state(state, "Initial State")

    # ========================================================================
    # STEP 2: GET FIRST QUESTION
    # ========================================================================

    print_header("STEP 2: Getting first question")

    state = await RealEstateAgentService.get_next_question(state)

    print_json(state["current_question"], "Current Question")
    print(f"\n💬 Agent: {state['conversational_message']}")
    print_state(state, "State After Getting Question")

    # ========================================================================
    # STEP 3: ANSWER Q1 - TRANSACTION TYPE
    # ========================================================================

    print_header("STEP 3: Answer Q1 - Transaction Type")

    user_input = "buy"
    print(f"👤 User answers: {user_input}")

    state = await RealEstateAgentService.process_user_input(
        state, user_input, "transaction_type"
    )

    print_json(state["current_question"], "Next Question")
    print(f"\n💬 Agent: {state['conversational_message']}")
    print_state(state, "State After Q1")

    user_summary = RealEstateAgentService.get_user_summary(state)
    print_json(user_summary, "User Summary So Far")

    # ========================================================================
    # STEP 4: ANSWER Q2 - LOCATION
    # ========================================================================

    print_header("STEP 4: Answer Q2 - Location")

    user_input = "Indiranagar"
    print(f"👤 User answers: {user_input}")

    state = await RealEstateAgentService.process_user_input(
        state, user_input, "location"
    )

    print_json(state["current_question"], "Next Question")
    print(f"\n💬 Agent: {state['conversational_message']}")
    print_state(state, "State After Q2")

    user_summary = RealEstateAgentService.get_user_summary(state)
    print_json(user_summary, "User Summary So Far")

    # ========================================================================
    # STEP 5: ANSWER Q3 - PRICE RANGE
    # ========================================================================

    print_header("STEP 5: Answer Q3 - Price Range (in lakhs)")

    user_input = {"min": 50.0, "max": 100.0}
    print(f"👤 User answers: {json.dumps(user_input)}")

    state = await RealEstateAgentService.process_user_input(
        state, user_input, "price_range"
    )

    print_json(state["current_question"], "Next Question")
    print(f"\n💬 Agent: {state['conversational_message']}")
    print_state(state, "State After Q3")

    user_summary = RealEstateAgentService.get_user_summary(state)
    print_json(user_summary, "User Summary So Far")

    # ========================================================================
    # STEP 6: ANSWER Q4 - PROPERTY AREA
    # ========================================================================

    print_header("STEP 6: Answer Q4 - Property Area (in sq ft)")

    user_input = {"min": 1000, "max": 2500}
    print(f"👤 User answers: {json.dumps(user_input)}")

    state = await RealEstateAgentService.process_user_input(
        state, user_input, "property_area"
    )

    print_json(state["current_question"], "Next Question")
    print(f"\n💬 Agent: {state['conversational_message']}")
    print_state(state, "State After Q4")

    user_summary = RealEstateAgentService.get_user_summary(state)
    print_json(user_summary, "User Summary So Far")

    # ========================================================================
    # STEP 7: ANSWER Q5 - PROPERTY TYPE
    # ========================================================================

    print_header("STEP 7: Answer Q5 - Property Type")

    user_input = "apartment"
    print(f"👤 User answers: {user_input}")

    state = await RealEstateAgentService.process_user_input(
        state, user_input, "property_type"
    )

    print_json(state["current_question"], "Next Question")
    print(f"\n💬 Agent: {state['conversational_message']}")
    print_state(state, "State After Q5")

    user_summary = RealEstateAgentService.get_user_summary(state)
    print_json(user_summary, "User Summary So Far")

    # ========================================================================
    # STEP 8: ANSWER Q6 - SPECIAL FEATURES
    # ========================================================================

    print_header("STEP 8: Answer Q6 - Special Features")

    user_input = ["gym", "pool", "parking", "security"]
    print(f"👤 User answers: {json.dumps(user_input)}")

    state = await RealEstateAgentService.process_user_input(
        state, user_input, "special_features"
    )

    print_json(state["current_question"], "Current Question (None - Completed)")
    print(f"\n💬 Agent: {state['conversational_message']}")
    print_state(state, "Final State")

    # ========================================================================
    # STEP 9: GET USER SUMMARY
    # ========================================================================

    print_header("STEP 9: Final User Summary")

    user_summary = RealEstateAgentService.get_user_summary(state)
    print_json(user_summary, "Complete User Summary")

    # ========================================================================
    # STEP 10: CONVERSATION HISTORY
    # ========================================================================

    print_header("STEP 10: Complete Conversation History")

    print(f"\n📝 Total messages: {len(state['messages'])}\n")
    for i, msg in enumerate(state["messages"], 1):
        role = "👤 User" if msg["role"] == "user" else "💬 Agent"
        print(f"{i}. {role}: {msg['content'][:100]}...")

    print_json(state["messages"], "Full Messages Array")

    # ========================================================================
    # COMPLETION
    # ========================================================================

    print_header("✅ CONVERSATION COMPLETED")

    completion_summary = {
        "status": "completed",
        "session_id": session_id,
        "completed": state["completed"],
        "total_questions_answered": len(state["questions_completed"]),
        "user_preferences": user_summary,
        "conversation_length": len(state["messages"]),
    }

    print_json(completion_summary, "Completion Summary")

    print("\n" + "=" * 80)
    print("  ✅ REAL ESTATE AGENT DEMO COMPLETED SUCCESSFULLY")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
