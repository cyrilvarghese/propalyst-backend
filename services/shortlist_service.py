"""
Shortlist Service
=================

Handles creating and managing property shortlists in JSON file.
"""

import json
import uuid
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime


class ShortlistService:
    """Service for managing property shortlists"""

    # Data file location
    DATA_FILE_PATH = Path(__file__).parent.parent / "data" / "shortlist.json"

    @classmethod
    def _ensure_data_directory(cls) -> None:
        """Ensure data directory exists"""
        cls.DATA_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)

    @classmethod
    def _load_existing_data(cls) -> List[Dict[str, Any]]:
        """Load existing shortlists from JSON file, or return empty list if file doesn't exist"""
        if cls.DATA_FILE_PATH.exists():
            try:
                with open(cls.DATA_FILE_PATH, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data if isinstance(data, list) else []
            except (json.JSONDecodeError, IOError) as e:
                print(f"[Shortlist] Warning: Could not load existing data: {e}")
                return []
        return []

    @classmethod
    def _save_data(cls, data: List[Dict[str, Any]]) -> None:
        """Save shortlists to JSON file"""
        cls._ensure_data_directory()
        with open(cls.DATA_FILE_PATH, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    @classmethod
    async def create_shortlist(
        cls,
        description: str,
        source: str,
        properties: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Create a new shortlist entry

        Args:
            description: Original user query or description
            source: Full URL of the property search source
            properties: List of property objects to shortlist

        Returns:
            Dictionary with success status and created shortlist data
        """
        try:
            # Load existing shortlists
            shortlists = cls._load_existing_data()

            # Create new shortlist entry
            new_shortlist = {
                "id": str(uuid.uuid4()),
                "description": description,
                "source": source,
                "created_at": datetime.now().isoformat(),
                "properties": properties
            }

            # Add to list and save
            shortlists.append(new_shortlist)
            cls._save_data(shortlists)

            print(f"[Shortlist] ✓ Created shortlist with ID: {new_shortlist['id']}")
            return {
                "success": True,
                "data": new_shortlist,
                "message": f"Shortlist created with {len(properties)} properties"
            }

        except Exception as e:
            print(f"[Shortlist] ✗ Error creating shortlist: {e}")
            return {
                "success": False,
                "data": None,
                "message": f"Error creating shortlist: {str(e)}"
            }

    @classmethod
    async def get_all_shortlists(cls) -> Dict[str, Any]:
        """
        Retrieve all shortlists

        Returns:
            Dictionary with success status and list of all shortlists
        """
        try:
            shortlists = cls._load_existing_data()
            print(f"[Shortlist] ✓ Retrieved {len(shortlists)} shortlists")
            return {
                "success": True,
                "data": shortlists,
                "message": f"Found {len(shortlists)} shortlists"
            }
        except Exception as e:
            print(f"[Shortlist] ✗ Error retrieving shortlists: {e}")
            return {
                "success": False,
                "data": [],
                "message": f"Error retrieving shortlists: {str(e)}"
            }

    @classmethod
    async def get_shortlist_by_id(cls, shortlist_id: str) -> Dict[str, Any]:
        """
        Retrieve a specific shortlist by ID

        Args:
            shortlist_id: Unique identifier of the shortlist

        Returns:
            Dictionary with success status and shortlist data
        """
        try:
            shortlists = cls._load_existing_data()

            # Find shortlist by ID
            shortlist = next((s for s in shortlists if s.get("id") == shortlist_id), None)

            if shortlist:
                print(f"[Shortlist] ✓ Found shortlist with ID: {shortlist_id}")
                return {
                    "success": True,
                    "data": shortlist,
                    "message": "Shortlist found"
                }
            else:
                print(f"[Shortlist] ✗ Shortlist not found: {shortlist_id}")
                return {
                    "success": False,
                    "data": None,
                    "message": f"Shortlist with ID {shortlist_id} not found"
                }

        except Exception as e:
            print(f"[Shortlist] ✗ Error retrieving shortlist: {e}")
            return {
                "success": False,
                "data": None,
                "message": f"Error retrieving shortlist: {str(e)}"
            }

    @classmethod
    async def delete_shortlist(cls, shortlist_id: str) -> Dict[str, Any]:
        """
        Delete a shortlist by ID

        Args:
            shortlist_id: Unique identifier of the shortlist to delete

        Returns:
            Dictionary with success status
        """
        try:
            shortlists = cls._load_existing_data()

            # Filter out the shortlist to delete
            original_count = len(shortlists)
            shortlists = [s for s in shortlists if s.get("id") != shortlist_id]

            if len(shortlists) < original_count:
                cls._save_data(shortlists)
                print(f"[Shortlist] ✓ Deleted shortlist with ID: {shortlist_id}")
                return {
                    "success": True,
                    "data": None,
                    "message": f"Shortlist {shortlist_id} deleted successfully"
                }
            else:
                print(f"[Shortlist] ✗ Shortlist not found for deletion: {shortlist_id}")
                return {
                    "success": False,
                    "data": None,
                    "message": f"Shortlist with ID {shortlist_id} not found"
                }

        except Exception as e:
            print(f"[Shortlist] ✗ Error deleting shortlist: {e}")
            return {
                "success": False,
                "data": None,
                "message": f"Error deleting shortlist: {str(e)}"
            }
