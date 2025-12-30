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

import google.generativeai as genai

from .state import RealEstateAgentState, create_real_estate_state
from .graph import create_real_estate_agent_graph
from .utils import clean_llm_response
from .nodes.acknowledge import (
    build_conversation_context,
    get_question_id_to_state_key_mapping,
)

logger = logging.getLogger(__name__)


# ============================================================================
# QUESTION ID TO STATE KEY MAPPING
# ============================================================================
#
# Question IDs (from nodes/questions.py) → State Field Names:
#   "req_type"              → req_type
#   "proximity_location"    → proximity_location
#   "budget"                → price_min, price_max
#   "property_area"         → area_min, area_max
#   "property_type"         → property_type
#   "special_requests"      → special_features
#   "taste_preference"      → taste_preference
#
# Use get_question_id_to_state_key_mapping() for programmatic access.
# ============================================================================


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


class InitialQueryParserPromptLoader:
    """Loads and caches the initial query parser prompt template"""

    PROMPT_FILE = Path(__file__).parent.parent / "prompts" / "initial_query_parser.txt"
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

        elif current_question_id == "bedroom_count":
            # Expect integer (1-5)
            state = {**state, "bedroom_count": user_input}
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

        elif current_question_id == "taste_preference":
            # Expect list of property preferences with ratings
            if isinstance(user_input, list):
                # Enrich with full property details from config
                enriched_preferences = cls._enrich_taste_preferences(user_input)
                state = {**state, "taste_preference": enriched_preferences}
                answer_for_acknowledgment = enriched_preferences

        # Mark this question as asked (to prevent repetition in router)
        if current_question_id:
            questions_asked = list(state.get("questions_asked", []))
            if current_question_id not in questions_asked:
                questions_asked.append(current_question_id)
            state = {**state, "questions_asked": questions_asked}

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
    async def process_initial_query(
        cls,
        state: RealEstateAgentState,
        initial_query: str,
    ) -> RealEstateAgentState:
        """
        Process initial free-form query and extract all answerable fields.

        This method is designed for initial queries that can extract multiple
        fields at once (e.g., "3bhk in indiranagar" extracts property_type,
        proximity_location, and property_area).

        Flow:
        1. Call LLM with initial_query_parser prompt
        2. Extract all non-null fields from response
        3. Map to state keys (req_type, proximity_location, price_min/max, etc.)
        4. Update state with all extracted fields
        5. Add all answered question_ids to questions_asked list
        6. Invoke graph to get next unanswered question

        Args:
            state (RealEstateAgentState): Current conversation state
            initial_query (str): Free-form query (e.g., "3bhk in indiranagar")

        Returns:
            RealEstateAgentState: Updated state with extracted fields and next question

        Example:
            >>> state = RealEstateAgentService.create_initial_state("session-123")
            >>> state = await RealEstateAgentService.process_initial_query(
            ...     state, "3bhk in indiranagar"
            ... )
            >>> print(state["proximity_location"])
            "Indiranagar"
            >>> print(state["questions_asked"])
            ["proximity_location", "property_area", "property_type"]
        """
        try:
            # Load prompt template
            prompt_template = InitialQueryParserPromptLoader.load()

            # Fill in template
            prompt = prompt_template.format(user_query=initial_query)

            # Call LLM
            model = genai.GenerativeModel(
                model_name="gemini-2.5-flash",
                generation_config=genai.types.GenerationConfig(
                    temperature=0.3,  # Low temp for consistent extraction
                ),
            )

            response = await model.generate_content_async(prompt)
            cleaned_response = clean_llm_response(response.text, format_type="json")
            extracted_data = json.loads(cleaned_response)

            # Track questions that were answered
            questions_answered = list(state.get("questions_asked", []))

            # Log what fields were extracted
            extracted_fields = []
            if extracted_data.get("req_type"):
                extracted_fields.append(f"req_type={extracted_data['req_type']}")
            if extracted_data.get("proximity_location"):
                extracted_fields.append(f"location={extracted_data['proximity_location']}")
            if extracted_data.get("budget"):
                extracted_fields.append(f"budget=₹{extracted_data['budget'][0]:.1f}-{extracted_data['budget'][1]:.1f}Cr")
            if extracted_data.get("property_area"):
                extracted_fields.append(f"area={extracted_data['property_area'][0]:,}-{extracted_data['property_area'][1]:,}sqft")
            if extracted_data.get("property_type"):
                extracted_fields.append(f"type={extracted_data['property_type']}")
            if extracted_data.get("bedroom_count"):
                extracted_fields.append(f"bedrooms={extracted_data['bedroom_count']}BHK")
            if extracted_data.get("special_features"):
                extracted_fields.append(f"features={extracted_data['special_features']}")

            print(f"✅ Extracted: {', '.join(extracted_fields) if extracted_fields else 'nothing'}")

            # Map extracted fields to state keys
            if extracted_data.get("req_type"):
                state = {**state, "req_type": extracted_data["req_type"]}
                if "req_type" not in questions_answered:
                    questions_answered.append("req_type")

            if extracted_data.get("proximity_location"):
                state = {**state, "proximity_location": extracted_data["proximity_location"]}
                if "proximity_location" not in questions_answered:
                    questions_answered.append("proximity_location")

            if extracted_data.get("budget"):
                budget = extracted_data["budget"]
                state = {
                    **state,
                    "price_min": budget[0],
                    "price_max": budget[1],
                }
                if "budget" not in questions_answered:
                    questions_answered.append("budget")

            if extracted_data.get("property_area"):
                area = extracted_data["property_area"]
                state = {
                    **state,
                    "area_min": area[0],
                    "area_max": area[1],
                }
                if "property_area" not in questions_answered:
                    questions_answered.append("property_area")

            if extracted_data.get("bedroom_count"):
                state = {**state, "bedroom_count": extracted_data["bedroom_count"]}
                if "bedroom_count" not in questions_answered:
                    questions_answered.append("bedroom_count")

            if extracted_data.get("property_type"):
                state = {**state, "property_type": extracted_data["property_type"]}
                if "property_type" not in questions_answered:
                    questions_answered.append("property_type")

            if extracted_data.get("special_features"):
                state = {**state, "special_features": extracted_data["special_features"]}
                if "special_features" not in questions_answered:
                    questions_answered.append("special_features")

            # Update questions_asked list
            state = {**state, "questions_asked": questions_answered}

            # Log state after extraction
            newly_answered = [q for q in questions_answered if q not in state.get("questions_asked", [])]
            state_summary = {
                "req_type": state.get("req_type"),
                "proximity_location": state.get("proximity_location"),
                "budget": f"₹{state.get('price_min', 0):.1f}-₹{state.get('price_max', 0):.1f}Cr" if state.get("price_min") else None,
                "property_area": f"{state.get('area_min', 0):,}-{state.get('area_max', 0):,}sqft" if state.get("area_min") else None,
                "bedroom_count": f"{state.get('bedroom_count')}BHK" if state.get("bedroom_count") else None,
                "property_type": state.get("property_type"),
                "special_features": state.get("special_features"),
            }
            # Remove None values from summary
            state_summary = {k: v for k, v in state_summary.items() if v is not None}

            print(f"📋 State after extraction:")
            for key, value in state_summary.items():
                print(f"   • {key}: {value}")
            print(f"✅ Questions answered: {', '.join(questions_answered) if questions_answered else 'none'}")

            # Add user message to conversation history
            messages = list(state.get("messages", []))
            messages.append(
                {
                    "role": "user",
                    "content": initial_query,
                }
            )
            state = {**state, "messages": messages}

            # Store extracted data in state to mark as answered
            if extracted_data.get("req_type"):
                state["req_type"] = extracted_data.get("req_type")

            if extracted_data.get("proximity_location"):
                state["proximity_location"] = extracted_data.get("proximity_location")

            if extracted_data.get("budget"):
                state["price_min"] = extracted_data["budget"][0]
                state["price_max"] = extracted_data["budget"][1]

            if extracted_data.get("property_area"):
                state["area_min"] = extracted_data["property_area"][0]
                state["area_max"] = extracted_data["property_area"][1]

            if extracted_data.get("bedroom_count"):
                state["bedroom_count"] = extracted_data.get("bedroom_count")

            if extracted_data.get("property_type"):
                state["property_type"] = extracted_data.get("property_type")

            if extracted_data.get("special_features"):
                state["special_features"] = extracted_data.get("special_features")

            # Set pending fields to trigger acknowledge node
            # This makes the acknowledge node generate a response based on the extracted fields
            state = {
                **state,
                "pending_answer": initial_query,
                "pending_question_id": "initial_query",
            }

            # Invoke graph to get next question (router will skip already-asked)
            print(f"📊 Extracted fields: {', '.join([k for k, v in [('req_type', extracted_data.get('req_type')), ('location', extracted_data.get('proximity_location')), ('budget', extracted_data.get('budget')), ('area', extracted_data.get('property_area')), ('bedrooms', extracted_data.get('bedroom_count')), ('type', extracted_data.get('property_type')), ('features', extracted_data.get('special_features'))] if v])}")
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

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            print(f"   ❌ JSON parse error: {e}")
            # Fallback: treat as if no initial query and get first question
            return await cls.get_next_question(state)
        except Exception as e:
            logger.error(f"Error processing initial query: {e}")
            print(f"   ❌ Error: {e}")
            # Fallback: treat as if no initial query
            return await cls.get_next_question(state)

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
        # Use shared utility function for consistency
        return build_conversation_context(state)

    @staticmethod
    def _enrich_taste_preferences(preferences: list) -> list:
        """
        Enrich taste preference data with full property details from config.

        Takes preference data (with propertyId, liked, reason) and adds complete
        property details from the taste_preference question configuration.

        Args:
            preferences: List of preference dicts with propertyId, liked, etc.

        Returns:
            List of enriched preference dicts with full property details
        """
        from .questions_config import get_question_by_id

        taste_config = get_question_by_id("taste_preference")
        if not taste_config:
            return preferences

        # Create a map of property ID to property data
        property_map = {}
        for prop in taste_config.control_data.get("properties", []):
            property_map[prop["id"]] = prop

        # Enrich each preference with property details
        enriched = []
        for pref in preferences:
            property_id = pref.get("propertyId") or pref.get("property_id")
            if property_id and property_id in property_map:
                enriched_pref = {
                    **property_map[property_id],  # Include all property details
                    "liked": pref.get("liked"),   # Add user's preference
                    "reason": pref.get("reason"),  # Add optional reason
                }
                enriched.append(enriched_pref)

        return enriched if enriched else preferences

    @staticmethod
    def get_user_summary(state: RealEstateAgentState) -> Dict[str, Any]:
        """
        Get a summary of user's preferences from state.

        Response keys align with question IDs from get_question_id_to_state_key_mapping():
        - "req_type" → req_type
        - "proximity_location" → proximity_location
        - "budget" → price_min, price_max
        - "property_area" → area_min, area_max
        - "bedroom_count" → bedroom_count
        - "property_type" → property_type
        - "special_requests" → special_features
        - "taste_preference" → taste_preference

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
            ...     "bedroom_count": 3,
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
            "budget": {
                "min": state.get("price_min"),
                "max": state.get("price_max"),
            },
            "property_area": {
                "min": state.get("area_min"),
                "max": state.get("area_max"),
            },
            "bedroom_count": state.get("bedroom_count"),
            "property_type": state.get("property_type"),
            "special_requests": state.get("special_features", []),
            "taste_preference": state.get("taste_preference", []),
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
            model = genai.GenerativeModel(
                model_name="gemini-2.5-flash",
                generation_config=genai.types.GenerationConfig(
                    temperature=0.3,
                ),
            )

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

            response = await model.generate_content_async(prompt)
            cleaned_response = clean_llm_response(response.text, format_type="json")
            parsed_data = json.loads(cleaned_response)

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
