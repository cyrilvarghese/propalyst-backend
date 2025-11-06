"""
FastAPI Application - Project 1: Dynamic UI Generator
======================================================

This is the main entry point for the backend API.

Key Components:
---------------
1. FastAPI app with CORS
2. Environment variable loading
3. API endpoints for UI generation
4. LangGraph workflow integration

Endpoints:
----------
GET  /              Health check
POST /api/generate-ui   Generate UI component from natural language

Run with:
---------
uvicorn main:app --reload --port 8000
"""

import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

from agent import create_ui_generator_graph, AgentState
from agent.graph import create_propalyst_graph
from agent.state import PropalystState
from agent.nodes.propalyst_qa import process_user_answer
from sessions import get_session, update_session

# Load environment variables from .env file
load_dotenv()

# ============================================================================
# FASTAPI APPLICATION SETUP
# ============================================================================

app = FastAPI(
    title="Dynamic UI Generator API",
    description="LangGraph-powered API for generating UI components from natural language",
    version="1.0.0",
    docs_url="/docs",  # Swagger UI
    redoc_url="/redoc"  # ReDoc alternative
)

# ============================================================================
# CORS CONFIGURATION
# ============================================================================

# Get allowed origins from environment variable
# Default to multiple localhost ports for development
cors_origins_str = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:3001,http://localhost:3002,http://localhost:3003")
cors_origins = [origin.strip() for origin in cors_origins_str.split(",")]

print(f"🌐 CORS enabled for origins: {cors_origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,  # Frontend URL(s)
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)

# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class GenerateUIRequest(BaseModel):
    """
    Request model for UI generation endpoint.

    Attributes:
        user_input (str): Natural language description of desired UI component

    Example:
        {
            "user_input": "checkbox with options Apple, Banana, Orange"
        }
    """
    user_input: str

    class Config:
        schema_extra = {
            "example": {
                "user_input": "button with label 'Submit'"
            }
        }


class UIComponentResponse(BaseModel):
    """
    Response model for successful UI generation.

    Attributes:
        type (str): Component type (e.g., "Button", "Slider")
        props (dict): Component properties

    Example:
        {
            "type": "Button",
            "props": {
                "label": "Submit",
                "variant": "primary"
            }
        }
    """
    type: str
    props: dict


class GenerateUIResponse(BaseModel):
    """
    Complete response from UI generation endpoint.

    Attributes:
        component (UIComponentResponse): The generated component configuration
        message (str): Human-readable message
        success (bool): Whether generation was successful

    Example:
        {
            "component": {
                "type": "Button",
                "props": {"label": "Submit"}
            },
            "message": "Here's a Button component",
            "success": true
        }
    """
    component: UIComponentResponse | None
    message: str
    success: bool


# ============================================================================
# PROPALYST REQUEST/RESPONSE MODELS (Project 2)
# ============================================================================

class PropalystChatRequest(BaseModel):
    """
    Request model for Propalyst conversational endpoint.

    Attributes:
        session_id (str): Unique session identifier (UUID)
        user_input (str | None): User's answer (None for initial request)
        field (str | None): Which field this answer is for

    Examples:
        Initial request (start conversation):
        {
            "session_id": "abc-123",
            "user_input": null
        }

        User answering Q1:
        {
            "session_id": "abc-123",
            "user_input": "Whitefield",
            "field": "work_location"
        }

        User answering Q2:
        {
            "session_id": "abc-123",
            "user_input": "Yes",
            "field": "has_kids"
        }
    """
    session_id: str
    user_input: str | None = None
    field: str | None = None

    class Config:
        schema_extra = {
            "example": {
                "session_id": "abc-123",
                "user_input": "Whitefield",
                "field": "work_location"
            }
        }


