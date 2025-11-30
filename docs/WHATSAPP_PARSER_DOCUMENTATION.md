# WhatsApp Parser & Extraction API

Complete documentation for the two-stage WhatsApp message processing pipeline.

---

## Quick Reference

### **Three APIs:**

1. **POST /api/whatsapp-raw/upload-file** - Upload & parse (Stage 1, no LLM)
2. **POST /api/whatsapp-raw/process-unprocessed-stream** - Process with LLM (Stage 2)
3. **GET /api/whatsapp-raw/raw-stats** - Check status

### **User Flow:**
```
Upload file → Check stats → Process with LLM
```

---

## API Endpoints

### **1. POST /api/whatsapp-raw/upload-file**

**STAGE 1: Upload & Parse (Fast, No LLM)**

**URL:**
```
POST http://localhost:8000/api/whatsapp-raw/upload-file
```

**Request:**
```http
Content-Type: multipart/form-data
file: chunk_100.txt
```

**Response:**
```json
{
  "success": true,
  "messages_parsed": 500,
  "messages_inserted": 300,
  "messages_skipped": 200,
  "ready_for_llm": 670,
  "message": "Upload complete! 300 new messages inserted, 200 duplicates skipped. 670 total messages ready for LLM processing."
}
```

**What it does:**
- Automatically detects format (iOS or Android)
- Parses file with format-specific regex
- Calculates MD5 hash for each message
- Inserts into `whatsapp_raw_messages` table
- Skips duplicates automatically
- **NO LLM calls** (instant)
- Logs detected format to server console

---

### **2. POST /api/whatsapp-raw/process-unprocessed-stream**

**STAGE 2: Process with LLM (Streaming)**

**URL:**
```
POST http://localhost:8000/api/whatsapp-raw/process-unprocessed-stream?limit=1000
```

**Parameters:**
- `limit` (optional, default: 1000) - Max messages to process

**Response (Server-Sent Events):**
```
event: start
data: {"batch_size": 670}

event: progress
data: {
  "status": "completed",
  "progress": "1/670",
  "message_type": "supply_sale",
  "location": "Whitefield",
  "split_index": "1/2"
}

event: progress
data: {
  "status": "completed",
  "progress": "2/670",
  "message_type": "supply_rent",
  "location": "Richmond Town",
  "split_index": null
}

event: complete
data: {
  "batch_size": 670,
  "messages_extracted": 750,
  "messages_failed": 10,
  "message": "Processing complete! Extracted: 750, Failed: 10"
}
```

**What it does:**
- Reads unprocessed messages from `whatsapp_raw_messages`
- For each: Calls Gemini API (split + extract)
- Inserts into `whatsapp_listing_data`
- Marks raw message as processed
- Streams real-time progress

---

### **3. GET /api/whatsapp-raw/raw-stats**

**Check Processing Status**

**URL:**
```
GET http://localhost:8000/api/whatsapp-raw/raw-stats
```

**Response:**
```json
{
  "total_messages": 792,
  "processed": 11,
  "unprocessed": 781,
  "deleted": 21,
  "media": 90,
  "ready_for_llm": 670,
  "unique_senders": 25,
  "date_range": {
    "earliest": "2025-01-01T10:00:00Z",
    "latest": "2025-01-31T23:59:59Z"
  }
}
```

**Fields:**
- `total_messages` - Total in raw table
- `processed` - Already processed by LLM
- `unprocessed` - Not yet processed
- `deleted` - Deleted messages (filtered out)
- `media` - Media-only messages (filtered out)
- `ready_for_llm` - Unprocessed AND not deleted AND not media
- `unique_senders` - Count of unique sender names

---

## Supported WhatsApp Export Formats

The parser supports **two WhatsApp export formats** and automatically detects which one is used:

### **Format 1: iOS (iPhone)**

**Format Patterns:**
- `[DD/MM/YY, HH:MM:SS AM/PM] Sender: Message` (12-hour with AM/PM, 2-digit year)
- `[DD/MM/YYYY, HH:MM:SS] Sender: Message` (24-hour, 4-digit year)

**Examples:**
```
[06/07/16, 8:04:11 PM] ~ Vino: Sir i am accepting it is my mistake
[10/07/16, 1:45:43 PM] Srinivas: Available for sale in Bangalore
[11/3/25, 12:54:10 PM] ‪+91 98861 35757‬: Rental Inventory
[26/11/2025, 20:53:56] Naresh Shetty: Test message
```

**Characteristics:**
- Timestamp in square brackets `[...]`
- **Time format**: 12-hour with AM/PM (e.g., `8:04:11 PM`) **OR** 24-hour (e.g., `20:53:56`)
- Always includes seconds (HH:MM:SS)
- **Year format**: 2-digit (YY) **OR** 4-digit (YYYY)
- Bracket-space separator `] ` before sender name
- Single-digit days/months allowed (e.g., `11/3/25` = March 11, 2025)

