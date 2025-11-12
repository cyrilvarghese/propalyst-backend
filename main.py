"""
FastAPI Application - Dynamic UI Generator
===========================================

This is the main entry point for the backend API.

Key Components:
---------------
1. FastAPI app with CORS
2. Environment variable loading
3. Router registration
4. LangGraph workflow initialization

Endpoints:
----------
- GET  /              Health check
- GET  /health         Detailed health check
- POST /api/generate-ui   Generate UI component (via ui_router)
- GET  /api/components    List components (via ui_router)
- POST /api/propalyst/chat    Propalyst chat (via propalyst_router)
- POST /api/propalyst/summary Propalyst summary (via propalyst_router)
- POST /api/propalyst/areas   Propalyst areas (via propalyst_router)
- POST /api/property-search    Property search (via search_router)

Run with:
---------
uvicorn main:app --reload --port 8000
"""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Import graph instances (initialized in graphs.py)
from graphs import ui_generator_graph, propalyst_graph

# Import routers
from routers import ui_router, propalyst_router, search_router, scraping_router

# Load environment variables from .env file
load_dotenv()

# ============================================================================
# FASTAPI APPLICATION SETUP
# ============================================================================

app = FastAPI(
    title="Dynamic UI Generator API",
    description="LangGraph-powered API for generating UI components from natural language",
    version="2.0.0",
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
# INCLUDE ROUTERS
# ============================================================================

app.include_router(ui_router)
app.include_router(propalyst_router)
app.include_router(search_router)
app.include_router(scraping_router)

# ============================================================================
# HEALTH CHECK ENDPOINTS
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
            "version": "2.0.0",
            "status": "running"
        }
    """
    return {
        "message": "Dynamic UI Generator API",
        "version": "2.0.0",
        "status": "running",
        "projects": {
            "project_1": "Dynamic UI Generator (one-shot)",
            "project_2": "Propalyst Q&A (multi-step conversations)",
            "project_3": "Property Search (Gemini grounding)"
        },
        "docs": "/docs",
        "endpoints": {
            "health": "/",
            "health_detailed": "/health",
            "project_1": {
                "generate_ui": "/api/generate-ui",
                "components": "/api/components"
            },
            "project_2": {
                "propalyst_chat": "/api/propalyst/chat",
                "propalyst_summary": "/api/propalyst/summary",
                "propalyst_areas": "/api/propalyst/areas"
            },
            "project_3": {
                "property_search": "/api/property-search"
            }
        }
    }


@app.get("/health")
async def health_check():
    """
    Detailed health check endpoint.

    Checks:
    - API is running
    - Environment variables are set
    - LangGraph workflows are initialized

    Returns:
        dict: Health status information
    """
    has_api_key = bool(os.getenv("OPENAI_API_KEY"))
    has_ui_graph = ui_generator_graph is not None
    has_propalyst_graph = propalyst_graph is not None

    return {
        "status": "healthy" if (has_api_key and has_ui_graph and has_propalyst_graph) else "degraded",
        "checks": {
            "api_running": True,
            "openai_api_key_set": has_api_key,
            "ui_generator_initialized": has_ui_graph,
            "propalyst_graph_initialized": has_propalyst_graph
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
