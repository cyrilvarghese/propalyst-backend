"""
Real Estate Agent - Comprehensive Test Suite
==============================================

Tests for the broker agent including:
- State creation and management
- Graph initialization
- Individual node functions
- Service layer logic
- API endpoint validation
"""

import asyncio
import pytest
from broker_agent.state import (
    RealEstateAgentState,
    create_real_estate_state,
)
from broker_agent.graph import create_real_estate_agent_graph, route_real_estate_agent
from broker_agent.service import RealEstateAgentService
from broker_agent.nodes.questions import (
    ask_transaction_type,
    ask_location,
    ask_price_range,
    ask_property_area,
    ask_property_type,
    ask_special_features,
)


# ============================================================================
# STATE TESTS
# ============================================================================

class TestStateCreation:
    """Test state initialization and creation"""

    def test_create_real_estate_state(self):
        """Test creating initial state"""
        session_id = "test-session-123"
        state = create_real_estate_state(session_id)

        assert state["session_id"] == session_id
        assert state["transaction_type"] is None
        assert state["location"] is None
        assert state["price_min"] is None
        assert state["price_max"] is None
        assert state["area_min"] is None
        assert state["area_max"] is None
        assert state["property_type"] is None
        assert state["special_features"] is None
        assert state["current_question_id"] is None
        assert state["questions_completed"] == []
        assert state["messages"] == []
        assert state["current_question"] is None
        assert state["conversational_message"] == ""
        assert state["completed"] is False
        assert state["error"] is None

    def test_state_immutability(self):
        """Test that state updates don't mutate original"""
        state1 = create_real_estate_state("session-1")
        state2 = {**state1, "transaction_type": "buy"}

        assert state1["transaction_type"] is None
        assert state2["transaction_type"] == "buy"


# ============================================================================
# NODE TESTS
# ============================================================================

class TestQuestionNodes:
    """Test individual question node functions"""

    @pytest.mark.asyncio
    async def test_ask_transaction_type_returns_question(self):
        """Test transaction type node returns correct question"""
        state = create_real_estate_state("session-1")
        result = await ask_transaction_type(state)

        assert result["current_question"]["id"] == "transaction_type"
        assert result["current_question"]["controlType"] == "radio"
        assert result["current_question"]["required"] is True
        assert len(result["current_question"]["data"]["options"]) == 2
        assert result["current_question_id"] == "transaction_type"

    @pytest.mark.asyncio
    async def test_ask_transaction_type_skips_if_answered(self):
        """Test transaction type node skips if already answered"""
        state = create_real_estate_state("session-1")
        state = {**state, "transaction_type": "buy"}
        result = await ask_transaction_type(state)

        assert result == state  # No changes

    @pytest.mark.asyncio
    async def test_ask_location_returns_question(self):
        """Test location node returns correct question"""
        state = create_real_estate_state("session-1")
        result = await ask_location(state)

        assert result["current_question"]["id"] == "location"
        assert result["current_question"]["controlType"] == "autocomplete"
        assert "options" in result["current_question"]["data"]
        assert len(result["current_question"]["data"]["options"]) >= 10

    @pytest.mark.asyncio
    async def test_ask_price_range_returns_question(self):
        """Test price range node returns correct question"""
        state = create_real_estate_state("session-1")
        result = await ask_price_range(state)

        assert result["current_question"]["id"] == "price_range"
        assert result["current_question"]["controlType"] == "range-slider"
        assert result["current_question"]["data"]["min"] == 10
        assert result["current_question"]["data"]["max"] == 500

    @pytest.mark.asyncio
    async def test_ask_property_area_returns_question(self):
        """Test property area node returns correct question"""
        state = create_real_estate_state("session-1")
        result = await ask_property_area(state)

        assert result["current_question"]["id"] == "property_area"
        assert result["current_question"]["controlType"] == "range-slider"
        assert result["current_question"]["data"]["min"] == 500
        assert result["current_question"]["data"]["max"] == 5000

    @pytest.mark.asyncio
    async def test_ask_property_type_returns_question(self):
        """Test property type node returns correct question"""
        state = create_real_estate_state("session-1")
        result = await ask_property_type(state)

        assert result["current_question"]["id"] == "property_type"
        assert result["current_question"]["controlType"] == "toggle-group"
        assert len(result["current_question"]["data"]["options"]) >= 6

    @pytest.mark.asyncio
    async def test_ask_special_features_returns_question(self):
        """Test special features node returns correct question"""
        state = create_real_estate_state("session-1")
        result = await ask_special_features(state)

        assert result["current_question"]["id"] == "special_features"
        assert result["current_question"]["controlType"] == "checkbox-group"
        assert result["current_question"]["required"] is False
        assert len(result["current_question"]["data"]["options"]) >= 10


