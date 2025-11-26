"""
Agent Profile Router
====================

API endpoints for agent profiling operations.
"""

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from typing import Optional
import json
import asyncio
from models.agent_profile import AgentProfilingResponse
from services.agent_profiling_service import AgentProfilingService
from services.supabase_service import SupabaseService
from services.agent_profiling_progress_service import AgentProfilingProgressService

router = APIRouter(
    prefix="/api/agent-profiles",
    tags=["Agent Profiles"]
)


@router.post("/process-all", response_model=AgentProfilingResponse)
async def process_all_agents():
    """
    Process all top agents and generate profiles using LLM (non-streaming)

    This endpoint:
    1. Fetches all top agents from crea_top_agents_3m_msgs_grouped view
    2. For each agent, sends their messages to LLM for profiling
    3. Stores/updates profiles in agent_profiles_clean table

    Returns:
        AgentProfilingResponse with processing statistics

    Example:
        POST /api/agent-profiles/process-all
    """
    try:
        print("[API-AgentProfile] Starting batch processing of all agents...")

        result = await AgentProfilingService.process_all_agents(SupabaseService)

        return AgentProfilingResponse(**result)

    except Exception as e:
        print(f"[API-AgentProfile] ✗ Error processing agents: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing agents: {str(e)}")


@router.post("/process-all-stream")
async def process_all_agents_stream():
    """
    Process all top agents with real-time streaming updates (SSE)

    Streams Server-Sent Events (SSE) after each agent is successfully:
    1. Profiled by LLM
    2. Saved to database
    3. Tracked in progress JSON file

    Returns:
        StreamingResponse with real-time updates

    Example:
        POST /api/agent-profiles/process-all-stream

    Event format:
        data: {"type": "start", "total_agents": 50}
        data: {"type": "progress", "agent_contact": "+91...", "status": "completed", "progress": "1/50"}
        data: {"type": "progress", "agent_contact": "+91...", "status": "failed", "error": "..."}
        data: {"type": "complete", "summary": {...}}
    """
    async def event_generator():
        try:
            print("[API-AgentProfile] Starting streaming batch processing...")

            # Fetch all agents
            all_agents = await SupabaseService.get_top_agents_grouped()

            if not all_agents:
                yield f"data: {json.dumps({'type': 'complete', 'message': 'No agents found'})}\n\n"
                return

            # Start session
            session_id = AgentProfilingProgressService.start_session(len(all_agents))

            # Filter completed agents
            agents = AgentProfilingProgressService.get_agents_to_process(all_agents)

            if not agents:
                yield f"data: {json.dumps({'type': 'complete', 'message': f'All {len(all_agents)} agents already processed'})}\n\n"
                return

            # Send start event
            yield f"data: {json.dumps({'type': 'start', 'total_agents': len(agents), 'session_id': session_id})}\n\n"

            profiles_processed = 0
            profiles_created = 0
            profiles_updated = 0
            errors = []

            # Process each agent
            for idx, agent_row in enumerate(agents, 1):
                agent_contact = agent_row.get("agent_contact", "unknown")

                try:
                    # Build LLM input
                    llm_input = AgentProfilingService.build_llm_input(agent_row)

                    # Call LLM for profiling
                    llm_output = await AgentProfilingService.profile_agent_with_llm(llm_input.model_dump())

                    # Prepare data for upsert
                    profile_data = {
                        "agent_contact": llm_output.agent_contact,
                        "agent_name": agent_row.get("agent_name"),
                        "company_name": agent_row.get("company_name"),
                        "sale_price_min": llm_output.sale_price_min,
                        "sale_price_max": llm_output.sale_price_max,
                        "rent_price_min": llm_output.rent_price_min,
                        "rent_price_max": llm_output.rent_price_max,
                        "bhk_min": llm_output.bhk_min,
                        "bhk_max": llm_output.bhk_max,
                        "supply_sale_count": llm_output.supply_sale_count,
                        "supply_rent_count": llm_output.supply_rent_count,
                        "demand_buy_count": llm_output.demand_buy_count,
                        "demand_rent_count": llm_output.demand_rent_count,
                        "primary_locations": llm_output.primary_locations,
                        "primary_property_types": llm_output.primary_property_types,
                        "profile_json": llm_output.model_dump(),
                        "summary_text": llm_output.summary_text,
                        "total_posts": agent_row.get("total_posts", 0),
                        "lookback_months": 3,
                        "messages_sampled": len(llm_input.sample_messages)
                    }

                    # Check if profile exists
                    existing_profile = await SupabaseService.get_agent_profile(agent_contact)

                    # Upsert to database
                    result = await SupabaseService.upsert_agent_profile(profile_data)

                    if result.get("success"):
                        profiles_processed += 1
                        if existing_profile:
                            profiles_updated += 1
                        else:
                            profiles_created += 1

                        # Mark as completed in progress tracker (JSON file)
                        AgentProfilingProgressService.mark_completed(agent_contact)

                        # Stream success event AFTER JSON entry is made
                        yield f"data: {json.dumps({'type': 'progress', 'agent_contact': agent_contact, 'status': 'completed', 'progress': f'{idx}/{len(agents)}', 'created': not existing_profile, 'summary': llm_output.summary_text[:100]})}\n\n"

                    else:
                        error_msg = result.get('message', 'Unknown error')
                        errors.append(f"{agent_contact}: {error_msg}")
                        AgentProfilingProgressService.mark_failed(agent_contact, error_msg)

                        # Stream error event
                        yield f"data: {json.dumps({'type': 'progress', 'agent_contact': agent_contact, 'status': 'failed', 'error': error_msg, 'progress': f'{idx}/{len(agents)}'})}\n\n"

                except Exception as e:
                    error_msg = str(e)
                    errors.append(f"{agent_contact}: {error_msg}")
                    AgentProfilingProgressService.mark_failed(agent_contact, error_msg)

                    # Stream error event
                    yield f"data: {json.dumps({'type': 'progress', 'agent_contact': agent_contact, 'status': 'failed', 'error': error_msg, 'progress': f'{idx}/{len(agents)}'})}\n\n"

                # Small delay to prevent overwhelming the client
                await asyncio.sleep(0.1)

            # Get final progress summary
            progress_summary = AgentProfilingProgressService.get_progress_summary()

            # Send completion event
            yield f"data: {json.dumps({'type': 'complete', 'summary': {'profiles_processed': profiles_processed, 'profiles_created': profiles_created, 'profiles_updated': profiles_updated, 'total_agents': len(all_agents), 'errors_count': len(errors), 'session_id': session_id, 'progress_summary': progress_summary}})}\n\n"

        except Exception as e:
            print(f"[API-AgentProfile] ✗ Streaming error: {str(e)}")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )


