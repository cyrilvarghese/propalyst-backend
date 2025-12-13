"""
Lead Service Module

Provides business logic for:
- Extracting detailed criteria from natural language queries
- Finding nearby localities using Google Search grounding
- Matching properties from Supabase
- Creating leads with complete metadata

Organized into specialized modules:
- extraction.py: LLM criteria extraction
- matching.py: Property matching from Supabase
- localities.py: Nearby locality finding
- persistence.py: Lead storage and retrieval
- service.py: Main orchestration service
"""

from .service import LeadService

__all__ = ["LeadService"]
