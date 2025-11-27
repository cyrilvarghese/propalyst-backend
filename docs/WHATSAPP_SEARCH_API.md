# WhatsApp Listings Search API

Search extracted WhatsApp listings with fuzzy matching and filtering.

---

## 📡 **Endpoint**

```
GET /api/whatsapp-listings/search
```

**Description:** Search structured data extracted from WhatsApp messages (supply/demand listings only).

---

## 🔍 **Query Parameters**

| Parameter | Type | Required | Default | Range | Description |
|-----------|------|----------|---------|-------|-------------|
| `agent_name` | string | No | - | - | Agent or company name to search for |
| `property_query` | string | No | - | - | Property type or project name (e.g., "Villa", "3BHK") |
| `location` | string | No | - | - | Location to search for |
| `message_type` | string | No | - | enum | Filter by type: `supply_sale`, `supply_rent`, `demand_buy`, `demand_rent` |
| `limit` | integer | No | 100 | 1-500 | Maximum number of results to return |
| `similarity_threshold` | float | No | 0.3 | 0-1 | Fuzzy matching threshold (lower = more lenient) |

**Note:** At least one search parameter (agent_name, property_query, location, or message_type) is required.

---

## 🎯 **Search Strategy**

Uses **HYBRID STRATEGY** for optimal performance:

1. **Database-level exact matching** (fast, uses indexes)
   - ILIKE queries on indexed fields
   - Returns exact substring matches

2. **Client-side fuzzy matching** (handles typos, variations)
   - Uses SequenceMatcher for similarity scoring
   - Threshold: 0.3 by default (30% similarity)

3. **SET INTERSECTION (AND logic)**
   - All specified filters must match
   - Results sorted by relevance score

---

## 📊 **Search Fields**

### **Agent Search** (`agent_name`)
Searches across:
- `agent_name` - Agent's name
- `agent_contact` - Phone number
- `company_name` - Company/firm name

### **Property Search** (`property_query`)
Searches across:
- `property_type` - apartment, villa, plot, etc.
- `project_name` - Project/building name

### **Location Search** (`location`)
Searches:
- `location` - Normalized location field

---

## 📋 **Response Format**

**Success Response (200 OK):**
```json
{
  "success": true,
  "data": [
    {
      "id": "uuid-here",
      "source_message_id": "uuid-here",
      "message_date": "2025-11-26T10:30:00Z",
      "agent_name": "Tajamul Mohiuddin",
      "agent_contact": "+919876543210",
      "company_name": "CREA",
      "raw_message": "Original WhatsApp message text...",
      "message_type": "supply_sale",
      "property_type": "villa",
      "area_sqft": 3500,
      "price": 35000000,
      "price_text": "3.5 Cr",
      "location": "Whitefield, Bangalore",
      "project_name": "Prestige Golfshire",
      "furnishing_status": "semi_furnished",
      "parking_count": 2,
      "parking_text": "2 covered",
      "facing_direction": "east",
      "special_features": ["corner_plot", "gated_community"],
      "llm_json": {...},
      "created_at": "2025-11-26T10:35:00Z"
    }
  ],
  "count": 1,
  "message": "Found 1 WhatsApp listings matching location='Whitefield'",
  "metadata": {
    "filters_applied": {
      "agent_name": null,
      "property_query": null,
      "location": "Whitefield",
      "message_type": null
    },
    "exact_matches": 1,
    "fuzzy_matches": 0,
    "search_strategy": "hybrid_intersection",
    "source": "whatsapp_listings_relevant"
  }
}
```

**Error Response:**
```json
{
  "success": false,
  "data": [],
  "count": 0,
  "message": "At least one search parameter is required"
}
```

---

## 🚀 **Usage Examples**

### **1. Search by Location**
```bash
curl -X GET "http://localhost:8000/api/whatsapp-listings/search?location=Whitefield"
```

### **2. Search by Agent Name**
```bash
curl -X GET "http://localhost:8000/api/whatsapp-listings/search?agent_name=Tajamul"
```

### **3. Search by Property Type**
```bash
curl -X GET "http://localhost:8000/api/whatsapp-listings/search?property_query=Villa"
```

### **4. Multiple Filters (AND logic)**
```bash
curl -X GET "http://localhost:8000/api/whatsapp-listings/search?location=Indiranagar&property_query=3BHK&message_type=supply_sale"
```

### **5. With Custom Limit**
```bash
curl -X GET "http://localhost:8000/api/whatsapp-listings/search?location=Koramangala&limit=50"
```

### **6. Fuzzy Search (Handles Typos)**
```bash
# Will match "Whitefield" even if you type "Whitefild" (typo)
curl -X GET "http://localhost:8000/api/whatsapp-listings/search?location=Whitefild&similarity_threshold=0.7"
```

---

## 💻 **JavaScript/TypeScript Examples**

### **Simple Search**
```javascript
async function searchListings(location) {
  const response = await fetch(
    `http://localhost:8000/api/whatsapp-listings/search?location=${encodeURIComponent(location)}`
  );
  const result = await response.json();

  if (result.success) {
    console.log(`Found ${result.count} listings`);
    return result.data;
  } else {
    console.error(result.message);
    return [];
  }
}

// Usage
const listings = await searchListings("Whitefield");
```

### **Multi-Filter Search**
```javascript
async function searchWithFilters(filters) {
  const params = new URLSearchParams();

  if (filters.agent) params.append('agent_name', filters.agent);
  if (filters.property) params.append('property_query', filters.property);
  if (filters.location) params.append('location', filters.location);
  if (filters.type) params.append('message_type', filters.type);
  if (filters.limit) params.append('limit', filters.limit);

  const response = await fetch(
    `http://localhost:8000/api/whatsapp-listings/search?${params}`
  );
  const result = await response.json();

  return result;
}