class PropalystChatResponse(BaseModel):
    """
    Response model for Propalyst chat endpoint.

    Attributes:
        component (dict | None): UI component to show
        message (str): Agent's message to user
        session_id (str): Session identifier
        current_step (int): Current question number (1-5)
        completed (bool): Whether all questions answered

    Example:
        {
            "component": {
                "type": "TextInput",
                "props": {
                    "field": "work_location",
                    "placeholder": "e.g., Whitefield"
                }
            },
            "message": "Hi! Where do you work?",
            "session_id": "abc-123",
            "current_step": 1,
            "completed": false
        }
    """
    component: dict | None
    message: str
    session_id: str
    current_step: int
    completed: bool


class PropalystSummaryRequest(BaseModel):
    """
    Request model for generating conversation summary.

    Attributes:
        session_id (str): Unique session identifier

    Example:
        {
            "session_id": "abc-123"
        }
    """
    session_id: str


class PropalystSummaryResponse(BaseModel):
    """
    Response model for conversation summary.

    Attributes:
        summary (str): LLM-generated detailed summary
        session_id (str): Session identifier

    Example:
        {
            "summary": "Based on our conversation, you work in Whitefield...",
            "session_id": "abc-123"
        }
    """
    summary: str
    session_id: str


class PropalystAreasRequest(BaseModel):
    """
    Request model for fetching recommended areas.

    Attributes:
        session_id (str): Unique session identifier

    Example:
        {
            "session_id": "abc-123"
        }
    """
    session_id: str


class PropalystAreasResponse(BaseModel):
    """
    Response model for recommended areas.

    Attributes:
        areas (list): List of recommended area objects
        session_id (str): Session identifier

    Example:
        {
            "areas": [
                {
                    "areaName": "Whitefield",
                    "image": "https://...",
                    "childFriendlyScore": 9,
                    "schoolsNearby": 12,
                    "averageCommute": "15-20 min",
                    "budgetRange": "₹60K - ₹85K",
                    "highlights": ["IT Hub", "Great Schools", "Metro Access"]
                }
            ],
            "session_id": "abc-123"
        }
    """
    areas: list
    session_id: str


# ============================================================================
# LANGGRAPH WORKFLOW INSTANCES
# ============================================================================

# Create the graphs once when the app starts
# This is more efficient than creating them for each request

# Project 1: UI Generator (one-shot)
print("🔄 Initializing UI Generator workflow...")
ui_generator_graph = create_ui_generator_graph()
print("✅ UI Generator workflow ready!")

# Project 2: Propalyst Q&A (multi-step)
print("🔄 Initializing Propalyst Q&A workflow...")
propalyst_graph = create_propalyst_graph()
print("✅ Propalyst Q&A workflow ready!")

# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.get("/")
async def root():
    """
    Health check endpoint.

    Returns:
        dict: Basic API information

    Example:
        GET http://localhost:8000/
        Response: {
            "message": "Dynamic UI Generator API",
            "version": "1.0.0",
            "status": "running"
        }
    """
    return {
        "message": "Dynamic UI Generator API",
        "version": "2.0.0",
        "status": "running",
        "projects": {
            "project_1": "Dynamic UI Generator (one-shot)",
            "project_2": "Propalyst Q&A (multi-step conversations)"
        },
        "docs": "/docs",
        "endpoints": {
            "health": "/",
            "project_1": {
                "generate_ui": "/api/generate-ui",
                "components": "/api/components"
            },
            "project_2": {
                "propalyst_chat": "/api/propalyst/chat"
            }
        }
    }


