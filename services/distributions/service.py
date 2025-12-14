"""
Locality Distribution Service
==============================

Service for processing and formatting locality distribution statistics.
Transforms flat database results into nested distribution structure.
"""

from typing import Dict, List, Any, Optional
from services.supabase_service import SupabaseService


class LocalityDistributionService:
    """Service for locality distribution statistics and formatting"""

    # Price range mapping (matches database column names to display names and rupees)
    PRICE_RANGES = [
        {"db_col": "price_2_5cr", "display": "2-5Cr"},
        {"db_col": "price_5_8cr", "display": "5-8Cr"},
        {"db_col": "price_8_10cr", "display": "8-10Cr"},
        {"db_col": "price_10_12cr", "display": "10-12Cr"},
        {"db_col": "price_12_15cr", "display": "12-15Cr"},
        {"db_col": "price_15cr_plus", "display": "15Cr+"},
    ]

    # Area range mapping
    AREA_RANGES = [
        {"db_col": "area_0_500", "display": "0-500"},
        {"db_col": "area_500_1000", "display": "500-1000"},
        {"db_col": "area_1000_1500", "display": "1000-1500"},
        {"db_col": "area_1500_2000", "display": "1500-2000"},
        {"db_col": "area_2000_3000", "display": "2000-3000"},
        {"db_col": "area_3000_4000", "display": "3000-4000"},
        {"db_col": "area_4000_5000", "display": "4000-5000"},
        {"db_col": "area_5000_plus", "display": "5000+"},
    ]

    # Property type mapping
    PROPERTY_TYPES = [
        {"db_col": "type_apartment", "display": "Apartment"},
        {"db_col": "type_villa", "display": "Villa"},
        {"db_col": "type_independent_house", "display": "Independent House"},
        {"db_col": "type_plot", "display": "Plot"},
    ]

    # BHK mapping
    BHK_RANGES = [
        {"db_col": "bhk_1", "display": "1BHK"},
        {"db_col": "bhk_2", "display": "2BHK"},
        {"db_col": "bhk_3", "display": "3BHK"},
        {"db_col": "bhk_4", "display": "4BHK"},
    ]

    @staticmethod
    def _transform_distribution(flat_data: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Transform flat database row into nested distribution structure

        Input (flat from DB):
        {
            "location": "indiranagar",
            "price_5_8cr": 2,
            "price_8_10cr": 3,
            "area_0_500": 1,
            "type_apartment": 5,
            "bhk_2": 3
        }

        Output (nested):
        {
            "price": [
                {"name": "5-8Cr", "count": 2},
                {"name": "8-10Cr", "count": 3}
            ],
            "area": [
                {"name": "0-500", "count": 1}
            ],
            "propertyType": [
                {"name": "Apartment", "count": 5}
            ],
            "bedroom": [
                {"name": "2BHK", "count": 3}
            ]
        }
        """
        transformed = {
            "price": [],
            "area": [],
            "propertyType": [],
            "bedroom": [],
        }

        # Transform price ranges
        for range_info in LocalityDistributionService.PRICE_RANGES:
            count = flat_data.get(range_info["db_col"], 0)
            if count > 0:  # Only include ranges with counts > 0
                transformed["price"].append({
                    "name": range_info["display"],
                    "count": count
                })

        # Transform area ranges
        for range_info in LocalityDistributionService.AREA_RANGES:
            count = flat_data.get(range_info["db_col"], 0)
            if count > 0:
                transformed["area"].append({
                    "name": range_info["display"],
                    "count": count
                })

        # Transform property types
        for range_info in LocalityDistributionService.PROPERTY_TYPES:
            count = flat_data.get(range_info["db_col"], 0)
            if count > 0:
                transformed["propertyType"].append({
                    "name": range_info["display"],
                    "count": count
                })

        # Transform BHK ranges
        for range_info in LocalityDistributionService.BHK_RANGES:
            count = flat_data.get(range_info["db_col"], 0)
            if count > 0:
                transformed["bedroom"].append({
                    "name": range_info["display"],
                    "count": count
                })

        return transformed

    @staticmethod
    def _aggregate_distributions(all_rows: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Aggregate distributions across all localities

        Sums counts for each distribution type across all rows.

        Args:
            all_rows: List of raw distribution rows from database

        Returns:
            Aggregated distributions in same nested format as individual localities
        """
        # Initialize aggregates
        aggregates = {
            "price": {},
            "area": {},
            "propertyType": {},
            "bedroom": {},
        }

        # Sum all counts across localities
        for row in all_rows:
            # Aggregate prices
            for range_info in LocalityDistributionService.PRICE_RANGES:
                count = row.get(range_info["db_col"], 0)
                if count > 0:
                    if range_info["display"] not in aggregates["price"]:
                        aggregates["price"][range_info["display"]] = 0
                    aggregates["price"][range_info["display"]] += count

            # Aggregate areas
            for range_info in LocalityDistributionService.AREA_RANGES:
                count = row.get(range_info["db_col"], 0)
                if count > 0:
                    if range_info["display"] not in aggregates["area"]:
                        aggregates["area"][range_info["display"]] = 0
                    aggregates["area"][range_info["display"]] += count

            # Aggregate property types
            for range_info in LocalityDistributionService.PROPERTY_TYPES:
                count = row.get(range_info["db_col"], 0)
                if count > 0:
                    if range_info["display"] not in aggregates["propertyType"]:
                        aggregates["propertyType"][range_info["display"]] = 0
                    aggregates["propertyType"][range_info["display"]] += count

            # Aggregate BHK
            for range_info in LocalityDistributionService.BHK_RANGES:
                count = row.get(range_info["db_col"], 0)
                if count > 0:
                    if range_info["display"] not in aggregates["bedroom"]:
                        aggregates["bedroom"][range_info["display"]] = 0
                    aggregates["bedroom"][range_info["display"]] += count

        # Convert aggregates dicts to arrays
        result = {
            "price": [{"name": name, "count": count} for name, count in aggregates["price"].items()],
            "area": [{"name": name, "count": count} for name, count in aggregates["area"].items()],
            "propertyType": [{"name": name, "count": count} for name, count in aggregates["propertyType"].items()],
            "bedroom": [{"name": name, "count": count} for name, count in aggregates["bedroom"].items()],
        }

        return result

    @staticmethod
    async def get_distributions(
        location: Optional[str] = None,
        limit: int = 100
    ) -> Dict[str, Any]:
        """
        Get distribution statistics per locality in nested format

        Fetches raw data from SupabaseService and transforms into nested structure
        matching mock-distributions.json format. Also includes aggregated totals
        across all localities.

        Args:
            location: Optional location filter (case-insensitive partial match)
            limit: Maximum number of localities to return

        Returns:
            Dictionary with:
            {
                "success": bool,
                "data": {
                    "distributions": {
                        "All": { ... },  # Aggregated across all localities
                        "Indiranagar": { ... },
                        "Koramangala": { ... }
                    }
                },
                "count": int,
                "message": str
            }
        """
        try:
            # Get raw distributions from database
            result = await SupabaseService.get_locality_distributions(
                location=location,
                limit=limit
            )

            if not result.get("success"):
                return {
                    "success": False,
                    "data": None,
                    "message": result.get("message", "Failed to retrieve distributions")
                }

            raw_distributions = result.get("data", [])

            # Transform to nested format
            distributions = {}

            # Add aggregated totals first (if we have data)
            if raw_distributions:
                aggregate_dist = LocalityDistributionService._aggregate_distributions(raw_distributions)
                distributions["All"] = aggregate_dist
                print(f"[LocalityDistributionService] ✓ Calculated aggregated distributions")

            # Add individual locality distributions
            for row in raw_distributions:
                location_name = row.get("location", "Unknown")
                # Capitalize location name for display (e.g., "indiranagar" -> "Indiranagar")
                display_location = location_name.title() if location_name else "Unknown"

                # Transform flat row to nested structure
                nested = LocalityDistributionService._transform_distribution(row)
                distributions[display_location] = nested

            print(f"[LocalityDistributionService] ✓ Transformed {len(distributions) - 1} locality distributions (+ 'All' aggregate)")

            return {
                "success": True,
                "data": {
                    "distributions": distributions
                },
                "count": len(distributions) - 1,  # Don't count "All" in the locality count
                "message": f"Retrieved distributions for {len(distributions) - 1} localities + aggregated totals"
            }

        except Exception as e:
            print(f"[LocalityDistributionService] ✗ Error: {e}")
            return {
                "success": False,
                "data": None,
                "message": f"Error retrieving distributions: {str(e)}"
            }
