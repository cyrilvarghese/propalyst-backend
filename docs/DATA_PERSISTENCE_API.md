# Data Persistence API Documentation

## Overview

The Data Persistence API automatically saves all scraped property data to a JSON file, organized by the source URL. This allows you to maintain a persistent database of all properties you've scraped and scored.

## File Location

All scraped properties are stored in:
```
/data/scraped_properties.json
```

## Data Structure

The JSON file uses the following structure:

```json
{
  "https://www.squareyards.com/sale/5-bhk-for-sale-in-indiranagar-bangalore": [
    {
      "title": "5 BHK House for Sale in Indiranagar, Bangalore",
      "price": "₹ 4.2 Cr",
      "location": "Indiranagar, Bangalore",
      "bedrooms": 5,
      "bathrooms": 5,
      "area": "1200",
      "facing": "West Facing",
      "parking": "1 Covered + 1 Open",
      "flooring": "Marble Flooring",
      "furnishing": "Unfurnished",
      "description": "This spacious 5-bedroom...",
      "agent_name": "Lakshminaryana N",
      "agent_rating": 4.7,
      "agent_url": "https://www.squareyards.com/agent/...",
      "relevance_score": 8,
      "relevance_reason": "Matched: location (Indiranagar), bedrooms (5 BHK), parking available",
      "property_url": "https://www.squareyards.com/resale-5-bhk-..."
    },
    // ... more properties from same URL ...
  ],
  "https://www.squareyards.com/sale/2-bhk-for-sale-in-whitefield": [
    // ... properties from different URL ...
  ]
}
```

## API Endpoints

### 1. Scrape and Save Properties (Automatic with Caching)

When you use the batch endpoint, it first checks if the URL has been previously scraped. If found in cache, it returns cached data instantly. Otherwise, it scrapes fresh data and saves it to the JSON file.

**Endpoint:**
```
GET /api/get_listing_details_batch?url=<URL>&orig_query=<QUERY>&batch_size=10&use_cache=true
```

**Query Parameters:**
- `url` (required, string): Property listing URL
- `orig_query` (required, string): Original search query for relevance scoring
- `batch_size` (optional, default: 10): Properties per API call
- `use_cache` (optional, default: true): Use cached data if available, set to false to force fresh scrape

**Response (From Cache):**
```json
{
  "success": true,
  "properties": [...],
  "count": 15,
  "source": "squareyards",
  "from_cache": true,
  "api_calls_made": 0
}
```

**Response (Fresh Scrape):**
```json
{
  "success": true,
  "properties": [...],
  "count": 15,
  "source": "squareyards",
  "scraped_at": "2025-11-13T10:30:00",
  "from_cache": false,
  "api_calls_made": 2,
  "persistence": {
    "success": true,
    "message": "Properties saved successfully",
    "url": "https://www.squareyards.com/...",
    "properties_saved": 15,
    "total_urls_in_file": 3,
    "file_path": "/data/scraped_properties.json",
    "saved_at": "2025-11-13T10:30:00",
    "merge_mode": true
  }
}
```

### 2. Get All Scraped Properties

Retrieve all properties from all URLs stored in the data file.

**Endpoint:**
```
GET /api/scraped_properties
```

**Response:**
```json
{
  "success": true,
  "data": {
    "https://www.squareyards.com/sale/5-bhk-for-sale-in-indiranagar-bangalore": [
      { /* property object */ },
      { /* property object */ }
    ],
    "https://www.squareyards.com/sale/2-bhk-for-sale-in-whitefield": [
      { /* property object */ }
    ]
  },
  "total_urls": 2,
  "total_properties": 25,
  "file_path": "/data/scraped_properties.json"
}
```

### 3. Get Properties by URL

Retrieve all properties that were scraped from a specific URL.

**Endpoint:**
```
GET /api/scraped_properties/by_url?url=<ENCODED_URL>
```

**Query Parameters:**
- `url` (required, string): The property listing URL to retrieve properties for. Must be URL-encoded.

**Example:**
```bash
curl -G "http://localhost:8000/api/scraped_properties/by_url" \
  --data-urlencode 'url=https://www.squareyards.com/sale/5-bhk-for-sale-in-indiranagar-bangalore'
```

