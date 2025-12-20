"""
Real Estate Agent LangGraph
=============================

Creates the conversation flow for the real estate agent.

The agent asks questions in order:
1. Transaction type (buy/sell)
2. Location
3. Price range
4. Property area
5. Property type
6. Special features

Uses conditional routing to determine which question to ask next.
"""

from langgraph.graph import StateGraph, END
from typing import Callable

from .state import RealEstateAgentState
from .nodes import (
    ask_transaction_type,
    ask_location,
    ask_price_range,
    ask_property_area,
    ask_property_type,
    ask_special_features,
    generate_acknowledgment,
)
from .nodes.completion import mark_conversation_complete


# ============================================================================
# ROUTER FUNCTION
# ============================================================================

def route_real_estate_agent(state: RealEstateAgentState) -> str:
    """
    Router that decides which question to ask next.

    This is the "brain" of the conversation. It checks what information
    is missing and routes to the appropriate question node.

    Decision Logic:
    ---------------
    1. Check req_type - if missing, ask
    2. Check proximity_location - if missing, ask
    3. Check price_min/max (budget) - if missing, ask
    4. Check area_min/max - if missing, ask
    5. Check property_type - if missing, ask
    6. Check special_features (special requests) - if missing, ask
    7. If all answered → mark complete

    Args:
        state (RealEstateAgentState): Current conversation state

    Returns:
        str: Name of next node to execute

    Examples:
        >>> state = create_real_estate_state("session-123")
        >>> route_real_estate_agent(state)
        "ask_transaction_type"

        >>> state["transaction_type"] = "buy"
        >>> route_real_estate_agent(state)
        "ask_location"
    """

    print("\n🎯 ROUTER: Deciding next question...")
    print(
        f"   State: req_type={state.get('req_type')}, "
        f"proximity_location={state.get('proximity_location')}, "
        f"price={state.get('price_min')}-{state.get('price_max')}, "
        f"area={state.get('area_min')}-{state.get('area_max')}, "
        f"type={state.get('property_type')}, "
        f"features={state.get('special_features')}"
    )

    # Q1: Transaction type
    if not state.get("req_type"):
        print("   → Missing req_type, asking...")
        return "ask_transaction_type"

    # Q2: Proximity Location
    if not state.get("proximity_location"):
        print("   → Missing proximity_location, asking...")
        return "ask_location"

    # Q3: Budget
    if not state.get("price_min") or not state.get("price_max"):
        print("   → Missing budget, asking...")
        return "ask_price_range"

    # Q4: Property area
    if not state.get("area_min") or not state.get("area_max"):
        print("   → Missing area, asking...")
        return "ask_property_area"

    # Q5: Property type
    if not state.get("property_type"):
        print("   → Missing property_type, asking...")
        return "ask_property_type"

    # Q6: Special requests (optional but encouraged)
    if not state.get("special_features"):
        print("   → Missing special requests, asking...")
        return "ask_special_features"

    # All questions answered - mark complete
    if not state.get("completed"):
        print("   → All questions answered! Marking complete...")
        return "mark_complete"

    print("   → Conversation complete, going to END")
    return "end"


# ============================================================================
# GRAPH CREATION
# ============================================================================

def create_real_estate_agent_graph() -> Callable:
    """
    Creates and compiles the real estate agent conversation graph.

    Graph Structure:
    ----------------
                        START
                          ↓
                    [ROUTER] ← Checks what's missing
                          ↓
        ┌─────────────────┼─────────────────┐
        │                 │                 │
    [Q1:trans]    [Q2:location]    [Q3:price] ... [Q6:features] [mark_complete]
        │                 │                 │
        └──→[LLM ACKNOWLEDGE]←──────────────┘
                          ↓
                        END

    Key Design:
    - Router runs ONCE per request at entry point
    - Each question node → acknowledge node → END
    - Acknowledge node generates LLM-based response
    - State persists between requests via session ID
    - No loops within a single request

    Returns:
        Callable: Compiled graph that can be invoked with state

    Example:
        >>> from broker_agent.state import create_real_estate_state
        >>> graph = create_real_estate_agent_graph()
        >>> state = create_real_estate_state("session-123")
        >>> result = await graph.ainvoke(state)
        >>> print(result["current_question"]["id"])
        "transaction_type"
    """

    print("🔄 Creating Real Estate Agent graph...")

    # Create StateGraph with RealEstateAgentState
    workflow = StateGraph(RealEstateAgentState)

    # Add all question nodes
    workflow.add_node("ask_transaction_type", ask_transaction_type)
    workflow.add_node("ask_location", ask_location)
    workflow.add_node("ask_price_range", ask_price_range)
    workflow.add_node("ask_property_area", ask_property_area)
    workflow.add_node("ask_property_type", ask_property_type)
    workflow.add_node("ask_special_features", ask_special_features)

    # Add acknowledgment and completion nodes
    workflow.add_node("acknowledge", generate_acknowledgment)
    workflow.add_node("mark_complete", mark_conversation_complete)

    # Set entry point with conditional routing
    # Router decides which question to ask based on what's missing
    workflow.set_conditional_entry_point(
        route_real_estate_agent,
        {
            "ask_transaction_type": "ask_transaction_type",
            "ask_location": "ask_location",
            "ask_price_range": "ask_price_range",
            "ask_property_area": "ask_property_area",
            "ask_property_type": "ask_property_type",
            "ask_special_features": "ask_special_features",
            "mark_complete": "mark_complete",
            "end": END,
        },
    )

    # Route all question nodes through acknowledgment
    workflow.add_edge("ask_transaction_type", "acknowledge")
    workflow.add_edge("ask_location", "acknowledge")
    workflow.add_edge("ask_price_range", "acknowledge")
    workflow.add_edge("ask_property_area", "acknowledge")
    workflow.add_edge("ask_property_type", "acknowledge")
    workflow.add_edge("ask_special_features", "acknowledge")

    # Acknowledgment and completion go to END
    workflow.add_edge("acknowledge", END)
    workflow.add_edge("mark_complete", END)

    # Compile the graph
    app = workflow.compile()

    print("✅ Real Estate Agent graph created!")
    return app


# ============================================================================
# EXPORT
# ============================================================================

__all__ = ["create_real_estate_agent_graph", "route_real_estate_agent"]