---

### **Format 2: Android**

**Format Patterns:**
- `DD/MM/YY, HH:MM AM/PM - Sender: Message` (12-hour with AM/PM, 2-digit year)
- `DD/MM/YYYY, HH:MM - Sender: Message` (24-hour, 4-digit year)
- `DD/MM/YYYY, HH:MM - Sender: Message` (24-hour, 4-digit year)

**Examples:**
```
28/11/2025, 14:30 - John Doe: Hello everyone
11/22/25, 12:16 PM - Naresh S: Good Morning
4/28/25, 8:31 AM - Vinay Gowda: *Purchasing Requirement for Villa*
3/4/2025, 9:15 - Jane Smith: Property available
```

**Characteristics:**
- No brackets around timestamp (unlike iOS)
- **Time format**: 24-hour (e.g., `14:30`) **OR** 12-hour with AM/PM (e.g., `12:16 PM`)
- No seconds (HH:MM only)
- **Year format**: 2-digit (YY) **OR** 4-digit (YYYY)
- Dash-space separator ` - ` before sender name
- Single-digit days/months allowed (3/4/2025 = April 3rd, 2025)

---

### **Format Detection (Automatic)**

The parser automatically detects the format by:
1. Scanning the first 50 lines of the file
2. Counting matches for each format
3. Returning the format with the most matches
4. Logging the detected format to console (e.g., `[WhatsAppRaw] Format detected: IOS (from file: chunk_100.txt)`)

**Example Server Output:**
```
[WhatsAppRaw] Format detected: ANDROID (from file: properties_may_2025.txt)
[WhatsAppRaw] Parsed 487 messages from file (format: android)
[WhatsAppRaw] Inserted 300 new, skipped 187 duplicates
```

### **Manual Format Override**

If automatic detection fails, you can specify the format programmatically:

```python
from services.whatsapp_parser_service import WhatsAppParserService, WhatsAppFormatType

# iOS format
messages = WhatsAppParserService.parse_file_content(
    content,
    format=WhatsAppFormatType.IOS
)

# Android format
messages = WhatsAppParserService.parse_file_content(
    content,
    format=WhatsAppFormatType.ANDROID
)
```

---

## Complete Workflow

### **Step 1: Upload File**

```bash
curl -X POST "http://localhost:8000/api/whatsapp-raw/upload-file" \
  -F "file=@chunk_100.txt"
```

**Response:**
```json
{
  "messages_inserted": 300,
  "messages_skipped": 200,
  "ready_for_llm": 670
}
```

**Database after Step 1:**
```
whatsapp_raw_messages: 300 rows (processed = false)
whatsapp_listing_data: 0 rows
```

---

### **Step 2: Check Stats**

```bash
curl "http://localhost:8000/api/whatsapp-raw/raw-stats"
```

**Response:**
```json
{
  "ready_for_llm": 670
}
```

---

### **Step 3: Process with LLM**

```bash
curl -N -X POST "http://localhost:8000/api/whatsapp-raw/process-unprocessed-stream"
```

**Response (streaming):**
```
event: start
data: {"batch_size": 670}

event: progress
data: {"progress": "1/670", "status": "completed"}
...

event: complete
data: {"messages_extracted": 750}
```

**Database after Step 3:**
```
whatsapp_raw_messages: 300 rows (processed = true)
whatsapp_listing_data: 750 rows
```

---

## Two-Stage Architecture

### **Why Two Stages?**

1. **Deduplication** - Upload same file twice = automatic duplicate detection
2. **Recovery** - LLM fails = raw data is safe
3. **User Control** - Upload now, process later
4. **Resume** - Server crash = continue from where left off
5. **Reprocessing** - Update prompts, reprocess old messages

### **Stage 1: Raw Messages**

**Table:** `whatsapp_raw_messages`

**Stores:** Parsed messages with hash for deduplication

**Fast:** No LLM calls (~1 second per 500 messages)

**Cost:** $0

---

### **Stage 2: Structured Data**

**Table:** `whatsapp_listing_data`

**Stores:** Extracted structured property data

**Slow:** LLM calls (~2 seconds per message)

**Cost:** ~$0.0001 per message

---

## Database Schema

### **Table 1: whatsapp_raw_messages (Stage 1)**

```sql
CREATE TABLE whatsapp_raw_messages (
  id uuid PRIMARY KEY,
  message_hash text UNIQUE,        -- MD5 for deduplication
  message_date timestamptz NOT NULL,
  sender_name text NOT NULL,
  message_text text NOT NULL,
  is_deleted boolean,
  is_media boolean,
  source_file text,
  line_number integer,
  processed boolean DEFAULT false,  -- LLM processing status
  processed_at timestamptz,
  created_at timestamptz
);
```

