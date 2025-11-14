"""
Data Persistence Service
========================

Handles saving scraped property data to JSON files.
"""

import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime


class DataPersistenceService:
    """Service for persisting scraped property data to JSON files"""

    # Default data file location
    DATA_FILE_PATH = Path(__file__).parent.parent / "data" / "scraped_properties.json"

    @classmethod
    def set_data_file_path(cls, file_path: str) -> None:
        """Set custom data file path"""
        cls.DATA_FILE_PATH = Path(file_path)

    @classmethod
    def _ensure_data_directory(cls) -> None:
        """Ensure data directory exists"""
        cls.DATA_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)

    @classmethod
    def _load_existing_data(cls) -> list:
        """Load existing data from JSON file, or return empty list if file doesn't exist"""
        if cls.DATA_FILE_PATH.exists():
            try:
                with open(cls.DATA_FILE_PATH, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Handle backward compatibility with old URL-keyed format
                    if isinstance(data, dict):
                        return cls._migrate_old_format(data)
                    return data if isinstance(data, list) else []
            except (json.JSONDecodeError, IOError) as e:
                print(f"[DataPersistence] Warning: Could not load existing data: {e}")
                return []
        return []

    @classmethod
    def _save_data(cls, data: list) -> None:
        """Save data to JSON file"""
        cls._ensure_data_directory()
        with open(cls.DATA_FILE_PATH, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    @classmethod
    def _migrate_old_format(cls, old_data: Dict[str, Any]) -> list:
        """Convert URL-keyed object format to array format"""
        new_data = []
        for url, entry in old_data.items():
            if isinstance(entry, dict) and "data" in entry:
                # Already has metadata, just add to array
                new_data.append(entry)
            elif isinstance(entry, list):
                # Old format without metadata, wrap it
                new_data.append({
                    "type": "unknown",
                    "source_url": url,
                    "scraped_at": datetime.now().isoformat(),
                    "data": entry
                })
        return new_data

    @classmethod
    async def save_scraped_properties(
        cls,
        url: str,
        properties: List[Dict[str, Any]],
        merge: bool = True,
        source: str = "unknown"
    ) -> Dict[str, Any]:
        """
        Save scraped properties to JSON file as array entries.

        Args:
            url: The URL that was scraped
            properties: List of property dictionaries
            merge: If True, merges with existing data. If False, overwrites all data.
            source: Source provider (squareyards, magicbricks, etc.)

        Returns:
            Dictionary with operation status and metadata
        """
        try:
            print(f"[DataPersistence] Saving {len(properties)} properties for URL: {url}")
            print(f"[DataPersistence] Source: {source}")

            # Load existing data
            if merge:
                all_data = cls._load_existing_data()
                print(f"[DataPersistence] Loaded {len(all_data)} existing entries")
            else:
                all_data = []
                print(f"[DataPersistence] Starting fresh (not merging)")

            # Wrap properties with metadata
            property_entry = {
                "type": source,
                "source_url": url,
                "scraped_at": datetime.now().isoformat(),
                "data": properties
            }

            # Remove any existing entry for this URL and add the new one
            all_data = [entry for entry in all_data if entry.get("source_url") != url]
            all_data.append(property_entry)

            # Save to file
            cls._save_data(all_data)

            result = {
                "success": True,
                "message": "Properties saved successfully",
                "url": url,
                "type": source,
                "properties_saved": len(properties),
                "total_entries_in_file": len(all_data),
                "file_path": str(cls.DATA_FILE_PATH),
                "saved_at": datetime.now().isoformat(),
                "merge_mode": merge
            }

            print(f"[DataPersistence] ✓ Successfully saved. File now contains {len(all_data)} entries")
            return result

        except Exception as e:
            print(f"[DataPersistence] ✗ Error saving properties: {e}")
            import traceback
            print(f"[DataPersistence] Traceback: {traceback.format_exc()}")
            return {
                "success": False,
                "message": f"Failed to save properties: {str(e)}",
                "url": url,
                "type": source,
                "properties_saved": 0,
                "error": str(e)
            }

    @classmethod
    async def get_all_data(cls) -> Dict[str, Any]:
        """
        Retrieve all saved data from JSON file.

        Returns:
            Dictionary with all entries and their properties
        """
        try:
            data = cls._load_existing_data()
            total_properties = sum(len(entry.get("data", [])) for entry in data)
            return {
                "success": True,
                "data": data,
                "total_entries": len(data),
                "total_properties": total_properties,
                "file_path": str(cls.DATA_FILE_PATH)
            }
        except Exception as e:
            print(f"[DataPersistence] Error retrieving data: {e}")
            return {
                "success": False,
                "error": str(e),
                "data": []
            }

    @classmethod
    async def get_properties_by_url(cls, url: str) -> Optional[List[Dict[str, Any]]]:
        """
        Retrieve properties for a specific URL.

        Args:
            url: The URL to retrieve properties for

        Returns:
            List of properties or None if URL not found
        """
        try:
            data = cls._load_existing_data()

            # Find entry by source_url
            for entry in data:
                if entry.get("source_url") == url:
                    return entry.get("data", [])

            return None

        except Exception as e:
            print(f"[DataPersistence] Error retrieving properties for URL: {e}")
            return None

    @classmethod
    async def delete_properties_by_url(cls, url: str) -> Dict[str, Any]:
        """
        Delete properties for a specific URL.

        Args:
            url: The URL whose properties should be deleted

        Returns:
            Dictionary with operation status
        """
        try:
            data = cls._load_existing_data()

            # Find and remove entry by source_url
            original_length = len(data)
            data = [entry for entry in data if entry.get("source_url") != url]

            if len(data) == original_length:
                return {
                    "success": False,
                    "message": f"URL not found in data file",
                    "url": url
                }

            cls._save_data(data)

            return {
                "success": True,
                "message": "Properties deleted successfully",
                "url": url,
                "total_entries_remaining": len(data),
                "file_path": str(cls.DATA_FILE_PATH),
                "deleted_at": datetime.now().isoformat()
            }

        except Exception as e:
            print(f"[DataPersistence] Error deleting properties: {e}")
            return {
                "success": False,
                "message": f"Failed to delete properties: {str(e)}",
                "url": url,
                "error": str(e)
            }

    @classmethod
    async def clear_all_data(cls) -> Dict[str, Any]:
        """
        Clear all data from the JSON file.

        Returns:
            Dictionary with operation status
        """
        try:
            cls._save_data([])
            return {
                "success": True,
                "message": "All data cleared successfully",
                "file_path": str(cls.DATA_FILE_PATH),
                "cleared_at": datetime.now().isoformat()
            }
        except Exception as e:
            print(f"[DataPersistence] Error clearing data: {e}")
            return {
                "success": False,
                "message": f"Failed to clear data: {str(e)}",
                "error": str(e)
            }
