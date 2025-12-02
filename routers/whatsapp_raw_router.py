"""
WhatsApp Raw Messages Router (Aggregate)

Combines all WhatsApp raw message routers:
- whatsapp_upload_processing_router: Upload files and process messages
- whatsapp_listings_router: Manage extracted listings
- whatsapp_stats_router: Statistics

To include in FastAPI app:
    from routers.whatsapp_raw_router import get_all_routers
    for router in get_all_routers():
        app.include_router(router)
"""

from routers.whatsapp_upload_processing_router import router as upload_processing_router
from routers.whatsapp_listings_router import router as listings_router
from routers.whatsapp_stats_router import router as stats_router


def get_all_routers():
    """Get all WhatsApp routers"""
    return [
        upload_processing_router,
        listings_router,
        stats_router
    ]