# ============================================================================
# ROUTER TESTS
# ============================================================================

class TestRouter:
    """Test the graph router function"""

    def test_router_starts_with_transaction_type(self):
        """Test router suggests transaction_type first"""
        state = create_real_estate_state("session-1")
        next_node = route_real_estate_agent(state)
        assert next_node == "ask_transaction_type"

    def test_router_asks_location_after_transaction(self):
        """Test router asks location after transaction type"""
        state = create_real_estate_state("session-1")
        state = {**state, "transaction_type": "buy"}
        next_node = route_real_estate_agent(state)
        assert next_node == "ask_location"

    def test_router_asks_price_after_location(self):
        """Test router asks price after location"""
        state = create_real_estate_state("session-1")
        state = {
            **state,
            "transaction_type": "buy",
            "location": "Indiranagar",
        }
        next_node = route_real_estate_agent(state)
        assert next_node == "ask_price_range"

    def test_router_asks_area_after_price(self):
        """Test router asks area after price range"""
        state = create_real_estate_state("session-1")
        state = {
            **state,
            "transaction_type": "buy",
            "location": "Indiranagar",
            "price_min": 50.0,
            "price_max": 100.0,
        }
        next_node = route_real_estate_agent(state)
        assert next_node == "ask_property_area"

    def test_router_asks_type_after_area(self):
        """Test router asks property type after area"""
        state = create_real_estate_state("session-1")
        state = {
            **state,
            "transaction_type": "buy",
            "location": "Indiranagar",
            "price_min": 50.0,
            "price_max": 100.0,
            "area_min": 1000,
            "area_max": 2500,
        }
        next_node = route_real_estate_agent(state)
        assert next_node == "ask_property_type"

    def test_router_asks_features_after_type(self):
        """Test router asks features after property type"""
        state = create_real_estate_state("session-1")
        state = {
            **state,
            "transaction_type": "buy",
            "location": "Indiranagar",
            "price_min": 50.0,
            "price_max": 100.0,
            "area_min": 1000,
            "area_max": 2500,
            "property_type": "apartment",
        }
        next_node = route_real_estate_agent(state)
        assert next_node == "ask_special_features"

    def test_router_marks_complete_when_all_answered(self):
        """Test router marks conversation complete"""
        state = create_real_estate_state("session-1")
        state = {
            **state,
            "transaction_type": "buy",
            "location": "Indiranagar",
            "price_min": 50.0,
            "price_max": 100.0,
            "area_min": 1000,
            "area_max": 2500,
            "property_type": "apartment",
            "special_features": ["gym", "pool"],
        }
        next_node = route_real_estate_agent(state)
        assert next_node == "mark_complete"

    def test_router_goes_to_end_when_complete(self):
        """Test router goes to END when completed"""
        state = create_real_estate_state("session-1")
        state = {
            **state,
            "transaction_type": "buy",
            "location": "Indiranagar",
            "price_min": 50.0,
            "price_max": 100.0,
            "area_min": 1000,
            "area_max": 2500,
            "property_type": "apartment",
            "special_features": ["gym", "pool"],
            "completed": True,
        }
        next_node = route_real_estate_agent(state)
        assert next_node == "end"


# ============================================================================
# GRAPH TESTS
# ============================================================================

