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
    def _load_existing_data(cls) -> Dict[str, Any]:
        """Load existing data from JSON file, or return empty dict if file doesn't exist"""
        if cls.DATA_FILE_PATH.exists():
            try:
                with open(cls.DATA_FILE_PATH, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"[DataPersistence] Warning: Could not load existing data: {e}")
                return {}
        return {}

    @classmethod
    def _save_data(cls, data: Dict[str, Any]) -> None:
        """Save data to JSON file"""
        cls._ensure_data_directory()
        with open(cls.DATA_FILE_PATH, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    @classmethod
    async def save_scraped_properties(
        cls,
        url: str,
        properties: List[Dict[str, Any]],
        merge: bool = True
    ) -> Dict[str, Any]:
        """
        Save scraped properties to JSON file with URL as key.

        Args:
            url: The URL that was scraped
            properties: List of property dictionaries
            merge: If True, merges with existing data. If False, overwrites all data.

        Returns:
            Dictionary with operation status and metadata
        """
        try:
            print(f"[DataPersistence] Saving {len(properties)} properties for URL: {url}")

            # Load existing data if merging
            if merge:
                all_data = cls._load_existing_data()
                print(f"[DataPersistence] Loaded {len(all_data)} existing URLs")
            else:
                all_data = {}
                print(f"[DataPersistence] Starting fresh (not merging)")

            # Add/update properties for this URL
            all_data[url] = properties

            # Save to file
            cls._save_data(all_data)

            result = {
                "success": True,
                "message": "Properties saved successfully",
                "url": url,
                "properties_saved": len(properties),
                "total_urls_in_file": len(all_data),
                "file_path": str(cls.DATA_FILE_PATH),
                "saved_at": datetime.now().isoformat(),
                "merge_mode": merge
            }

            print(f"[DataPersistence] ✓ Successfully saved. File now contains {len(all_data)} URLs")
            return result

        except Exception as e:
            print(f"[DataPersistence] ✗ Error saving properties: {e}")
            import traceback
            print(f"[DataPersistence] Traceback: {traceback.format_exc()}")
            return {
                "success": False,
                "message": f"Failed to save properties: {str(e)}",
                "url": url,
                "properties_saved": 0,
                "error": str(e)
            }

    @classmethod
    async def get_all_data(cls) -> Dict[str, Any]:
        """
        Retrieve all saved data from JSON file.

        Returns:
            Dictionary with all URLs and their properties
        """
        try:
            data = cls._load_existing_data()
            total_properties = sum(len(props) for props in data.values())
            return {
                "success": True,
                "data": data,
                "total_urls": len(data),
                "total_properties": total_properties,
                "file_path": str(cls.DATA_FILE_PATH)
            }
        except Exception as e:
            print(f"[DataPersistence] Error retrieving data: {e}")
            return {
                "success": False,
                "error": str(e),
                "data": {}
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
            return data.get(url)
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

            if url not in data:
                return {
                    "success": False,
                    "message": f"URL not found in data file",
                    "url": url
                }

            del data[url]
            cls._save_data(data)

            return {
                "success": True,
                "message": "Properties deleted successfully",
                "url": url,
                "total_urls_remaining": len(data),
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
            cls._save_data({})
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