@app.post("/api/generate-ui", response_model=GenerateUIResponse)
async def generate_ui(request: GenerateUIRequest):
    """
    Generate UI component from natural language description.

    This endpoint:
    1. Receives user's natural language input
    2. Runs it through LangGraph workflow
    3. Returns component configuration

    Args:
        request (GenerateUIRequest): Request with user_input

    Returns:
        GenerateUIResponse: Generated component or error

    Raises:
        HTTPException: If generation fails

    Examples:
        Request:
        POST /api/generate-ui
        {
            "user_input": "button"
        }

        Response:
        {
            "component": {
                "type": "Button",
                "props": {"label": "Click Me", "variant": "primary"}
            },
            "message": "Here's a Button component",
            "success": true
        }
    """

    print(f"\n📥 Received request: {request.user_input}")

    try:
        # Step 1: Create initial state
        initial_state = AgentState(
            user_input=request.user_input,
            component=None,
            message="",
            error=None
        )

        # Step 2: Run the LangGraph workflow
        print("🔄 Running LangGraph workflow...")
        final_state = await ui_generator_graph.ainvoke(initial_state)

        # Step 3: Check for errors
        if final_state.get("error"):
            print(f"❌ Workflow error: {final_state['error']}")
            raise HTTPException(
                status_code=400,
                detail=final_state["error"]
            )

        # Step 4: Extract component from state
        component = final_state.get("component")

        if not component:
            print("❌ No component generated")
            raise HTTPException(
                status_code=500,
                detail="Failed to generate component"
            )

        print(f"✅ Generated component: {component.type}")

        # Step 5: Return response
        return GenerateUIResponse(
            component=UIComponentResponse(
                type=component.type,
                props=component.props
            ),
            message=final_state.get("message", "Component generated successfully"),
            success=True
        )

    except HTTPException:
        # Re-raise HTTP exceptions
        raise

    except Exception as e:
        # Catch any unexpected errors
        error_message = f"Internal error: {str(e)}"
        print(f"❌ {error_message}")

        raise HTTPException(
            status_code=500,
            detail=error_message
        )


# ============================================================================
# PROPALYST ENDPOINTS (Project 2)
# ============================================================================

@app.post("/api/propalyst/chat", response_model=PropalystChatResponse)
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


@app.post("/api/propalyst/summary", response_model=PropalystSummaryResponse)
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
        from langchain_openai import ChatOpenAI
        from langchain_core.messages import SystemMessage, HumanMessage
        import os

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


@app.post("/api/propalyst/areas", response_model=PropalystAreasResponse)
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


# ============================================================================
# ADDITIONAL ENDPOINTS (Optional - for debugging)
# ============================================================================

@app.get("/api/components")
async def list_components():
    """
    List available component types.

    This is helpful for frontend to know what components are supported.

    Returns:
        dict: List of available components with their schemas

    Example:
        GET /api/components
        Response: {
            "components": ["Button", "TextArea", "CheckboxGroup", "Slider"]
        }
    """
    from agent.state import COMPONENT_SCHEMAS

    return {
        "components": list(COMPONENT_SCHEMAS.keys()),
        "schemas": COMPONENT_SCHEMAS
    }


@app.get("/health")
async def health_check():
    """
    Detailed health check endpoint.

    Checks:
    - API is running
    - Environment variables are set
    - LangGraph workflow is initialized

    Returns:
        dict: Health status information
    """
    has_api_key = bool(os.getenv("OPENAI_API_KEY"))
    has_graph = ui_generator_graph is not None

    return {
        "status": "healthy" if (has_api_key and has_graph) else "degraded",
        "checks": {
            "api_running": True,
            "openai_api_key_set": has_api_key,
            "langgraph_initialized": has_graph
        },
        "warnings": [] if has_api_key else ["OPENAI_API_KEY not set"]
    }


# ============================================================================
# STARTUP/SHUTDOWN EVENTS
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """
    Runs when the application starts.

    Good place for:
    - Loading models
    - Connecting to databases
    - Initializing services
    """
    print("\n" + "="*60)
    print("🚀 Dynamic UI Generator API Starting...")
    print("="*60)
    print(f"📍 API Documentation: http://localhost:8000/docs")
    print(f"📍 Health Check: http://localhost:8000/health")
    print("="*60 + "\n")


@app.on_event("shutdown")
async def shutdown_event():
    """
    Runs when the application shuts down.

    Good place for:
    - Closing connections
    - Saving state
    - Cleanup
    """
    print("\n" + "="*60)
    print("👋 Shutting down Dynamic UI Generator API")
    print("="*60 + "\n")


# ============================================================================
# RUN APPLICATION
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    # Run the application
    # This is just for development - use uvicorn command in production
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Auto-reload on code changes
        log_level="info"
    )
