"""
UI Generation Router
====================

API endpoints for UI component generation functionality.
"""

from fastapi import APIRouter, HTTPException

from models.ui import GenerateUIRequest, GenerateUIResponse, UIComponentResponse
from agent import AgentState

router = APIRouter(
    prefix="/api",
    tags=["UI Generation"]
)


@router.post("/generate-ui", response_model=GenerateUIResponse)
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
        # Import graph instance from graphs module
        from graphs import ui_generator_graph

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


@router.get("/components")
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