**Response:**
```json
{
  "success": true,
  "url": "https://www.squareyards.com/sale/5-bhk-for-sale-in-indiranagar-bangalore",
  "properties": [
    { /* property objects */ }
  ],
  "count": 5
}
```

### 4. Delete Properties by URL

Delete all properties scraped from a specific URL.

**Endpoint:**
```
DELETE /api/scraped_properties/by_url?url=<ENCODED_URL>
```

**Query Parameters:**
- `url` (required, string): The URL whose properties should be deleted.

**Example:**
```bash
curl -X DELETE -G "http://localhost:8000/api/scraped_properties/by_url" \
  --data-urlencode 'url=https://www.squareyards.com/sale/5-bhk-for-sale-in-indiranagar-bangalore'
```

**Response:**
```json
{
  "success": true,
  "message": "Properties deleted successfully",
  "url": "https://www.squareyards.com/sale/5-bhk-for-sale-in-indiranagar-bangalore",
  "total_urls_remaining": 1,
  "file_path": "/data/scraped_properties.json",
  "deleted_at": "2025-11-13T10:35:00"
}
```

### 5. Clear All Scraped Properties

Delete ALL properties from the data file. **WARNING: This is destructive!**

**Endpoint:**
```
DELETE /api/scraped_properties
```

**Example:**
```bash
curl -X DELETE "http://localhost:8000/api/scraped_properties"
```

**Response:**
```json
{
  "success": true,
  "message": "All data cleared successfully",
  "file_path": "/data/scraped_properties.json",
  "cleared_at": "2025-11-13T10:35:00"
}
```

## Workflow Example

### Step 1: Initial Scrape and Cache

First time you scrape a URL, it fetches fresh data and saves it to cache:

```bash
curl -G "http://localhost:8000/api/get_listing_details_batch" \
  --data-urlencode 'url=https://www.squareyards.com/sale/5-bhk-for-sale-in-indiranagar-bangalore' \
  --data-urlencode 'orig_query=5bhk with east facing parking' \
  --data-urlencode 'batch_size=10'
```

Response includes:
```json
{
  "from_cache": false,
  "api_calls_made": 2,
  "persistence": { ... }
}
```

### Step 2: Instant Cache Hit

Call the same endpoint again (default `use_cache=true`):

```bash
curl -G "http://localhost:8000/api/get_listing_details_batch" \
  --data-urlencode 'url=https://www.squareyards.com/sale/5-bhk-for-sale-in-indiranagar-bangalore' \
  --data-urlencode 'orig_query=5bhk with east facing parking'
```

Response is instant (0 API calls):
```json
{
  "from_cache": true,
  "api_calls_made": 0
}
```

### Step 3: Force Fresh Scrape

If you want updated data, set `use_cache=false`:

```bash
curl -G "http://localhost:8000/api/get_listing_details_batch" \
  --data-urlencode 'url=https://www.squareyards.com/sale/5-bhk-for-sale-in-indiranagar-bangalore' \
  --data-urlencode 'orig_query=5bhk with east facing parking' \
  --data-urlencode 'use_cache=false'
```

Response includes fresh data:
```json
{
  "from_cache": false,
  "api_calls_made": 2,
  "persistence": { ... }
}
```

### Step 4: Analyze or Export Data

You can now:
- Sort properties by relevance score
- Filter by price, location, or other criteria
- Export to CSV or other formats
- Run analytics on the collected data
- Build reports or dashboards

## Implementation Details

### Merge Mode

When saving properties, the system uses **merge mode by default**. This means:

- **New URLs**: Properties for new URLs are added to the file
- **Existing URLs**: Properties for existing URLs are **replaced** (not appended)
- **Other URLs**: Properties for other URLs are preserved

Example:

```
Initial state:
{
  "url-1": [prop1, prop2],
  "url-2": [prop3, prop4]
}

After saving new properties for "url-1":
{
  "url-1": [prop5, prop6, prop7],  // Replaced
  "url-2": [prop3, prop4]           // Unchanged
}
```

### File Location Configuration

To use a custom location for the data file, you can configure it:

```python
from services.data_persistence_service import DataPersistenceService

# Set custom path
DataPersistenceService.set_data_file_path('/custom/path/properties.json')
```

### Error Handling

All endpoints include comprehensive error handling:

```json
{
  "success": false,
  "error": "Description of what went wrong",
  "message": "User-friendly error message"
}
```

