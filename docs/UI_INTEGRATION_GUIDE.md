# WhatsApp Listing Extraction - API Documentation

API endpoints for WhatsApp message extraction and statistics.

---

## 📡 **Available Endpoints**

### **1. Stream Extraction (Batch Processing)**

**Endpoint:**
```
POST /api/whatsapp-listings/extract-all-stream?batch_size={size}
```

**Description:**
Processes unprocessed WhatsApp messages from `crea_wapp` table using LLM extraction. Database automatically tracks processed messages via LEFT JOIN with `whatsapp_listing_data` table.

**Parameters:**
| Parameter | Type | Required | Default | Range | Description |
|-----------|------|----------|---------|-------|-------------|
| batch_size | integer | No | 100 | 1-500 | Number of messages to process in this batch |

**Response Type:** Server-Sent Events (SSE) Stream

**Event Types:**

**Start Event:**
```json
{
  "type": "start",
  "batch_size": 100
}
```

**Progress Event:**
```json
{
  "type": "progress",
  "message_id": "uuid-here",
  "status": "completed",  // or "skipped" or "failed"
  "message_type": "supply_sale",  // message classification
  "is_relevant": true,
  "progress": "47/100"
}
```

**Complete Event:**
```json
{
  "type": "complete",
  "batch_size": 100,
  "messages_extracted": 85,
  "messages_skipped": 12,
  "messages_failed": 3,
  "message": "Batch complete! Extracted: 85, Skipped: 12, Failed: 3"
}
```

**Error Event:**
```json
{
  "type": "error",
  "message": "Error description"
}
```

**Message Status Types:**
- `completed`: Relevant message (supply/demand) extracted successfully
- `skipped`: Non-relevant message (garbage, greeting, generic_info, media)
- `failed`: Extraction or database error

**Message Types:**
- `supply_sale`: Property for sale
- `supply_rent`: Property for rent
- `demand_buy`: Buyer requirement
- `demand_rent`: Rental requirement
- `greeting`: Hi/Hello messages
- `garbage`: Media, empty, or junk messages
- `generic_info`: General information

**Examples:**
```bash
# Process 10 messages (testing)
curl -X POST "http://localhost:8000/api/whatsapp-listings/extract-all-stream?batch_size=10"

# Process 100 messages (default)
curl -X POST "http://localhost:8000/api/whatsapp-listings/extract-all-stream"

# Process 200 messages (faster processing)
curl -X POST "http://localhost:8000/api/whatsapp-listings/extract-all-stream?batch_size=200"
```

---

### **2. Get Statistics**

**Endpoint:**
```
GET /api/whatsapp-listings/stats
```

**Description:**
Returns overall extraction statistics using database queries (LEFT JOIN to count unprocessed messages).

**Response:**
```json
{
  "success": true,
  "data": {
    "total_messages": 2847,
    "extracted_count": 1523,
    "remaining_count": 1324,
    "progress_percentage": 53.49,
    "message_type_breakdown": {
      "supply_sale": 892,
      "supply_rent": 345,
      "demand_buy": 178,
      "demand_rent": 67,
      "greeting": 23,
      "garbage": 18
    }
  },
  "message": "Extraction statistics retrieved"
}
```

**Example:**
```bash
curl -X GET "http://localhost:8000/api/whatsapp-listings/stats"
```

---

### **3. Get Extracted Listings**

**Endpoint:**
```
GET /api/whatsapp-listings?limit={limit}&offset={offset}
```

**Description:**
Returns paginated list of extracted listings from `whatsapp_listing_data` table.

**Parameters:**
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| limit | integer | No | 100 | Maximum number of listings to return |
| offset | integer | No | 0 | Number of listings to skip (pagination) |

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "id": "uuid",
      "source_message_id": "uuid",
      "message_date": "2025-11-26T10:30:00",
      "agent_contact": "+919876543210",
      "agent_name": "John Doe",
      "company_name": "ABC Realty",
      "raw_message": "3BHK for sale...",
      "message_type": "supply_sale",
      "property_type": "apartment",
      "area_sqft": 1500,
      "price": 8500000,
      "price_text": "85 lakhs",
      "location": "Whitefield, Bangalore",
      "project_name": "Prestige Lakeside",
      "furnishing_status": "semi_furnished",
      "parking_count": 2,
      "parking_text": "2 covered",
      "facing_direction": "east",
      "special_features": ["balcony", "club_house"],
      "llm_json": {...},
      "created_at": "2025-11-26T10:35:00"
    }
  ],
  "count": 100,
  "message": "Listings retrieved successfully"
}
```

**Example:**
```bash
# Get first 50 listings
curl -X GET "http://localhost:8000/api/whatsapp-listings?limit=50&offset=0"

