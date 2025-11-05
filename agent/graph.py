"""
LangGraph Workflow Definition
==============================

This module creates the LangGraph workflow (the "graph").

Key Concepts:
-------------
1. StateGraph: The workflow container
2. Nodes: Functions that process state
3. Edges: Connections between nodes
4. Entry/Exit points: Where the graph starts and ends

Our Graph:
----------
    START
      ↓
[extract_ui_component]
      ↓
     END

Simple, right? Just one node for now!

Later projects will have multiple nodes with conditional routing.
"""

from langgraph.graph import StateGraph, END
from typing import Callable

from .state import AgentState, PropalystState
from .nodes.ui_extractor import extract_ui_component
from .nodes.propalyst_qa import (
    ask_work_location,
    ask_kids,
    ask_commute,
    ask_property_type,
    ask_budget
)


# ============================================================================
# GRAPH CREATION
# ============================================================================

def create_ui_generator_graph() -> Callable:
    """
    Creates and compiles the LangGraph workflow.

    Steps:
    ------
    1. Create StateGraph with AgentState type
    2. Add node(s) to the graph
    3. Set entry point (where graph starts)
    4. Add edge(s) to connect nodes
    5. Compile the graph into a runnable function

    Returns:
        Callable: Compiled graph that can be invoked with state

    Example:
        >>> graph = create_ui_generator_graph()
        >>> result = await graph.ainvoke({"user_input": "button"})
        >>> print(result["component"].type)
        "Button"
    """

    # Step 1: Create the StateGraph
    # This tells LangGraph what type of state will flow through the workflow
    workflow = StateGraph(AgentState)

    # Step 2: Add nodes
    # Each node is a function that processes the state
    # Signature: (state: AgentState) -> AgentState
    workflow.add_node("extract_ui", extract_ui_component)

    # Step 3: Set entry point
    # This is where the graph starts executing
    # The state will first flow to the "extract_ui" node
    workflow.set_entry_point("extract_ui")

    # Step 4: Add edges
    # Edges define how state flows between nodes
    # Since we only have one node, we just connect it to END
    workflow.add_edge("extract_ui", END)

    # Step 5: Compile the graph
    # This creates an actual runnable function from the graph definition
    # The compiled graph can be called with .invoke() or .ainvoke()
    app = workflow.compile()

    return app


# ============================================================================
# GRAPH WITH MULTIPLE NODES (Future enhancement example)
# ============================================================================

def create_multi_node_graph() -> Callable:
    """
    Example of a multi-node graph (for future projects).

    This shows how you'd build a more complex workflow.

    Graph structure:
    ----------------
        START
          ↓
    [extract_ui]
          ↓
    [validate_props]
          ↓
    [enhance_component]
          ↓
         END

    Returns:
        Callable: Compiled multi-node graph
    """

    workflow = StateGraph(AgentState)

    # Add multiple nodes
    workflow.add_node("extract_ui", extract_ui_component)
    # workflow.add_node("validate_props", validate_props_node)
    # workflow.add_node("enhance_component", enhance_component_node)

    # Set entry point
    workflow.set_entry_point("extract_ui")

    # Connect nodes in sequence
    # workflow.add_edge("extract_ui", "validate_props")
    # workflow.add_edge("validate_props", "enhance_component")
    # workflow.add_edge("enhance_component", END)

    # Compile
    app = workflow.compile()

    return app


# ============================================================================
# GRAPH WITH CONDITIONAL ROUTING (Project 2 preview)
# ============================================================================

def create_conditional_graph() -> Callable:
    """
    Example of conditional routing (for Project 2).

    This shows how to route to different nodes based on state.

    Graph structure:
    ----------------
        START
          ↓
    [extract_ui]
          ↓
      [ROUTER] -----> if valid: [format_response]
          |                           ↓
          |                          END
          |
          └---------> if invalid: [handle_error]
                                      ↓
                                     END

    Returns:
        Callable: Compiled graph with conditional routing
    """

    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("extract_ui", extract_ui_component)
    # workflow.add_node("format_response", format_response_node)
    # workflow.add_node("handle_error", handle_error_node)

    # Set entry point
    workflow.set_entry_point("extract_ui")

    # Add conditional edges
    # def route_based_on_validity(state: AgentState) -> str:
    #     """Router function that decides which node to go to next"""
    #     if state.get("error") is None:
    #         return "format_response"
    #     else:
    #         return "handle_error"

    # workflow.add_conditional_edges(
    #     "extract_ui",
    #     route_based_on_validity,
    #     {
    #         "format_response": "format_response",
    #         "handle_error": "handle_error"
    #     }
    # )

    # Both branches end
    # workflow.add_edge("format_response", END)
    # workflow.add_edge("handle_error", END)

    # Compile
    app = workflow.compile()

    return app


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

async def run_graph(user_input: str) -> AgentState:
    """
    Convenience function to run the graph with user input.

    Args:
        user_input (str): The user's UI component request

    Returns:
        AgentState: Final state after graph execution

    Example:
        >>> result = await run_graph("button")
        >>> print(result["component"].type)
        "Button"
    """
    # Create the graph
    app = create_ui_generator_graph()

    # Create initial state
    initial_state = AgentState(
        user_input=user_input,
        component=None,
        message="",
        error=None
    )

    # Run the graph
    final_state = await app.ainvoke(initial_state)

    return final_state


