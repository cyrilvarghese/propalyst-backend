"""
Lead Persistence Module
========================

Handles lead storage and retrieval from JSON file.
"""

import json
from pathlib import Path
from typing import Dict, Any, List


class LeadPersistenceService:
    """Service for persisting leads to JSON file storage"""

    DATA_FILE_PATH = Path(__file__).parent.parent.parent / "data" / "leads.json"

    @classmethod
    def _ensure_data_directory(cls) -> None:
        """Ensure data directory exists"""
        cls.DATA_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)

    @classmethod
    def load_leads(cls) -> List[Dict[str, Any]]:
        """Load existing leads from JSON file"""
        if cls.DATA_FILE_PATH.exists():
            try:
                with open(cls.DATA_FILE_PATH, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data if isinstance(data, list) else []
            except (json.JSONDecodeError, IOError) as e:
                print(f"[LeadPersistence] Warning: Could not load leads: {e}")
                return []
        return []

    @classmethod
    def save_leads(cls, leads: List[Dict[str, Any]]) -> None:
        """Save leads to JSON file"""
        cls._ensure_data_directory()
        with open(cls.DATA_FILE_PATH, 'w', encoding='utf-8') as f:
            json.dump(leads, f, indent=2, ensure_ascii=False)

    @classmethod
    def save_lead(cls, lead: Dict[str, Any]) -> None:
        """Append a single lead to the leads file"""
        leads = cls.load_leads()
        leads.append(lead)
        cls.save_leads(leads)
