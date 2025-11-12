"""
UI Generation Models
====================

Pydantic models for UI generation endpoints.
"""

from pydantic import BaseModel


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