def visualize_graph(save_path: str = "graph.png"):
    """
    Visualize the graph structure (requires graphviz).

    This creates a visual diagram of your workflow.
    Useful for understanding complex graphs!

    Args:
        save_path (str): Where to save the graph image

    Note:
        Requires: pip install graphviz
        Also needs graphviz system package installed

    Example:
        >>> visualize_graph("my_workflow.png")
        # Creates an image file showing the graph structure
    """
    try:
        app = create_ui_generator_graph()

        # This will generate a visual representation
        # showing nodes and edges
        graph_image = app.get_graph().draw_mermaid_png()

        with open(save_path, "wb") as f:
            f.write(graph_image)

        print(f"✅ Graph visualization saved to: {save_path}")

    except ImportError:
        print("❌ graphviz not installed. Run: pip install graphviz")
    except Exception as e:
        print(f"❌ Error visualizing graph: {e}")


# ============================================================================
# PROPALYST GRAPH (Project 2 - Multi-step Q&A)
# ============================================================================

def route_propalyst(state: PropalystState) -> str:
    """
    Router for Propalyst conversation flow.

    This is the "brain" that decides what to do next based on state.

    Decision logic:
    ---------------
    1. Check Q1 (work_location) - if missing, ask
    2. Check Q2 (has_kids) - if missing, ask
    3. Check Q3 (commute_time_max) - if missing, ask
    4. Check Q4 (property_type) - if missing, ask
    5. Check Q5 (budget_max) - if missing, ask
    6. If all answered → END (for now, will add calculator later)

    Args:
        state: Current PropalystState

    Returns:
        str: Name of next node to execute

    Examples:
        >>> state = {"work_location": None, ...}
        >>> route_propalyst(state)
        "ask_work_location"

        >>> state = {"work_location": "Whitefield", "has_kids": None, ...}
        >>> route_propalyst(state)
        "ask_kids"
    """

    print("\n🎯 ROUTER: Deciding next step...")
    print(f"   State: work_location={state.get('work_location')}, "
          f"has_kids={state.get('has_kids')}, "
          f"commute={state.get('commute_time_max')}, "
          f"type={state.get('property_type')}, "
          f"budget={state.get('budget_max')}")

    # Q1: Work location
    if not state.get("work_location"):
        print("   → Missing work_location, going to ask_work_location")
        return "ask_work_location"

    # Q2: Kids
    if state.get("has_kids") is None:
        print("   → Missing has_kids, going to ask_kids")
        return "ask_kids"

    # Q3: Commute
    if not state.get("commute_time_max"):
        print("   → Missing commute_time_max, going to ask_commute")
        return "ask_commute"

    # Q4: Property type
    if not state.get("property_type"):
        print("   → Missing property_type, going to ask_property_type")
        return "ask_property_type"

    # Q5: Budget
    if not state.get("budget_max"):
        print("   → Missing budget_max, going to ask_budget")
        return "ask_budget"

    # All questions answered!
    print("   → All questions answered! Going to END")
    return "end"


def create_propalyst_graph() -> Callable:
    """
    Creates the Propalyst Q&A conversation graph.

    This graph handles the multi-step conversation:
    Q1 → Q2 → Q3 → Q4 → Q5 → END

    The graph uses conditional routing to decide which question
    to ask next based on what data is missing.

    Graph structure:
    ----------------
                    START
                      ↓
                [ROUTER] ← Checks what's missing
                      ↓
            ┌─────────┼─────────┐
            │         │         │
       [Q1:work] [Q2:kids] [Q3:commute] ...
            │         │         │
            └─────────┴─────────┘
                      ↓
                    END

    Key: Router runs ONCE per request at entry point.
    After showing a component, we go to END (not back to router).

    Returns:
        Callable: Compiled graph that can be invoked

    Example:
        >>> graph = create_propalyst_graph()
        >>> state = create_propalyst_state("session-123")
        >>> result = await graph.ainvoke(state)
        >>> print(result["component"])
        {"type": "TextInput", "props": {...}}
    """

    print("🔄 Creating Propalyst Q&A graph...")

    # Create StateGraph with PropalystState
    workflow = StateGraph(PropalystState)

    # Add all Q&A nodes
    workflow.add_node("ask_work_location", ask_work_location)
    workflow.add_node("ask_kids", ask_kids)
    workflow.add_node("ask_commute", ask_commute)
    workflow.add_node("ask_property_type", ask_property_type)
    workflow.add_node("ask_budget", ask_budget)

    # Set entry point with conditional routing
    # Router decides which node to run based on what's missing
    workflow.set_conditional_entry_point(
        route_propalyst,
        {
            "ask_work_location": "ask_work_location",
            "ask_kids": "ask_kids",
            "ask_commute": "ask_commute",
            "ask_property_type": "ask_property_type",
            "ask_budget": "ask_budget",
            "end": END
        }
    )

    # After each node runs, go to END
    # Don't route back through router (prevents infinite loop)
    workflow.add_edge("ask_work_location", END)
    workflow.add_edge("ask_kids", END)
    workflow.add_edge("ask_commute", END)
    workflow.add_edge("ask_property_type", END)
    workflow.add_edge("ask_budget", END)

    # Compile the graph
    app = workflow.compile()

    print("✅ Propalyst graph created!")
    return app


# ============================================================================
# EXPORT
# ============================================================================

__all__ = [
    "create_ui_generator_graph",
    "create_propalyst_graph",
    "run_graph",
    "visualize_graph"
]