// Usage
const results = await searchWithFilters({
  location: 'Indiranagar',
  property: '3BHK',
  type: 'supply_sale',
  limit: 50
});

console.log(results.metadata); // Shows search strategy and match counts
```

### **With TypeScript Types**
```typescript
interface WhatsAppListing {
  id: string;
  source_message_id: string;
  message_date: string;
  agent_name: string | null;
  agent_contact: string | null;
  company_name: string | null;
  raw_message: string;
  message_type: 'supply_sale' | 'supply_rent' | 'demand_buy' | 'demand_rent';
  property_type: string | null;
  area_sqft: number | null;
  price: number | null;
  price_text: string | null;
  location: string | null;
  project_name: string | null;
  furnishing_status: string | null;
  parking_count: number | null;
  parking_text: string | null;
  facing_direction: string | null;
  special_features: string[] | null;
  llm_json: any;
  created_at: string;
}

interface SearchResponse {
  success: boolean;
  data: WhatsAppListing[];
  count: number;
  message: string;
  metadata?: {
    filters_applied: {
      agent_name: string | null;
      property_query: string | null;
      location: string | null;
      message_type: string | null;
    };
    exact_matches: number;
    fuzzy_matches: number;
    search_strategy: string;
    source: string;
  };
}

async function searchListings(
  location?: string,
  property?: string,
  agent?: string
): Promise<SearchResponse> {
  const params = new URLSearchParams();
  if (location) params.append('location', location);
  if (property) params.append('property_query', property);
  if (agent) params.append('agent_name', agent);

  const response = await fetch(
    `http://localhost:8000/api/whatsapp-listings/search?${params}`
  );

  return await response.json();
}
```

---

## 🐍 **Python Example**

```python
import requests
from typing import Optional, Dict, Any, List

def search_whatsapp_listings(
    agent_name: Optional[str] = None,
    property_query: Optional[str] = None,
    location: Optional[str] = None,
    message_type: Optional[str] = None,
    limit: int = 100
) -> Dict[str, Any]:
    """Search WhatsApp listings with filters"""

    url = "http://localhost:8000/api/whatsapp-listings/search"

    params = {}
    if agent_name:
        params['agent_name'] = agent_name
    if property_query:
        params['property_query'] = property_query
    if location:
        params['location'] = location
    if message_type:
        params['message_type'] = message_type
    if limit != 100:
        params['limit'] = limit

    response = requests.get(url, params=params)
    return response.json()

# Usage examples
if __name__ == "__main__":
    # Search by location
    results = search_whatsapp_listings(location="Whitefield")
    print(f"Found {results['count']} listings")

    # Multi-filter search
    results = search_whatsapp_listings(
        location="Indiranagar",
        property_query="3BHK",
        message_type="supply_sale"
    )

    for listing in results['data']:
        print(f"{listing['property_type']} in {listing['location']}")
        print(f"Price: {listing['price_text']}")
        print(f"Agent: {listing['agent_name']}")
        print("---")
```

---

## 🔍 **Search Behavior**

### **Exact Matching (Fast)**
- Uses database ILIKE queries
- Returns results with substring matches
- Example: `location=White` matches "**White**field"

### **Fuzzy Matching (Comprehensive)**
- Handles typos and variations
- Uses similarity threshold (default: 0.3)
- Example: `location=Whitefild` (typo) matches "Whitefield"

### **AND Logic**
When multiple filters are specified, **ALL must match**:

```bash
# This returns listings that match ALL three conditions:
GET /search?agent_name=Tajamul&location=Whitefield&property_query=Villa
```

---

## 📈 **Performance**

- **Fast:** Database indexes + efficient queries
- **Scalable:** Handles 1000s of listings
- **Smart:** Only runs fuzzy search if exact matches < limit

**Typical response times:**
- Exact matches only: ~50-100ms
- With fuzzy matching: ~200-500ms

---

## ⚙️ **Configuration**

### **Similarity Threshold**

Adjust fuzzy matching sensitivity:

| Threshold | Behavior |
|-----------|----------|
| `0.1` | Very lenient (many false positives) |
| `0.3` | Balanced (default) |
| `0.5` | Moderate |
| `0.7` | Strict (fewer false positives) |
| `0.9` | Very strict (almost exact match) |

```bash
# Lenient search (catches more typos)
GET /search?location=Whitefield&similarity_threshold=0.2

# Strict search (fewer false matches)
GET /search?location=Whitefield&similarity_threshold=0.8
```

---

## 🔗 **Related APIs**

| Endpoint | Purpose |
|----------|---------|
| `GET /api/whatsapp-listings` | Get all extracted listings (paginated) |
| `GET /api/whatsapp-listings/stats` | Get extraction statistics |
| `POST /api/whatsapp-listings/extract-all-stream` | Stream extraction process |
| `POST /api/whatsapp-listings/extract/{id}` | Extract single message |

---

## 💡 **Tips**

1. **Use specific filters** for best results
2. **Combine filters** (AND logic) to narrow down results
3. **Adjust similarity_threshold** if getting too many/few results
4. **Use message_type filter** to search only sales or rentals
5. **Check metadata** in response to see exact vs fuzzy match counts

---

**For complete API documentation, see: [docs/UI_INTEGRATION_GUIDE.md](UI_INTEGRATION_GUIDE.md)**
