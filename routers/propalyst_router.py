"""
Propalyst Router
================

API endpoints for Propalyst conversational Q&A functionality.
"""

import os
from fastapi import APIRouter, HTTPException
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from models.propalyst import (
    PropalystChatRequest,
    PropalystChatResponse,
    PropalystSummaryRequest,
    PropalystSummaryResponse,
    PropalystAreasRequest,
    PropalystAreasResponse
)
from agent.graph import create_propalyst_graph
from agent.nodes.propalyst_qa import process_user_answer
from sessions import get_session, update_session

router = APIRouter(
    prefix="/api/propalyst",
    tags=["Propalyst"]
)


@router.post("/chat", response_model=PropalystChatResponse)
async def propalyst_chat(request: PropalystChatRequest):
    """
    Propalyst conversational Q&A endpoint.

    This endpoint handles multi-step conversations with session persistence:
    1. Initial request → Ask Q1 (work location)
    2. User answers Q1 → Ask Q2 (kids)
    3. User answers Q2 → Ask Q3 (commute)
    ... and so on

    State persists across requests via session_id.

    Args:
        request (PropalystChatRequest): Request with session_id and optional user_input

    Returns:
        PropalystChatResponse: Next question or results

    Flow:
        Request 1:
        POST /api/propalyst/chat
        {
            "session_id": "abc-123",
            "user_input": null
        }
        → Response: Q1 (work location)

        Request 2:
        POST /api/propalyst/chat
        {
            "session_id": "abc-123",
            "user_input": "Whitefield",
            "field": "work_location"
        }
        → State saves "Whitefield"
        → Response: Q2 (kids)

        ... and so on for Q3, Q4, Q5
    """

    print(f"\n💬 Propalyst Chat - Session: {request.session_id}")

    try:
        # Import graph instance from graphs module
        from graphs import propalyst_graph

        # Step 1: Get or create session state
        state = get_session(request.session_id)

        # Step 2: If user provided input, process it
        if request.user_input and request.field:
            print(f"   📝 Processing answer for field: {request.field}")
            print(f"   💭 User input: {request.user_input}")

            # Parse and update state with user's answer
            state = await process_user_answer(state, request.field, request.user_input)

        # Step 3: Run graph to get next question or results
        print("   🔄 Running Propalyst graph...")
        updated_state = await propalyst_graph.ainvoke(state)

        # Step 4: Save updated state
        update_session(request.session_id, updated_state)

        # Step 5: Extract component and message
        component = updated_state.get("component")
        message = updated_state.get("message", "")
        current_step = updated_state.get("current_step", 1)

        # Step 6: Check if conversation is complete (all 5 questions answered)
        completed = (
            updated_state.get("work_location") is not None and
            updated_state.get("has_kids") is not None and
            updated_state.get("commute_time_max") is not None and
            updated_state.get("property_type") is not None and
            updated_state.get("budget_max") is not None
        )

        print(f"   ✅ Step {current_step}/5, Completed: {completed}")

        # Step 7: Convert component to dict
        component_dict = None
        if component:
            component_dict = {
                "type": component.type,
                "props": component.props
            }

        # Step 8: Return response
        return PropalystChatResponse(
            component=component_dict,
            message=message,
            session_id=request.session_id,
            current_step=current_step,
            completed=completed
        )

    except Exception as e:
        error_message = f"Propalyst chat error: {str(e)}"
        print(f"   ❌ {error_message}")

        raise HTTPException(
            status_code=500,
            detail=error_message
        )


