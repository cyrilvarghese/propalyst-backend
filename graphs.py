"""
Graph Instances Module
======================

Centralized initialization of LangGraph workflow instances.
This module ensures graphs are initialized once and can be imported by routers.
"""

from agent import create_ui_generator_graph
from agent.graph import create_propalyst_graph

# Initialize graphs at module level
# These will be created when the module is first imported

print("[INIT] Initializing UI Generator workflow...")
ui_generator_graph = create_ui_generator_graph()
print("[INIT] UI Generator workflow ready!")

print("[INIT] Initializing Propalyst Q&A workflow...")
propalyst_graph = create_propalyst_graph()
print("[INIT] Propalyst Q&A workflow ready!")




