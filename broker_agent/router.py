"""
Real Estate Agent API Router
=============================

FastAPI routes for the real estate agent conversation.

Endpoints:
- POST /api/broker_agent/sessions - Create new session
- GET /api/broker_agent/sessions/{session_id} - Get session state
- POST /api/broker_agent/sessions/{session_id}/answer - Submit answer (structured or chat, via type flag)
- GET /api/broker_agent/sessions/{session_id}/summary - Get user preference summary
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import logging

from .service import RealEstateAgentService
from .state import RealEstateAgentState

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/broker_agent", tags=["Real Estate Agent"])


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class CreateSessionRequest(BaseModel):
    """Request to create a new session"""
    pass


class CreateSessionResponse(BaseModel):
    """Response with new session ID"""
    session_id: str = Field(..., description="Unique session identifier")
    message: str = Field(..., description="Welcome message")


class SubmitAnswerRequest(BaseModel):
    """Request to submit an answer to a question"""
    answer: Any = Field(..., description="The user's answer or natural language text")
    question_id: Optional[str] = Field(
        None, description="ID of the question being answered (required for structured type)"
    )
    type: str = Field(
        default="structured",
        description="Type of input: 'structured' (UI controls), 'chat' (natural language), or 'initial_query' (multi-field extraction)"
    )


class ConversationResponse(BaseModel):
    """Response with current conversation state"""
    session_id: str = Field(..., description="Session identifier")
    current_question: Optional[Dict[str, Any]] = Field(
        None, description="Current question to ask user"
    )
    acknowledgment: Optional[str] = Field(
        None, description="LLM-generated acknowledgment for the last answer"
    )
    additional_type: Optional[str] = Field(
        None, description="Type of micro-interaction: 'nudge', 'comment', 'insight', or None"
    )
    additional_text: Optional[str] = Field(
        None, description="Optional nudge, comment, or insight to accompany the acknowledgment"
    )
    processed_answer: Optional[Any] = Field(
        None, description="The answer that was just processed (for UI update)"
    )
    processed_question_id: Optional[str] = Field(
        None, description="Which question was answered (for UI update)"
    )
    why_question: bool = Field(
        False, description="True if the current response is asking a 'why' follow-up question"
    )
    completed: bool = Field(False, description="Whether conversation is complete")
    user_summary: Dict[str, Any] = Field(
        default_factory=dict, description="Summary of user preferences"
    )
    messages: List[Dict[str, str]] = Field(
        default_factory=list, description="Conversation history"
    )


class UserSummaryResponse(BaseModel):
    """
    Summary of user's property preferences.

    Keys align with question IDs from the conversation flow:
    - req_type → Transaction type (buy/sell)
    - proximity_location → Location preference
    - budget → Budget range (min/max)
    - property_area → Property area range (min/max)
    - property_type → Property type preference
    - special_requests → Special features requested
    """
    req_type: Optional[str]
    proximity_location: Optional[str]
    budget: Dict[str, Optional[float]]
    property_area: Dict[str, Optional[int]]
    property_type: Optional[str]
    special_requests: List[str]


# ============================================================================
# ROUTES
# ============================================================================

# Store sessions in memory (in production, use database)
_sessions: Dict[str, RealEstateAgentState] = {}


@router.post("/sessions", response_model=CreateSessionResponse)
async def create_session(request: CreateSessionRequest) -> CreateSessionResponse:
    """
    Create a new real estate agent conversation session.

    This initializes a new conversation and returns a session ID
    that should be used for subsequent interactions.

    Returns:
        CreateSessionResponse: Session ID and welcome message

    Example:
        ```
        POST /api/broker_agent/sessions
        {}

        {
            "session_id": "550e8400-e29b-41d4-a716-446655440000",
            "message": "Welcome to the Real Estate Agent! Let's find your perfect property."
        }
        ```
    """
    try:
        session_id = RealEstateAgentService.create_session()
        state = RealEstateAgentService.create_initial_state(session_id)

        # Get first question
        state = await RealEstateAgentService.get_next_question(state)

        _sessions[session_id] = state

        return CreateSessionResponse(
            session_id=session_id,
            message="Welcome to the Real Estate Agent! Let's find your perfect property.",
        )

    except Exception as e:
        logger.error(f"Error creating session: {e}")
        raise HTTPException(status_code=500, detail="Failed to create session")


@router.get("/sessions/{session_id}", response_model=ConversationResponse)
async def get_session(session_id: str) -> ConversationResponse:
    """
    Get current state of a conversation session.

    Returns the current question to ask and conversation history.

    Args:
        session_id (str): Session identifier

    Returns:
        ConversationResponse: Current conversation state

    Example:
        ```
        GET /api/broker_agent/sessions/550e8400-e29b-41d4-a716-446655440000

        {
            "session_id": "550e8400-e29b-41d4-a716-446655440000",
            "current_question": {
                "id": "transaction_type",
                "question": "Are you looking to buy or sell a property?",
                ...
            },
            "message": "Are you looking to buy or sell a property?",
            "completed": false,
            "user_summary": {...},
            "messages": [...]
        }
        ```
    """
    try:
        if session_id not in _sessions:
            raise HTTPException(status_code=404, detail="Session not found")

        state = _sessions[session_id]
        user_summary = RealEstateAgentService.get_user_summary(state)

        return ConversationResponse(
            session_id=session_id,
            current_question=state.get("current_question"),
            acknowledgment=state.get("last_response_text"),
            additional_type=state.get("additional_type"),
            additional_text=state.get("additional_text"),
            why_question=state.get("is_asking_why", False),
            completed=state.get("completed", False),
            user_summary=user_summary,
            messages=state.get("messages", []),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting session {session_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get session")


@router.post("/sessions/{session_id}/answer", response_model=ConversationResponse)
async def submit_answer(
    session_id: str, request: SubmitAnswerRequest
) -> ConversationResponse:
    """
    Submit an answer to the current question.

    Supports three types of input:
    1. **Structured** (UI controls): Pre-structured data with question_id
    2. **Chat** (Natural language): Free-form text answering the current question
    3. **Initial Query** (Multi-field extraction): Free-form query that extracts multiple fields at once

    Updates the conversation state with the user's answer
    and returns the next question to ask.

    Args:
        session_id (str): Session identifier
        request (SubmitAnswerRequest): User's answer, question ID, and input type

    Returns:
        ConversationResponse: Updated conversation state with next question

    Examples:
        **Structured Input (from UI controls):**
        ```
        POST /api/broker_agent/sessions/{id}/answer
        {
            "answer": "buy",
            "question_id": "req_type",
            "type": "structured"
        }
        ```

        **Chat Input (natural language answer to current question):**
        ```
        POST /api/broker_agent/sessions/{id}/answer
        {
            "answer": "I prefer locations near my office",
            "type": "chat"
        }
        ```

        **Initial Query Input (multi-field extraction):**
        ```
        POST /api/broker_agent/sessions/{id}/answer
        {
            "answer": "3bhk in indiranagar",
            "type": "initial_query"
        }
        ```

        **Response (same for all):**
        ```
        {
            "session_id": "550e8400-e29b-41d4-a716-446655440000",
            "current_question": {
                "id": "budget",
                "question": "What's your budget range?",
                ...
            },
            "message": "Great! I see you're looking for a 3BHK in Indiranagar. What's your budget range?",
            "acknowledgment": "3BHK in Indiranagar...",
            "completed": false,
            "user_summary": {...},
            "messages": [...]
        }
        ```
    """
    try:
        if session_id not in _sessions:
            raise HTTPException(status_code=404, detail="Session not found")

        state = _sessions[session_id]

        # Route based on input type
        if request.type == "initial_query":
            # Initial query with multi-field extraction
            state = await RealEstateAgentService.process_initial_query(
                state, request.answer
            )
        elif request.type == "chat":
            # Natural language input - LLM will parse
            state = await RealEstateAgentService.process_chat_input(
                state, request.answer
            )
        else:
            # Structured input - direct processing
            state = await RealEstateAgentService.process_user_input(
                state, request.answer, request.question_id
            )

        # Update session
        _sessions[session_id] = state

        user_summary = RealEstateAgentService.get_user_summary(state)

        return ConversationResponse(
            session_id=session_id,
            current_question=state.get("current_question"),
            acknowledgment=state.get("last_response_text"),
            additional_type=state.get("additional_type"),
            additional_text=state.get("additional_text"),
            processed_answer=state.get("last_processed_answer"),
            processed_question_id=state.get("last_processed_question_id"),
            why_question=state.get("is_asking_why", False),
            completed=state.get("completed", False),
            user_summary=user_summary,
            messages=state.get("messages", []),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error submitting answer for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to process answer")


@router.get("/sessions/{session_id}/summary", response_model=UserSummaryResponse)
async def get_user_summary(session_id: str) -> UserSummaryResponse:
    """
    Get summary of user's property preferences.

    Args:
        session_id (str): Session identifier

    Returns:
        UserSummaryResponse: Summary of user preferences

    Example:
        ```
        GET /api/broker_agent/sessions/550e8400-e29b-41d4-a716-446655440000/summary

        {
            "req_type": "buy",
            "proximity_location": "Indiranagar",
            "budget": {
                "min": 50.0,
                "max": 100.0
            },
            "property_area": {
                "min": 1000,
                "max": 2500
            },
            "property_type": "apartment",
            "special_requests": ["gym", "pool", "parking"]
        }
        ```
    """
    try:
        if session_id not in _sessions:
            raise HTTPException(status_code=404, detail="Session not found")

        state = _sessions[session_id]
        summary = RealEstateAgentService.get_user_summary(state)

        return UserSummaryResponse(**summary)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting summary for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get summary")


# ============================================================================
# EXPORT
# ============================================================================

__all__ = ["router"]
