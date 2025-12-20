"""
Real Estate Agent Service
==========================

Business logic layer for the real estate agent.

Handles:
- Graph invocation and session management
- Conversation state updates
- User input processing and validation
"""

from typing import Optional, Dict, Any
import uuid
import logging

from .state import RealEstateAgentState, create_real_estate_state
from .graph import create_real_estate_agent_graph

logger = logging.getLogger(__name__)


class RealEstateAgentService:
    """Service for managing real estate agent conversations"""

    # Cache compiled graph to avoid recreating it
    _graph = None

    @classmethod
    def _get_graph(cls):
        """Get or create the compiled graph"""
        if cls._graph is None:
            cls._graph = create_real_estate_agent_graph()
        return cls._graph

    @staticmethod
    def create_session() -> str:
        """
        Create a new conversation session.

        Returns:
            str: Unique session ID

        Example:
            >>> session_id = RealEstateAgentService.create_session()
            >>> print(session_id)  # "550e8400-e29b-41d4-a716-446655440000"
        """
        return str(uuid.uuid4())

    @staticmethod
    def create_initial_state(session_id: str) -> RealEstateAgentState:
        """
        Create initial state for a new session.

        Args:
            session_id (str): Unique session identifier

        Returns:
            RealEstateAgentState: Fresh state with all fields initialized
        """
        return create_real_estate_state(session_id)

    @classmethod
    async def process_user_input(
        cls,
        state: RealEstateAgentState,
        user_input: Any,
        current_question_id: Optional[str] = None,
    ) -> RealEstateAgentState:
        """
        Process user input and update state.

        This updates the state with the user's answer to the current question,
        then invokes the graph to get the next question.

        The pending_answer and pending_question_id are set to trigger LLM
        acknowledgment generation in the acknowledge node.

        Args:
            state (RealEstateAgentState): Current conversation state
            user_input (Any): User's answer to the current question
            current_question_id (Optional[str]): Which question is being answered

        Returns:
            RealEstateAgentState: Updated state with next question and acknowledgment

        Example:
            >>> state = RealEstateAgentService.create_initial_state("session-123")
            >>> state = await RealEstateAgentService.process_user_input(
            ...     state, "buy", "req_type"
            ... )
            >>> print(state["req_type"])
            "buy"
            >>> print(state["last_response_text"])
            "Great! Buying a property..."
        """

        # Extract and store answer based on question type
        # Track the clean answer value for use in acknowledgment
        answer_for_acknowledgment = None

        if current_question_id == "req_type":
            state = {**state, "req_type": user_input}
            answer_for_acknowledgment = user_input

        elif current_question_id == "proximity_location":
            # Extract location value from object structures:
            # 1. {value: "my_work", ...} - location type
            # 2. {location: {lat, lng, address}, ...} - nested location object
            # 3. {address: "Delhi, India"} - direct address
            if isinstance(user_input, dict):
                location_value = user_input.get("value")

                # If no value, try to extract address from nested location object
                if not location_value and user_input.get("location"):
                    location_obj = user_input["location"]
                    if isinstance(location_obj, dict):
                        location_value = location_obj.get("address")

                # Fallback to address if at root level
                if not location_value:
                    location_value = user_input.get("address")

                # Last resort: stringify
                if not location_value:
                    location_value = str(user_input)
            else:
                location_value = str(user_input)
            state = {**state, "proximity_location": location_value}
            answer_for_acknowledgment = location_value

        elif current_question_id == "budget":
            # Expect array [min, max] (in crores)
            if isinstance(user_input, list) and len(user_input) == 2:
                state = {
                    **state,
                    "price_min": user_input[0],
                    "price_max": user_input[1],
                }
                answer_for_acknowledgment = user_input

        elif current_question_id == "property_area":
            # Expect array [min, max] (in sq ft)
            if isinstance(user_input, list) and len(user_input) == 2:
                state = {
                    **state,
                    "area_min": user_input[0],
                    "area_max": user_input[1],
                }
                answer_for_acknowledgment = user_input

        elif current_question_id == "property_type":
            state = {**state, "property_type": user_input}
            answer_for_acknowledgment = user_input

        elif current_question_id == "special_requests":
            # Expect list of tags/preferences
            if isinstance(user_input, list):
                state = {**state, "special_features": user_input}
                answer_for_acknowledgment = user_input

        elif current_question_id == "special_features":
            # Legacy - for backward compatibility
            if isinstance(user_input, list):
                state = {**state, "special_features": user_input}
                answer_for_acknowledgment = user_input

        # Mark this question as completed
        if current_question_id:
            completed = list(state.get("questions_completed", []))
            if current_question_id not in completed:
                completed.append(current_question_id)
            state = {**state, "questions_completed": completed}

        # Add user message to conversation history
        messages = list(state.get("messages", []))
        messages.append(
            {
                "role": "user",
                "content": str(user_input),
            }
        )
        state = {**state, "messages": messages}

        # Set pending answer for LLM acknowledgment
        # Use the clean extracted answer value, not the raw input
        # This ensures acknowledge node can format it properly
        if answer_for_acknowledgment is not None:
            state = {
                **state,
                "pending_answer": answer_for_acknowledgment,
                "pending_question_id": current_question_id,
            }

        # Invoke graph to get next question
        graph = cls._get_graph()
        result = await graph.ainvoke(state)

        # Add agent message to conversation history
        messages = list(result.get("messages", []))
        agent_message = result.get("conversational_message", "")
        if agent_message and (
            not messages or messages[-1]["role"] != "agent"
        ):
            messages.append({"role": "agent", "content": agent_message})
        result = {**result, "messages": messages}

        return result

    @classmethod
    async def get_next_question(
        cls, state: RealEstateAgentState
    ) -> RealEstateAgentState:
        """
        Get the next question without processing input.

        Useful for getting the initial question or checking what's next.

        Args:
            state (RealEstateAgentState): Current conversation state

        Returns:
            RealEstateAgentState: State with next question set
        """
        graph = cls._get_graph()
        return await graph.ainvoke(state)

    @staticmethod
    def get_user_summary(state: RealEstateAgentState) -> Dict[str, Any]:
        """
        Get a summary of user's preferences from state.

        Args:
            state (RealEstateAgentState): Conversation state

        Returns:
            Dict[str, Any]: Summary of user preferences

        Example:
            >>> state = create_real_estate_state("session-123")
            >>> state = {
            ...     **state,
            ...     "req_type": "buy",
            ...     "proximity_location": "Indiranagar",
            ...     "price_min": 50.0,
            ...     "price_max": 100.0,
            ...     "area_min": 1000,
            ...     "area_max": 2500,
            ...     "property_type": "apartment",
            ...     "special_features": ["gym", "pool"],
            ... }
            >>> summary = RealEstateAgentService.get_user_summary(state)
            >>> print(summary["req_type"])
            "buy"
        """
        return {
            "req_type": state.get("req_type"),
            "proximity_location": state.get("proximity_location"),
            "price_range": {
                "min": state.get("price_min"),
                "max": state.get("price_max"),
            },
            "area_range": {
                "min": state.get("area_min"),
                "max": state.get("area_max"),
            },
            "property_type": state.get("property_type"),
            "special_features": state.get("special_features", []),
        }


__all__ = ["RealEstateAgentService"]