---

### **Table 2: whatsapp_listing_data (Stage 2)**

```sql
CREATE TABLE whatsapp_listing_data (
  id uuid PRIMARY KEY,
  source_raw_message_id uuid,      -- Links to Stage 1
  message_date timestamptz,
  agent_name text,
  agent_contact text,
  raw_message text NOT NULL,
  message_type text NOT NULL,
  property_type text,
  bhk_config integer,
  area_sqft numeric,
  price numeric,
  price_text text,
  location text,
  project_name text,
  furnishing_status text,
  parking_count integer,
  facing_direction text,
  special_features text[],
  llm_json jsonb,
  created_at timestamptz
);
```

---

## Example Scenarios

### **Scenario 1: Upload & Process Immediately**

```javascript
// Step 1: Upload
const upload = await fetch('/api/whatsapp-raw/upload-file', {
  method: 'POST',
  body: formData
}).then(r => r.json());

console.log(`${upload.messages_inserted} new messages`);

// Step 2: Process immediately
const eventSource = new EventSource('/api/whatsapp-raw/process-unprocessed-stream');

eventSource.addEventListener('progress', (e) => {
  const data = JSON.parse(e.data);
  console.log(`${data.progress} - ${data.message_type}`);
});

eventSource.addEventListener('complete', (e) => {
  const data = JSON.parse(e.data);
  console.log(`Done! ${data.messages_extracted} extracted`);
  eventSource.close();
});
```

---

### **Scenario 2: Upload Multiple Files, Process Later**

```javascript
// Morning: Upload 3 files
await uploadFile('chunk_001.txt');  // 300 messages
await uploadFile('chunk_002.txt');  // 250 messages
await uploadFile('chunk_003.txt');  // 400 messages

// Check stats
const stats = await fetch('/api/whatsapp-raw/raw-stats').then(r => r.json());
console.log(`Ready to process: ${stats.ready_for_llm}`);  // 850 messages

// Evening: Start processing
fetch('/api/whatsapp-raw/process-unprocessed-stream', {method: 'POST'});
```

---

### **Scenario 3: Upload Same File Twice (Deduplication)**

```javascript
// First upload
const upload1 = await uploadFile('chunk_100.txt');
// Result: 300 inserted, 0 skipped

// Upload same file again
const upload2 = await uploadFile('chunk_100.txt');
// Result: 0 inserted, 300 skipped (all duplicates!)

// Check stats
const stats = await fetch('/api/whatsapp-raw/raw-stats').then(r => r.json());
// ready_for_llm: 250 (still same, no duplicates added)
```

---

### **Scenario 4: Resume After Interruption**

```javascript
// Processing crashed after 100 messages

// Check status
const stats = await fetch('/api/whatsapp-raw/raw-stats').then(r => r.json());
console.log(`Processed: ${stats.processed}`);      // 100
console.log(`Still to do: ${stats.ready_for_llm}`); // 570

// Resume processing
fetch('/api/whatsapp-raw/process-unprocessed-stream', {method: 'POST'});
// Continues from message 101!
```

---

## Performance

### **Stage 1 (Upload):**
- **Speed:** ~1 second per 500 messages
- **Cost:** $0 (no LLM)

### **Stage 2 (LLM Processing):**
- **Speed:** ~2 seconds per message
- **Cost:** ~$0.0001 per message
- **Example:** 670 messages = 22 minutes, $0.067

---

## Environment Variables

```bash
GEMINI_AI_API_KEY=your_api_key
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
```

---

## Database Setup

Run these SQL files in Supabase **in order**:

```sql
-- 1. Stage 1 table
-- Run: sql/whatsapp_raw_messages.sql

-- 2. Stage 2 table
-- Run: sql/whatsapp_listing_data.sql
```

---

## Monitoring Queries

### **Check Processing Progress**

```sql
SELECT COUNT(*)
FROM whatsapp_raw_messages
WHERE processed = false
  AND is_deleted = false
  AND is_media = false;
```

### **View Unprocessed by File**

```sql
SELECT source_file, COUNT(*) as count
FROM whatsapp_raw_messages
WHERE processed = false
GROUP BY source_file;
```

### **Audit Trail**

```sql
SELECT
  wrm.sender_name,
  wrm.message_text as original,
  wld.message_type,
  wld.location
FROM whatsapp_raw_messages wrm
JOIN whatsapp_listing_data wld
  ON wrm.id = wld.source_raw_message_id
LIMIT 10;
```

---

**Last Updated:** 2025-11-27
