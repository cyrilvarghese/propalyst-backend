"""
API Routers Package
===================

Modular API routers for different features.
"""

from .ui_router import router as ui_router
from .propalyst_router import router as propalyst_router
from .search_router import router as search_router
from .scraping_router import router as scraping_router

__all__ = [
    "ui_router",
    "propalyst_router",
    "search_router",
    "scraping_router"
]