## Usage in Frontend

### Using the Batch Endpoint

```javascript
// Scrape and save properties in one call
async function scrapeAndSave(url, query) {
  const response = await fetch(
    `/api/get_listing_details_batch?url=${encodeURIComponent(url)}&orig_query=${encodeURIComponent(query)}`
  );
  const data = await response.json();

  console.log(`Saved ${data.count} properties`);
  console.log(`Persistence info:`, data.persistence);

  return data.properties;
}
```

### Retrieving Saved Data

```javascript
// Get all properties from all URLs
async function getAllProperties() {
  const response = await fetch('/api/scraped_properties');
  const data = await response.json();

  console.log(`Total URLs: ${data.total_urls}`);
  console.log(`Total properties: ${data.total_properties}`);

  return data.data;
}

// Get properties from specific URL
async function getPropertiesByUrl(url) {
  const response = await fetch(
    `/api/scraped_properties/by_url?url=${encodeURIComponent(url)}`
  );
  const data = await response.json();

  if (data.success) {
    return data.properties;
  } else {
    console.error('URL not found');
    return [];
  }
}
```

### Deleting Data

```javascript
// Delete properties from specific URL
async function deleteByUrl(url) {
  const response = await fetch(
    `/api/scraped_properties/by_url?url=${encodeURIComponent(url)}`,
    { method: 'DELETE' }
  );
  const data = await response.json();

  if (data.success) {
    console.log('Properties deleted');
  }
}

// Clear all data
async function clearAllData() {
  const confirmed = confirm('Are you sure? This will delete all saved properties!');
  if (!confirmed) return;

  const response = await fetch('/api/scraped_properties', { method: 'DELETE' });
  const data = await response.json();

  if (data.success) {
    console.log('All data cleared');
  }
}
```

## Benefits

1. **Persistent Storage**: Data persists across application restarts
2. **Cost Reduction**: Avoid re-scraping the same URLs repeatedly
3. **Historical Data**: Build a database of properties over time
4. **Analysis**: Perform analytics on collected data
5. **Incremental Updates**: Only scrape new properties or refresh existing ones
6. **Data Auditing**: Track which URLs were scraped and when

## Best Practices

1. **Regular Backups**: Periodically back up the `data/scraped_properties.json` file
2. **Archive Old Data**: Periodically move old URLs to archive files
3. **Scrape Responsibly**: Don't scrape the same URL too frequently to respect server resources
4. **Monitor File Size**: The JSON file grows as you collect more properties
5. **Version Control**: Don't commit `data/scraped_properties.json` to git (add to `.gitignore`)

## Sample Data File

Here's a complete example of what the data file looks like:

```json
{
  "https://www.squareyards.com/sale/3-bhk-for-sale-in-whitefield-bangalore": [
    {
      "title": "3 BHK Apartment for Sale in Whitefield, Bangalore",
      "price": "₹ 2.5 Cr",
      "location": "Whitefield, Bangalore",
      "bedrooms": 3,
      "bathrooms": 2,
      "area": "1400",
      "facing": "North Facing",
      "parking": "2 Covered",
      "flooring": "Laminated Flooring",
      "furnishing": "Semi-Furnished",
      "description": "Spacious 3 BHK apartment...",
      "agent_name": "John Doe",
      "agent_rating": 4.5,
      "agent_url": "https://www.squareyards.com/agent/john-doe/123456",
      "relevance_score": 7,
      "relevance_reason": "Matched: bedrooms (3 BHK), location (Whitefield), parking (2 Covered)",
      "property_url": "https://www.squareyards.com/resale-3-bhk-apartment-in-whitefield..."
    }
  ]
}
```

## Troubleshooting

### "URL not found in data file"

This means the URL hasn't been scraped yet or the properties were deleted. Scrape the URL using the batch endpoint first.

### File permission errors

Ensure the `/data` directory exists and the application has write permissions:

```bash
mkdir -p /data
chmod 755 /data
```

### Large file size

If the data file grows too large, consider:
- Archiving old data to separate files
- Deleting properties older than a certain date
- Filtering to keep only high-relevance properties

---

**See Also:**
- [Batch API Integration](./NEXTJS_BATCH_API_INTEGRATION.md)
- [SSE Integration](./NEXTJS_SSE_INTEGRATION.md)
