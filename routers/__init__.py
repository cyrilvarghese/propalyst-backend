"""
API Routers Package
===================

Modular API routers for different features.
"""

from .ui_router import router as ui_router
from .propalyst_router import router as propalyst_router
from .search_router import router as search_router
from .scraping_router import router as scraping_router
from .crea_wapp_router import router as crea_wapp_router
from .shortlist_router import router as shortlist_router
from .agent_profile_router import router as agent_profile_router
from .whatsapp_listing_router import router as whatsapp_listing_router
from .whatsapp_upload_processing_router import router as whatsapp_upload_processing_router
from .whatsapp_listings_router import router as whatsapp_listings_router
from .whatsapp_stats_router import router as whatsapp_stats_router

__all__ = [
    "ui_router",
    "propalyst_router",
    "search_router",
    "scraping_router",
    "crea_wapp_router",
    "shortlist_router",
    "agent_profile_router",
    "whatsapp_listing_router",
    "whatsapp_upload_processing_router",
    "whatsapp_listings_router",
    "whatsapp_stats_router"
]
