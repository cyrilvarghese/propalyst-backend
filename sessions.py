"""
Session Management for Propalyst
=================================

This module handles session state persistence across HTTP requests.

Key Concepts:
-------------
1. Session = Conversation instance with unique ID
2. State = All user data + conversation history for that session
3. Persistence = In-memory dict (simple for now)

Why Sessions?
-------------
Without sessions:
    Request 1: "Whitefield" → state lost
    Request 2: "Yes" → doesn't know previous answer

With sessions:
    Request 1: "Whitefield" → saved to sessions["abc-123"]
    Request 2: "Yes" → retrieves sessions["abc-123"], still has "Whitefield"!

This is what makes multi-turn conversations possible.

Future enhancements:
- Redis for distributed systems
- Database for long-term persistence
- Session expiration/cleanup
"""

from typing import Dict
from agent.state import PropalystState, create_propalyst_state


# ============================================================================
# IN-MEMORY SESSION STORAGE
# ============================================================================

# Simple dict to store all active sessions
# Key: session_id (UUID string)
# Value: PropalystState with all conversation data
sessions: Dict[str, PropalystState] = {}


# ============================================================================
# SESSION MANAGEMENT FUNCTIONS
# ============================================================================

def get_session(session_id: str) -> PropalystState:
    """
    Get or create a session.

    If session exists, returns saved state (with all previous answers).
    If new session, creates fresh PropalystState.

    Args:
        session_id (str): Unique session identifier (UUID)

    Returns:
        PropalystState: Current state for this session

    Examples:
        >>> # First request - new session
        >>> state = get_session("abc-123")
        >>> state["work_location"]
        None

        >>> # Later request - existing session
        >>> state["work_location"] = "Whitefield"
        >>> update_session("abc-123", state)
        >>>
        >>> # Next request gets saved data
        >>> state = get_session("abc-123")
        >>> state["work_location"]
        "Whitefield"  ← Still there!
    """
    if session_id not in sessions:
        print(f"🆕 Creating new session: {session_id}")
        sessions[session_id] = create_propalyst_state(session_id)
    else:
        print(f"♻️  Retrieved existing session: {session_id}")

    return sessions[session_id]


def update_session(session_id: str, state: PropalystState):
    """
    Save updated state back to session storage.

    Call this after processing user input to persist changes.

    Args:
        session_id (str): Session to update
        state (PropalystState): Updated state to save

    Examples:
        >>> state = get_session("abc-123")
        >>> state["work_location"] = "Whitefield"
        >>> update_session("abc-123", state)  ← Saves changes
    """
    print(f"💾 Updating session: {session_id}")
    sessions[session_id] = state


def delete_session(session_id: str):
    """
    Delete a session (cleanup).

    Use when:
    - User completes flow and closes browser
    - Session expires
    - User explicitly resets conversation

    Args:
        session_id (str): Session to delete

    Examples:
        >>> delete_session("abc-123")
        >>> get_session("abc-123")  # Creates new empty session
    """
    if session_id in sessions:
        print(f"🗑️  Deleting session: {session_id}")
        del sessions[session_id]
    else:
        print(f"⚠️  Session not found: {session_id}")


def list_sessions() -> list[str]:
    """
    Get all active session IDs.

    Useful for debugging or admin dashboards.

    Returns:
        list[str]: List of session IDs

    Examples:
        >>> list_sessions()
        ["abc-123", "def-456", "ghi-789"]
    """
    return list(sessions.keys())


def get_session_count() -> int:
    """
    Count active sessions.

    Returns:
        int: Number of active sessions

    Examples:
        >>> get_session_count()
        3
    """
    return len(sessions)


# ============================================================================
# SESSION DEBUGGING HELPERS
# ============================================================================

def print_session_state(session_id: str):
    """
    Print current state of a session (for debugging).

    Args:
        session_id (str): Session to inspect

    Examples:
        >>> print_session_state("abc-123")
        Session: abc-123
        ─────────────────
        work_location: Whitefield
        has_kids: True
        commute_time_max: 30
        property_type: None
        budget_max: None
        current_step: 3
    """
    if session_id not in sessions:
        print(f"❌ Session not found: {session_id}")
        return

    state = sessions[session_id]
    print(f"\nSession: {session_id}")
    print("─" * 50)
    print(f"  work_location: {state.get('work_location')}")
    print(f"  has_kids: {state.get('has_kids')}")
    print(f"  commute_time_max: {state.get('commute_time_max')}")
    print(f"  property_type: {state.get('property_type')}")
    print(f"  budget_max: {state.get('budget_max')}")
    print(f"  current_step: {state.get('current_step')}")
    print(f"  messages: {len(state.get('messages', []))} messages")
    print("─" * 50 + "\n")


# ============================================================================
# EXPORT
# ============================================================================

__all__ = [
    "get_session",
    "update_session",
    "delete_session",
    "list_sessions",
    "get_session_count",
    "print_session_state"
]
