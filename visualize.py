"""
Visualize LangGraph Workflow
=============================

This script creates a visual representation of the LangGraph workflow.
"""

import sys
from agent.graph import create_ui_generator_graph

def visualize_as_mermaid():
    """
    Generate a Mermaid diagram of the workflow.

    Mermaid is a text-based diagram format that can be:
    - Viewed in markdown files
    - Rendered by GitHub
    - Converted to images online at mermaid.live
    """
    print("🔄 Creating LangGraph workflow...")
    app = create_ui_generator_graph()

    print("✅ Workflow created!")
    print("\n" + "="*60)
    print("LANGGRAPH WORKFLOW DIAGRAM (Mermaid Format)")
    print("="*60 + "\n")

    try:
        # Get the Mermaid diagram
        mermaid_code = app.get_graph().draw_mermaid()

        print(mermaid_code)

        print("\n" + "="*60)
        print("HOW TO VIEW THIS DIAGRAM:")
        print("="*60)
        print("1. Copy the diagram above (starting from 'graph TD')")
        print("2. Visit: https://mermaid.live")
        print("3. Paste the code in the editor")
        print("4. See your workflow visualized!")
        print("\nOR")
        print("5. Save to a .md file and view in GitHub/VS Code")
        print("="*60)

        # Save to file
        with open("workflow.mmd", "w") as f:
            f.write(mermaid_code)

        print("\n✅ Also saved to: workflow.mmd")

    except Exception as e:
        print(f"❌ Error: {e}")
        return 1

    return 0

def visualize_as_ascii():
    """
    Generate a simple ASCII representation of the workflow.
    """
    print("\n" + "="*60)
    print("ASCII WORKFLOW DIAGRAM")
    print("="*60 + "\n")

    diagram = """
    ┌─────────────────────────────────────────┐
    │              __START__                  │
    └─────────────────┬───────────────────────┘
                      │
                      ↓
    ┌─────────────────────────────────────────┐
    │                                         │
    │         extract_ui_component            │
    │                                         │
    │  • Receives user input                  │
    │  • Calls LLM (OpenAI)                   │
    │  • Extracts component type & props      │
    │  • Returns UIComponent                  │
    │                                         │
    └─────────────────┬───────────────────────┘
                      │
                      ↓
    ┌─────────────────────────────────────────┐
    │               __END__                   │
    └─────────────────────────────────────────┘

    Flow Example:
    =============

    Input State:
    ┌───────────────────────────────────────┐
    │ user_input: "button"                  │
    │ component: None                       │
    │ message: ""                           │
    │ error: None                           │
    └───────────────────────────────────────┘
              ↓
    [extract_ui_component node processes]
              ↓
    Output State:
    ┌───────────────────────────────────────┐
    │ user_input: "button"                  │
    │ component: {                          │
    │   type: "Button",                     │
    │   props: {                            │
    │     label: "Click Me",                │
    │     variant: "primary"                │
    │   }                                   │
    │ }                                     │
    │ message: "Here's a Button component"  │
    │ error: None                           │
    └───────────────────────────────────────┘
    """

    print(diagram)

if __name__ == "__main__":
    print("🎨 LangGraph Workflow Visualizer")
    print("="*60 + "\n")

    # Show ASCII diagram first
    visualize_as_ascii()

    # Then show Mermaid diagram
    sys.exit(visualize_as_mermaid())