@router.post("/summary", response_model=PropalystSummaryResponse)
async def propalyst_summary(request: PropalystSummaryRequest):
    """
    Generate LLM-based conversation summary.

    This endpoint:
    1. Retrieves the completed conversation state
    2. Uses LLM to generate a detailed, contextual summary
    3. Returns the summary for display in textarea

    Args:
        request (PropalystSummaryRequest): Request with session_id

    Returns:
        PropalystSummaryResponse: LLM-generated summary

    Example:
        Request:
        POST /api/propalyst/summary
        {
            "session_id": "abc-123"
        }

        Response:
        {
            "summary": "Based on our conversation, you're looking for a Villa in Whitefield...",
            "session_id": "abc-123"
        }
    """

    print(f"\n📝 Generating summary for session: {request.session_id}")

    try:
        # Step 1: Get session state
        state = get_session(request.session_id)

        # Step 2: Extract collected data
        work_location = state.get("work_location")
        has_kids = state.get("has_kids")
        commute_time_max = state.get("commute_time_max")
        property_type = state.get("property_type")
        budget_max = state.get("budget_max")

        # Step 3: Generate summary using LLM
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found")

        llm = ChatOpenAI(
            api_key=api_key,
            model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
            temperature=0.7
        )

        prompt = f"""You are a helpful real estate assistant. Generate a friendly, detailed summary that introduces the AREAS we're recommending based on the user's requirements.

User's preferences:
- Work Location: {work_location}
- Has Kids: {"Yes" if has_kids else "No"}
- Maximum Commute Time: {commute_time_max} minutes
- Property Type: {property_type}
- Maximum Budget: ₹{budget_max:,}

Generate a 2-3 sentence summary that:
1. Briefly acknowledges their key requirements (work location, family needs, budget, commute)
2. Explicitly states "Here are the areas we suggest based on your requirements" or similar phrasing
3. Sounds warm and personalized

Important: Emphasize that these are AREA recommendations, not individual properties. The summary should introduce the areas shown below.

Do not use bullet points. Write in paragraph form. Be conversational and friendly."""

        messages = [
            SystemMessage(content="You are a friendly real estate assistant helping users find their perfect home."),
            HumanMessage(content=prompt)
        ]

        print("   🤖 Generating summary with LLM...")
        response = await llm.ainvoke(messages)
        summary = response.content.strip()

        print(f"   ✅ Summary generated: {summary[:100]}...")

        return PropalystSummaryResponse(
            summary=summary,
            session_id=request.session_id
        )

    except Exception as e:
        error_message = f"Summary generation error: {str(e)}"
        print(f"   ❌ {error_message}")

        raise HTTPException(
            status_code=500,
            detail=error_message
        )


@router.post("/areas", response_model=PropalystAreasResponse)
async def propalyst_areas(request: PropalystAreasRequest):
    """
    Get recommended areas for a completed session.

    This endpoint:
    1. Retrieves the session state
    2. If areas not yet calculated, triggers the calculate_areas node
    3. Returns recommended areas from state

    Args:
        request (PropalystAreasRequest): Request with session_id

    Returns:
        PropalystAreasResponse: List of recommended areas

    Example:
        Request:
        POST /api/propalyst/areas
        {
            "session_id": "abc-123"
        }

        Response:
        {
            "areas": [
                {
                    "areaName": "Whitefield",
                    "image": "https://...",
                    "childFriendlyScore": 9,
                    ...
                }
            ],
            "session_id": "abc-123"
        }
    """

    print(f"\n🏘️  Fetching areas for session: {request.session_id}")

    # Add delay to test skeleton loader (3 seconds)
    import asyncio
    await asyncio.sleep(3)

    try:
        # Import graph instance from graphs module
        from graphs import propalyst_graph

        # Step 1: Get session state
        state = get_session(request.session_id)

        # Step 2: Check if areas already calculated
        if not state.get("calculated"):
            print("   ⚠️  Areas not yet calculated, triggering calculate_areas node...")

            # Run graph to trigger calculate_areas node
            updated_state = await propalyst_graph.ainvoke(state)

            # Save updated state
            update_session(request.session_id, updated_state)
            state = updated_state

        # Step 3: Extract recommended areas
        recommended_areas = state.get("recommended_areas", [])

        print(f"   ✅ Returning {len(recommended_areas)} recommended areas")

        return PropalystAreasResponse(
            areas=recommended_areas,
            session_id=request.session_id
        )

    except Exception as e:
        error_message = f"Areas fetch error: {str(e)}"
        print(f"   ❌ {error_message}")

        raise HTTPException(
            status_code=500,
            detail=error_message
        )