class TestGraph:
    """Test the compiled LangGraph"""

    def test_graph_creation(self):
        """Test graph can be created"""
        graph = create_real_estate_agent_graph()
        assert graph is not None

    @pytest.mark.asyncio
    async def test_graph_first_question(self):
        """Test graph returns first question"""
        graph = create_real_estate_agent_graph()
        state = create_real_estate_state("session-1")
        result = await graph.ainvoke(state)

        assert result["current_question"]["id"] == "transaction_type"
        assert result["conversational_message"] != ""

    @pytest.mark.asyncio
    async def test_graph_flow_transaction_to_location(self):
        """Test graph flow from transaction to location"""
        graph = create_real_estate_agent_graph()
        state = create_real_estate_state("session-1")

        # Get first question
        result = await graph.ainvoke(state)
        assert result["current_question"]["id"] == "transaction_type"

        # Update with answer
        state = {**result, "transaction_type": "buy"}

        # Get next question
        result = await graph.ainvoke(state)
        assert result["current_question"]["id"] == "location"


# ============================================================================
# SERVICE TESTS
# ============================================================================

class TestRealEstateAgentService:
    """Test the service layer"""

    def test_create_session_returns_id(self):
        """Test session creation returns unique ID"""
        session_id = RealEstateAgentService.create_session()
        assert isinstance(session_id, str)
        assert len(session_id) > 0

    def test_create_session_returns_unique_ids(self):
        """Test each session gets unique ID"""
        session_id_1 = RealEstateAgentService.create_session()
        session_id_2 = RealEstateAgentService.create_session()
        assert session_id_1 != session_id_2

    def test_create_initial_state(self):
        """Test initial state creation"""
        session_id = "test-session"
        state = RealEstateAgentService.create_initial_state(session_id)

        assert state["session_id"] == session_id
        assert state["transaction_type"] is None

    @pytest.mark.asyncio
    async def test_get_next_question(self):
        """Test getting next question"""
        state = RealEstateAgentService.create_initial_state("session-1")
        result = await RealEstateAgentService.get_next_question(state)

        assert result["current_question"] is not None
        assert result["current_question"]["id"] == "transaction_type"

    @pytest.mark.asyncio
    async def test_process_user_input_transaction_type(self):
        """Test processing transaction type input"""
        state = RealEstateAgentService.create_initial_state("session-1")
        result = await RealEstateAgentService.process_user_input(
            state, "buy", "transaction_type"
        )

        assert result["transaction_type"] == "buy"
        assert "transaction_type" in result["questions_completed"]
        assert result["current_question"]["id"] == "location"

    @pytest.mark.asyncio
    async def test_process_user_input_location(self):
        """Test processing location input"""
        state = RealEstateAgentService.create_initial_state("session-1")
        state = {**state, "transaction_type": "buy"}

        result = await RealEstateAgentService.process_user_input(
            state, "Indiranagar", "location"
        )

        assert result["location"] == "Indiranagar"
        assert result["current_question"]["id"] == "price_range"

    @pytest.mark.asyncio
    async def test_process_user_input_price_range(self):
        """Test processing price range input"""
        state = RealEstateAgentService.create_initial_state("session-1")
        state = {
            **state,
            "transaction_type": "buy",
            "location": "Indiranagar",
        }

        result = await RealEstateAgentService.process_user_input(
            state, {"min": 50.0, "max": 100.0}, "price_range"
        )

        assert result["price_min"] == 50.0
        assert result["price_max"] == 100.0
        assert result["current_question"]["id"] == "property_area"

    @pytest.mark.asyncio
    async def test_process_user_input_property_area(self):
        """Test processing property area input"""
        state = RealEstateAgentService.create_initial_state("session-1")
        state = {
            **state,
            "transaction_type": "buy",
            "location": "Indiranagar",
            "price_min": 50.0,
            "price_max": 100.0,
        }

        result = await RealEstateAgentService.process_user_input(
            state, {"min": 1000, "max": 2500}, "property_area"
        )

        assert result["area_min"] == 1000
        assert result["area_max"] == 2500
        assert result["current_question"]["id"] == "property_type"

    @pytest.mark.asyncio
    async def test_process_user_input_property_type(self):
        """Test processing property type input"""
        state = RealEstateAgentService.create_initial_state("session-1")
        state = {
            **state,
            "transaction_type": "buy",
            "location": "Indiranagar",
            "price_min": 50.0,
            "price_max": 100.0,
            "area_min": 1000,
            "area_max": 2500,
        }

        result = await RealEstateAgentService.process_user_input(
            state, "apartment", "property_type"
        )

        assert result["property_type"] == "apartment"
        assert result["current_question"]["id"] == "special_features"

    @pytest.mark.asyncio
    async def test_process_user_input_special_features(self):
        """Test processing special features input"""
        state = RealEstateAgentService.create_initial_state("session-1")
        state = {
            **state,
            "transaction_type": "buy",
            "location": "Indiranagar",
            "price_min": 50.0,
            "price_max": 100.0,
            "area_min": 1000,
            "area_max": 2500,
            "property_type": "apartment",
        }

        result = await RealEstateAgentService.process_user_input(
            state, ["gym", "pool", "parking"], "special_features"
        )

        assert result["special_features"] == ["gym", "pool", "parking"]
        assert result["completed"] is True

    def test_get_user_summary(self):
        """Test getting user summary"""
        state = RealEstateAgentService.create_initial_state("session-1")
        state = {
            **state,
            "transaction_type": "buy",
            "location": "Indiranagar",
            "price_min": 50.0,
            "price_max": 100.0,
            "area_min": 1000,
            "area_max": 2500,
            "property_type": "apartment",
            "special_features": ["gym", "pool"],
        }

        summary = RealEstateAgentService.get_user_summary(state)

        assert summary["transaction_type"] == "buy"
        assert summary["location"] == "Indiranagar"
        assert summary["price_range"]["min"] == 50.0
        assert summary["price_range"]["max"] == 100.0
        assert summary["area_range"]["min"] == 1000
        assert summary["area_range"]["max"] == 2500
        assert summary["property_type"] == "apartment"
        assert summary["special_features"] == ["gym", "pool"]


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestFullConversation:
    """Test complete conversation flow"""

    @pytest.mark.asyncio
    async def test_full_conversation_flow(self):
        """Test complete conversation from start to finish"""
        # Create session
        session_id = RealEstateAgentService.create_session()
        state = RealEstateAgentService.create_initial_state(session_id)

        # Q1: Transaction Type
        state = await RealEstateAgentService.get_next_question(state)
        assert state["current_question"]["id"] == "transaction_type"

        state = await RealEstateAgentService.process_user_input(
            state, "buy", "transaction_type"
        )
        assert state["transaction_type"] == "buy"

        # Q2: Location
        assert state["current_question"]["id"] == "location"
        state = await RealEstateAgentService.process_user_input(
            state, "Indiranagar", "location"
        )
        assert state["location"] == "Indiranagar"

        # Q3: Price Range
        assert state["current_question"]["id"] == "price_range"
        state = await RealEstateAgentService.process_user_input(
            state, {"min": 50.0, "max": 100.0}, "price_range"
        )
        assert state["price_min"] == 50.0
        assert state["price_max"] == 100.0

        # Q4: Property Area
        assert state["current_question"]["id"] == "property_area"
        state = await RealEstateAgentService.process_user_input(
            state, {"min": 1000, "max": 2500}, "property_area"
        )
        assert state["area_min"] == 1000
        assert state["area_max"] == 2500

        # Q5: Property Type
        assert state["current_question"]["id"] == "property_type"
        state = await RealEstateAgentService.process_user_input(
            state, "apartment", "property_type"
        )
        assert state["property_type"] == "apartment"

        # Q6: Special Features
        assert state["current_question"]["id"] == "special_features"
        state = await RealEstateAgentService.process_user_input(
            state, ["gym", "pool", "parking"], "special_features"
        )
        assert state["special_features"] == ["gym", "pool", "parking"]

        # Completed
        assert state["completed"] is True
        assert state["conversational_message"] != ""

        # Get summary
        summary = RealEstateAgentService.get_user_summary(state)
        assert summary["transaction_type"] == "buy"
        assert summary["location"] == "Indiranagar"


# ============================================================================
# RUN TESTS
# ============================================================================

if __name__ == "__main__":
    # Run with: pytest test_broker_agent.py -v
    # Or: python -m pytest test_broker_agent.py -v
    pytest.main([__file__, "-v"])
