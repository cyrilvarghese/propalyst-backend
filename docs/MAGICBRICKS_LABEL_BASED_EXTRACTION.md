# MagicBricks Label-Based Field Extraction

## Problem
The original schema used nth-child and nth-of-type CSS selectors which were unreliable because:
- DOM structure varies across different property listings
- The order of summary items can change
- nth-child selectors would break if structure changed

## Solution
Implemented a two-stage extraction approach:

### Stage 1: Extract All Summary Items with Labels
The schema now extracts ALL summary items with their labels and values as arrays:

```json
{
  "all_summary_items": [
    {
      "label": "Carpet Area",
      "value": "2200 sqft"
    },
    {
      "label": "Furnishing Status",
      "value": "Ready to Move"
    },
    {
      "label": "Parking",
      "value": "2 Covered"
    },
    {
      "label": "Washroom",
      "value": "2"
    },
    ...
  ]
}
```

### Stage 2: Post-Process and Map Labels to Fields
After extraction, the `_post_process_properties()` method:
1. Iterates through `all_summary_items` array
2. Matches label text against known field names
3. Maps extracted values to appropriately named fields
4. Handles both simple items and nested column items (Cabins, Seats)
5. Removes the raw `all_summary_items` from final output

## Label-to-Field Mapping
```python
{
    "Carpet Area": "carpet_area",
    "Furnishing Status": "furnishing_status",
    "Cabins": "cabins",
    "Seats": "seats",
    "Parking": "parking",
    "Washroom": "washrooms",
    "Pantry": "pantry"
}
```

## Output Format
Final properties contain mapped fields instead of raw items:

```json
{
  "title": "Office Space for rent...",
  "price": "₹1.5 Lac",
  "carpet_area": "2200 sqft",
  "furnishing_status": "Ready to Move",
  "cabins": "2",
  "seats": "40",
  "parking": "2 Covered",
  "washrooms": "2",
  "pantry": "Wet Pantry/Cafeteria",
  "description": "...",
  "agent_name": "Myriad Solutions"
}
```

## Benefits
✓ **Robust**: Works regardless of item order
✓ **Flexible**: Handles different property types
✓ **Maintainable**: Label text is explicit and self-documenting
✓ **Scalable**: Easy to add new label mappings
✓ **Resilient**: Missing items don't break extraction

## Implementation Details

### Schema Changes
- Changed from nth-child selectors to array-based extraction
- Extracts complete label-value pairs with `all_summary_items`
- Handles nested column items for multi-column layouts

### Scraper Changes
- Added `label_to_field` mapping dictionary in `__init__()`
- Added `_post_process_properties()` method to transform raw data
- Calls post-processing on all extracted data before return

## Error Handling
- Gracefully handles missing labels
- Skips invalid items (non-dict types)
- Preserves all other fields unchanged
- Works with or without column items

## Testing
The approach has been tested with:
- Commercial properties (offices, commercial spaces)
- Varied item orderings
- Nested column structures
- Missing or additional items