@router.post("/process/{agent_contact}")
async def process_single_agent(agent_contact: str):
    """
    Process a single agent by contact number (for testing)

    Args:
        agent_contact: Agent phone number (e.g., +919876543210)

    Returns:
        Processing result with agent profile data

    Example:
        POST /api/agent-profiles/process/+919876543210
    """
    try:
        print(f"[API-AgentProfile] Processing single agent: {agent_contact}")

        result = await AgentProfilingService.process_single_agent(agent_contact, SupabaseService)

        if not result.get("success"):
            raise HTTPException(status_code=404, detail=result.get("message"))

        return result

    except HTTPException:
        raise
    except Exception as e:
        print(f"[API-AgentProfile] ✗ Error processing agent {agent_contact}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing agent: {str(e)}")


@router.get("")
async def get_all_profiles(
    limit: int = Query(100, description="Maximum number of profiles to return"),
    offset: int = Query(0, description="Number of profiles to skip for pagination")
):
    """
    Get all agent profiles with pagination

    Args:
        limit: Maximum number of profiles (default: 100)
        offset: Number of profiles to skip (default: 0)

    Returns:
        List of agent profiles

    Example:
        GET /api/agent-profiles?limit=50&offset=0
    """
    try:
        print(f"[API-AgentProfile] Retrieving profiles (limit: {limit}, offset: {offset})")

        result = await SupabaseService.get_all_agent_profiles(limit=limit, offset=offset)

        return result

    except Exception as e:
        print(f"[API-AgentProfile] ✗ Error retrieving profiles: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving profiles: {str(e)}")


@router.get("/{agent_contact}")
async def get_agent_profile(agent_contact: str):
    """
    Get a specific agent profile by contact number

    Args:
        agent_contact: Agent phone number (e.g., +919876543210)

    Returns:
        Agent profile data

    Example:
        GET /api/agent-profiles/+919876543210
    """
    try:
        print(f"[API-AgentProfile] Retrieving profile for agent: {agent_contact}")

        profile = await SupabaseService.get_agent_profile(agent_contact)

        if not profile:
            raise HTTPException(status_code=404, detail=f"Profile not found for agent {agent_contact}")

        return {
            "success": True,
            "data": profile,
            "message": f"Profile found for {agent_contact}"
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[API-AgentProfile] ✗ Error retrieving profile: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving profile: {str(e)}")


# ============================================================================
# Progress Tracking Endpoints
# ============================================================================

@router.get("/progress/summary")
async def get_progress_summary():
    """
    Get current progress summary of agent profiling batch job

    Returns:
        Progress statistics including completed, failed, and remaining agents

    Example:
        GET /api/agent-profiles/progress/summary
    """
    try:
        print("[API-AgentProfile] Retrieving progress summary")

        summary = AgentProfilingProgressService.get_progress_summary()

        return {
            "success": True,
            "data": summary,
            "message": "Progress summary retrieved"
        }

    except Exception as e:
        print(f"[API-AgentProfile] ✗ Error retrieving progress: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving progress: {str(e)}")


@router.post("/progress/reset")
async def reset_progress():
    """
    Reset/clear the progress tracker

    Use this after a successful batch or to start fresh

    Returns:
        Confirmation message

    Example:
        POST /api/agent-profiles/progress/reset
    """
    try:
        print("[API-AgentProfile] Resetting progress tracker")

        AgentProfilingProgressService.reset_progress()

        return {
            "success": True,
            "message": "Progress tracker reset successfully"
        }

    except Exception as e:
        print(f"[API-AgentProfile] ✗ Error resetting progress: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error resetting progress: {str(e)}")
