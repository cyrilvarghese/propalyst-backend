"""
Real Estate Agent Service
==========================

Business logic layer for the real estate agent.

Handles:
- Graph invocation and session management
- Conversation state updates
- User input processing and validation
"""

from typing import Optional, Dict, Any, Tuple
import uuid
import logging
import json
from pathlib import Path

from langchain_google_genai import ChatGoogleGenerativeAI

from .state import RealEstateAgentState, create_real_estate_state
from .graph import create_real_estate_agent_graph

logger = logging.getLogger(__name__)


# ============================================================================
# PROMPT LOADING
# ============================================================================

class NLPParserPromptLoader:
    """Loads and caches the NLP parser prompt template"""

    PROMPT_FILE = Path(__file__).parent.parent / "prompts" / "nlp_parser.txt"
    _cache: Optional[str] = None

    @classmethod
    def load(cls) -> str:
        """Load prompt template from file (with caching)"""
        if cls._cache is None:
            try:
                with open(cls.PROMPT_FILE, "r") as f:
                    cls._cache = f.read()
            except FileNotFoundError:
                logger.error(f"Prompt file not found: {cls.PROMPT_FILE}")
                raise
        return cls._cache


# ============================================================================
# REAL ESTATE AGENT SERVICE
# ============================================================================

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
                # Also store for response (these persist across graph execution)
                "last_processed_answer": answer_for_acknowledgment,
                "last_processed_question_id": current_question_id,
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

    @classmethod
    async def process_chat_input(
        cls,
        state: RealEstateAgentState,
        user_text: str,
    ) -> RealEstateAgentState:
        """
        Process natural language chat input.

        Flow:
        1. Parse NLP to extract structured answer
        2. Call process_user_input() with parsed data
        3. Return updated state

        Args:
            state (RealEstateAgentState): Current conversation state
            user_text (str): Natural language text from user

        Returns:
            RealEstateAgentState: Updated state with next question and acknowledgment

        Example:
            >>> state = RealEstateAgentService.create_initial_state("session-123")
            >>> state = await RealEstateAgentService.process_chat_input(
            ...     state, "I want to buy a property in Delhi"
            ... )
            >>> print(state["req_type"])
            "buy"
        """

        # Get current question context
        current_q_id = state.get("current_question_id")

        # Parse with LLM (context-aware)
        answer, inferred_q_id = await cls.parse_natural_language_input(
            user_text=user_text,
            question_id=current_q_id,
            context=state  # Full state for context
        )

        # Process as structured input
        result = await cls.process_user_input(
            state=state,
            user_input=answer,
            current_question_id=inferred_q_id
        )

        return result

    @classmethod
    def _build_nlp_context(cls, state: Optional[Dict[str, Any]]) -> str:
        """
        Build conversation context from state for intelligent NLP parsing.

        Args:
            state (Optional[Dict]): Current conversation state

        Returns:
            str: Formatted context summary for LLM
        """
        if not state:
            return "(No previous answers)"

        context_parts = []

        # Add transaction type if answered
        if state.get("req_type"):
            transaction = "Buying" if state["req_type"] == "buy" else "Selling"
            context_parts.append(f"- Looking to: {transaction}")

        # Add location if answered
        if state.get("proximity_location"):
            location = state["proximity_location"]
            if isinstance(location, str):
                location = location.replace("_", " ").title()
            context_parts.append(f"- Proximity preference: {location}")

        # Add budget if answered
        if state.get("price_min") and state.get("price_max"):
            price = f"₹{state['price_min']:.1f}Cr - ₹{state['price_max']:.1f}Cr"
            context_parts.append(f"- Budget: {price}")

        # Add property area if answered
        if state.get("area_min") and state.get("area_max"):
            area = f"{state['area_min']:,} - {state['area_max']:,} sq ft"
            context_parts.append(f"- Property size: {area}")

        # Add property type if answered
        if state.get("property_type"):
            prop_type = state["property_type"].title()
            context_parts.append(f"- Property type: {prop_type}")

        # Add special features if answered
        if state.get("special_features"):
            features = state["special_features"]
            if isinstance(features, list):
                features_str = ", ".join([f.replace("_", " ").title() for f in features])
                context_parts.append(f"- Special features: {features_str}")

        if not context_parts:
            return "(Starting conversation)"

        return "\n".join(context_parts)

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

    @classmethod
    async def parse_natural_language_input(
        cls,
        user_text: str,
        question_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Any, Optional[str]]:
        """
        Parse natural language input and convert to structured answer.

        Uses LLM to understand user intent and convert to the format
        expected by process_user_input.

        Args:
            user_text (str): Natural language text from user (e.g., "I want to buy")
            question_id (Optional[str]): Which question this is answering
            context (Optional[Dict]): State context for better understanding

        Returns:
            Tuple[Any, Optional[str]]: (parsed_answer, inferred_question_id)
                - parsed_answer: The answer in expected format
                - inferred_question_id: The question ID if not provided

        Example:
            >>> answer, qid = await RealEstateAgentService.parse_natural_language_input(
            ...     "I want to buy a property",
            ...     question_id="req_type"
            ... )
            >>> print(answer)  # "buy"
            >>> print(qid)     # "req_type"
        """
        try:
            llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.3)

            # Build conversation context from state
            conversation_context = cls._build_nlp_context(context)

            # Load external prompt template
            prompt_template = NLPParserPromptLoader.load()

            # Fill in template variables
            prompt = prompt_template.format(
                conversation_context=conversation_context,
                current_question=question_id if question_id else "Unknown",
                user_text=user_text,
            )

            response = await llm.ainvoke(prompt)
            parsed_data = json.loads(response.content.strip())

            answer = parsed_data.get("answer")
            inferred_question_id = parsed_data.get("question_id") or question_id
            confidence = parsed_data.get("confidence", 0.5)

            logger.info(
                f"Parsed NL input: '{user_text}' → {inferred_question_id}={answer} "
                f"(confidence: {confidence})"
            )

            return answer, inferred_question_id

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            # Fallback: return the text as-is
            return user_text, question_id
        except Exception as e:
            logger.error(f"Error parsing natural language input: {e}")
            raise


__all__ = ["RealEstateAgentService"]
