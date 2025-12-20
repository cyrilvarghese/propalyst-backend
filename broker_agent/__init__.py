"""
Real Estate Agent
=================

A LangChain-based conversational real estate agent that probes for:
1. Transaction type (buy or sell)
2. Location
3. Price range
4. Property area/size
5. Property type
6. Special features/preferences

Usage:
------
from broker_agent.service import RealEstateAgentService

# Create session
session_id = RealEstateAgentService.create_session()
state = RealEstateAgentService.create_initial_state(session_id)

# Get first question
state = await RealEstateAgentService.get_next_question(state)

# Process user answer
state = await RealEstateAgentService.process_user_input(
    state, "buy", "transaction_type"
)

# Get user summary
summary = RealEstateAgentService.get_user_summary(state)
"""

from .state import (
    RealEstateAgentState,
    ConversationalQuestion,
    PropertyPreference,
    create_real_estate_state,
)
from .graph import create_real_estate_agent_graph, route_real_estate_agent
from .service import RealEstateAgentService
from .router import router

__all__ = [
    "RealEstateAgentState",
    "ConversationalQuestion",
    "PropertyPreference",
    "create_real_estate_state",
    "create_real_estate_agent_graph",
    "route_real_estate_agent",
    "RealEstateAgentService",
    "router",
]
