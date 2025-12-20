"""
Real Estate Agent - Example Usage
===================================

This script demonstrates how to use the real estate agent programmatically.

Run with: python test_broker_agent_example.py
(Requires async runtime, or wrap in asyncio.run())
"""

import asyncio
from broker_agent.service import RealEstateAgentService
from broker_agent.state import create_real_estate_state


async def main():
    """Example conversation with the real estate agent"""

    print("\n" + "=" * 70)
    print("REAL ESTATE AGENT - EXAMPLE CONVERSATION")
    print("=" * 70)

    # Step 1: Create a new session
    print("\n[Step 1] Creating new session...")
    session_id = RealEstateAgentService.create_session()
    print(f"✅ Session created: {session_id}")

    # Initialize state
    state = RealEstateAgentService.create_initial_state(session_id)

    # Step 2: Get first question
    print("\n[Step 2] Getting first question...")
    state = await RealEstateAgentService.get_next_question(state)
    print(f"Agent: {state['conversational_message']}")
    print(f"Question ID: {state['current_question']['id']}")
    print(f"Control Type: {state['current_question']['controlType']}")
    if "options" in state["current_question"]["data"]:
        for opt in state["current_question"]["data"]["options"]:
            print(f"  - {opt['label']}")

    # Step 3: Answer Q1 - Transaction Type
    print("\n[Step 3] Answering Q1: Transaction Type...")
    user_answer = "buy"
    print(f"User: {user_answer}")
    state = await RealEstateAgentService.process_user_input(
        state, user_answer, "transaction_type"
    )
    print(f"Agent: {state['conversational_message']}")
    print(f"Next question: {state['current_question']['id']}")

    # Step 4: Answer Q2 - Location
    print("\n[Step 4] Answering Q2: Location...")
    user_answer = "Indiranagar"
    print(f"User: {user_answer}")
    state = await RealEstateAgentService.process_user_input(
        state, user_answer, "location"
    )
    print(f"Agent: {state['conversational_message']}")
    print(f"Next question: {state['current_question']['id']}")

    # Step 5: Answer Q3 - Price Range
    print("\n[Step 5] Answering Q3: Price Range...")
    user_answer = {"min": 50.0, "max": 100.0}
    print(f"User: {user_answer}")
    state = await RealEstateAgentService.process_user_input(
        state, user_answer, "price_range"
    )
    print(f"Agent: {state['conversational_message']}")
    print(f"Next question: {state['current_question']['id']}")

    # Step 6: Answer Q4 - Property Area
    print("\n[Step 6] Answering Q4: Property Area...")
    user_answer = {"min": 1000, "max": 2500}
    print(f"User: {user_answer}")
    state = await RealEstateAgentService.process_user_input(
        state, user_answer, "property_area"
    )
    print(f"Agent: {state['conversational_message']}")
    print(f"Next question: {state['current_question']['id']}")

    # Step 7: Answer Q5 - Property Type
    print("\n[Step 7] Answering Q5: Property Type...")
    user_answer = "apartment"
    print(f"User: {user_answer}")
    state = await RealEstateAgentService.process_user_input(
        state, user_answer, "property_type"
    )
    print(f"Agent: {state['conversational_message']}")
    print(f"Next question: {state['current_question']['id']}")

    # Step 8: Answer Q6 - Special Features
    print("\n[Step 8] Answering Q6: Special Features...")
    user_answer = ["gym", "pool", "parking", "security"]
    print(f"User: {user_answer}")
    state = await RealEstateAgentService.process_user_input(
        state, user_answer, "special_features"
    )
    print(f"Agent: {state['conversational_message']}")
    print(f"Conversation completed: {state['completed']}")

    # Step 9: Get user summary
    print("\n[Step 9] Getting user summary...")
    summary = RealEstateAgentService.get_user_summary(state)
    print("User Preferences:")
    print(f"  Transaction Type: {summary['transaction_type']}")
    print(f"  Location: {summary['location']}")
    print(f"  Price Range: ₹{summary['price_range']['min']}-{summary['price_range']['max']} lakhs")
    print(f"  Area Range: {summary['area_range']['min']}-{summary['area_range']['max']} sq ft")
    print(f"  Property Type: {summary['property_type']}")
    print(f"  Special Features: {', '.join(summary['special_features'])}")

    # Step 10: Show conversation history
    print("\n[Step 10] Conversation History:")
    for i, msg in enumerate(state["messages"], 1):
        role = msg["role"].upper()
        content = msg["content"]
        print(f"  {i}. [{role}] {content}")

    print("\n" + "=" * 70)
    print("✅ Example conversation completed successfully!")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