# Get next 50 listings
curl -X GET "http://localhost:8000/api/whatsapp-listings?limit=50&offset=50"
```

---

### **4. Extract Single Message (Testing)**

**Endpoint:**
```
POST /api/whatsapp-listings/extract/{message_id}
```

**Description:**
Extract and process a single message by ID. Useful for testing and debugging.

**Path Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| message_id | string (UUID) | Yes | Message UUID from `crea_wapp` table |

**Response:**
```json
{
  "success": true,
  "message": "Successfully processed message uuid - type: supply_sale",
  "is_relevant": true,
  "message_type": "supply_sale",
  "data": {
    "id": "uuid",
    "source_message_id": "uuid",
    "message_type": "supply_sale",
    "property_type": "apartment",
    "location": "Whitefield",
    "price": 8500000,
    ...
  }
}
```

**Example:**
```bash
curl -X POST "http://localhost:8000/api/whatsapp-listings/extract/a1b2c3d4-uuid-here"
```

---

## 📊 **Database Schema**

### **Source Table: `crea_wapp`**
Contains raw WhatsApp messages.

### **Destination Table: `whatsapp_listing_data`**
Contains extracted structured data.

**Progress Tracking:**
Database-driven using LEFT JOIN. No file-based progress tracking.

```sql
-- Query to find unprocessed messages
SELECT cw.*
FROM crea_wapp cw
LEFT JOIN whatsapp_listing_data wld ON cw.id = wld.source_message_id
WHERE wld.source_message_id IS NULL
ORDER BY cw.message_date DESC
LIMIT {batch_size};
```

---

## 🔄 **Typical Workflow**

### **Step 1: Check Statistics**
```bash
GET /api/whatsapp-listings/stats
```
Returns: Total messages, extracted count, remaining count, progress percentage

### **Step 2: Start Batch Extraction**
```bash
POST /api/whatsapp-listings/extract-all-stream?batch_size=100
```
Streams: Real-time progress events (start → progress → complete)

### **Step 3: Monitor Progress**
- Listen to SSE stream for real-time updates
- Each message streams: `{type: "progress", status: "completed/skipped/failed"}`

### **Step 4: Batch Complete**
- Receive `{type: "complete"}` event
- Call stats endpoint to see updated counts
- If remaining > 0, repeat Step 2

### **Step 5: View Extracted Data**
```bash
GET /api/whatsapp-listings?limit=100&offset=0
```
Returns: Paginated list of extracted listings

---

## ⚡ **Key Features**

### **Database-Driven Progress**
- No JSON files or manual tracking
- LEFT JOIN query finds unprocessed messages
- Idempotent: Safe to call multiple times

### **Message Classification**
- **Relevant**: `supply_sale`, `supply_rent`, `demand_buy`, `demand_rent`
- **Non-Relevant**: `greeting`, `garbage`, `generic_info`

### **Auto-Skip Logic**
- Media messages (`<Media omitted>`) → Classified as `garbage`, no LLM call
- Empty messages → Classified as `garbage`, no LLM call
- Non-relevant messages → Stored with minimal data

### **Real-Time Streaming**
- Server-Sent Events (SSE) for live progress
- No polling required
- Batch processing with configurable size

---

## 🛠️ **Error Handling**

**HTTP Status Codes:**
- `200`: Success
- `404`: Message not found (single message extraction)
- `500`: Server error (LLM failure, database error)

**Stream Error Events:**
```json
{
  "type": "error",
  "message": "Error description"
}
```

**Common Errors:**
- LLM API failure
- JSON parse error
- Database connection error
- Invalid message ID

---

## 📋 **API Summary Table**

| Endpoint | Method | Purpose | Response Type |
|----------|--------|---------|---------------|
| `/api/whatsapp-listings/extract-all-stream` | POST | Batch extraction with streaming | SSE Stream |
| `/api/whatsapp-listings/stats` | GET | Overall statistics | JSON |
| `/api/whatsapp-listings` | GET | Get extracted listings (paginated) | JSON |
| `/api/whatsapp-listings/extract/{id}` | POST | Extract single message | JSON |

---

**End of API Documentation**
