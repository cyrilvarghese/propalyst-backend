# Streaming Extraction API - Usage Examples

Complete guide for using the `/api/whatsapp-listings/extract-all-stream` endpoint with Server-Sent Events (SSE).

---

## 📡 **Endpoint Overview**

```
POST /api/whatsapp-listings/extract-all-stream?batch_size={size}
```

**Response Type:** Server-Sent Events (SSE) Stream
**Content-Type:** `text/event-stream`

---

## 🔥 **Live Stream Response Example**

Here's what the complete stream looks like from start to finish:

**✨ Using Named Events (Clean!):**

```
event: start
data: {"batch_size": 5}

event: progress
data: {"message_id": "a1b2c3d4-uuid-1", "status": "completed", "message_type": "supply_sale", "is_relevant": true, "progress": "1/5"}

event: progress
data: {"message_id": "e5f6g7h8-uuid-2", "status": "skipped", "message_type": "garbage", "is_relevant": false, "progress": "2/5", "reason": "media_omitted"}

event: progress
data: {"message_id": "i9j0k1l2-uuid-3", "status": "completed", "message_type": "demand_buy", "is_relevant": true, "progress": "3/5"}

event: progress
data: {"message_id": "m3n4o5p6-uuid-4", "status": "skipped", "message_type": "greeting", "is_relevant": false, "progress": "4/5"}

event: progress
data: {"message_id": "q7r8s9t0-uuid-5", "status": "failed", "error": "LLM API timeout", "progress": "5/5"}

event: complete
data: {"batch_size": 5, "messages_extracted": 2, "messages_skipped": 2, "messages_failed": 1, "message": "Batch complete! Extracted: 2, Skipped: 2, Failed: 1"}
```

**Benefits of named events:**
- ✅ Cleaner client code with separate event listeners
- ✅ No need to check `data.type` manually
- ✅ Better TypeScript/type safety
- ✅ Standard SSE practice

---

## 🚀 **Usage Examples**

### **1. cURL (Command Line)**

**Basic usage:**
```bash
curl -X POST "http://localhost:8000/api/whatsapp-listings/extract-all-stream?batch_size=10" \
  -H "Accept: text/event-stream" \
  --no-buffer
```

**With output to file:**
```bash
curl -X POST "http://localhost:8000/api/whatsapp-listings/extract-all-stream?batch_size=100" \
  -H "Accept: text/event-stream" \
  --no-buffer \
  > extraction_log.txt
```

**Parse events in real-time (with jq):**
```bash
curl -X POST "http://localhost:8000/api/whatsapp-listings/extract-all-stream?batch_size=10" \
  -H "Accept: text/event-stream" \
  --no-buffer \
  | while read -r line; do
      if [[ $line == data:* ]]; then
        echo "$line" | sed 's/data: //' | jq .
      fi
    done
```

---

### **2. JavaScript (Browser) - EventSource API** ⭐ **RECOMMENDED**

**✨ Super Clean Version (Named Events):**
```javascript
const eventSource = new EventSource(
  'http://localhost:8000/api/whatsapp-listings/extract-all-stream?batch_size=10'
);

// Separate handlers for each event type - MUCH cleaner!
eventSource.addEventListener('start', (event) => {
  const data = JSON.parse(event.data);
  console.log(`🚀 Starting batch: ${data.batch_size} messages`);
});

eventSource.addEventListener('progress', (event) => {
  const data = JSON.parse(event.data);

  if (data.status === 'completed') {
    console.log(`✓ ${data.progress} - ${data.message_type}`);
  } else if (data.status === 'skipped') {
    console.log(`⊘ ${data.progress} - ${data.message_type}`);
  } else if (data.status === 'failed') {
    console.error(`✗ ${data.progress} - ${data.error}`);
  }
});

eventSource.addEventListener('complete', (event) => {
  const data = JSON.parse(event.data);
  console.log('🎉 Batch complete!', data);
  eventSource.close();
});

eventSource.addEventListener('error', (event) => {
  const data = JSON.parse(event.data);
  console.error('❌ Error:', data.message);
  eventSource.close();
});

eventSource.onerror = (error) => {
  console.error('Connection error:', error);
  eventSource.close();
};
```

**Why this is better:**
- ✅ No need to check `if (data.type === 'progress')` manually
- ✅ Cleaner separation of concerns
- ✅ Easier to maintain and extend
- ✅ Standard EventSource pattern

**Complete example with UI updates (Named Events):**
```javascript
function startExtraction(batchSize = 100) {
  const eventSource = new EventSource(
    `http://localhost:8000/api/whatsapp-listings/extract-all-stream?batch_size=${batchSize}`
  );

  let stats = { extracted: 0, skipped: 0, failed: 0 };

  // 'start' event
  eventSource.addEventListener('start', (event) => {
    const data = JSON.parse(event.data);
    console.log(`🚀 Starting batch: ${data.batch_size} messages`);
    document.getElementById('status').textContent = 'Processing...';
  });

  // 'progress' event
  eventSource.addEventListener('progress', (event) => {
    const data = JSON.parse(event.data);

    // Update counters
    if (data.status === 'completed') {
      stats.extracted++;
      console.log(`✓ ${data.progress} - ${data.message_type}`);
    } else if (data.status === 'skipped') {
      stats.skipped++;
      console.log(`⊘ ${data.progress} - ${data.message_type}`);
    } else if (data.status === 'failed') {
      stats.failed++;
      console.error(`✗ ${data.progress} - ${data.error}`);
    }

    // Update UI
    document.getElementById('extracted').textContent = stats.extracted;
    document.getElementById('skipped').textContent = stats.skipped;
    document.getElementById('failed').textContent = stats.failed;
    document.getElementById('progress').textContent = data.progress;
  });

  // 'complete' event
  eventSource.addEventListener('complete', (event) => {
    const data = JSON.parse(event.data);
    console.log('🎉 Batch complete!', data);
    document.getElementById('status').textContent = 'Complete';
    eventSource.close();

    // Show summary
    alert(`
      Extraction Complete!
      Extracted: ${data.messages_extracted}
      Skipped: ${data.messages_skipped}
      Failed: ${data.messages_failed}
    `);
  });

  // 'error' event
  eventSource.addEventListener('error', (event) => {
    const data = JSON.parse(event.data);
    console.error('❌ Error:', data.message);
    document.getElementById('status').textContent = 'Error';
    eventSource.close();
  });

  // Connection error
  eventSource.onerror = (error) => {
    console.error('Connection error:', error);
    eventSource.close();
  };

  return eventSource;
}

// Usage
const stream = startExtraction(50);

// Stop early if needed
// stream.close();
```

---

### **3. JavaScript (Fetch API with Streaming)**

For better control and POST support (parses named events):

```javascript
async function streamExtraction(batchSize = 100) {
  const response = await fetch(
    `http://localhost:8000/api/whatsapp-listings/extract-all-stream?batch_size=${batchSize}`,
    {
      method: 'POST',
      headers: {
        'Accept': 'text/event-stream'
      }
    }
  );

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();

    if (done) {
      console.log('Stream complete');
      break;
    }

    // Decode chunk
    buffer += decoder.decode(value, { stream: true });

    // Split by double newline (SSE message separator)
    const messages = buffer.split('\n\n');
    buffer = messages.pop(); // Keep incomplete message in buffer

    for (const message of messages) {
      if (!message.trim()) continue;

      // Parse SSE message (event + data)
      const lines = message.split('\n');
      let eventType = 'message'; // Default
      let data = null;

      for (const line of lines) {
        if (line.startsWith('event: ')) {
          eventType = line.substring(7);
        } else if (line.startsWith('data: ')) {
          const jsonData = line.substring(6);
          try {
            data = JSON.parse(jsonData);
          } catch (e) {
            console.error('Parse error:', e);
          }
        }
      }

      if (data) {
        handleEvent(eventType, data);
      }
    }
  }
}

function handleEvent(eventType, data) {
  switch(eventType) {
    case 'start':
      console.log(`🚀 Starting: ${data.batch_size} messages`);
      break;
    case 'progress':
      console.log(`${data.status} - ${data.progress}`);
      break;
    case 'complete':
      console.log(`✓ Done! Extracted: ${data.messages_extracted}`);
      break;
    case 'error':
      console.error(`✗ Error: ${data.message}`);
      break;
  }
}

// Usage
streamExtraction(10);
```

---

### **4. Python - SSE Client**

**Using `sseclient-py` library:**

```bash
pip install sseclient-py requests
```

```python
import requests
from sseclient import SSEClient

def stream_extraction(batch_size=100):
    """Stream WhatsApp extraction with real-time updates (Named Events)"""

    url = f"http://localhost:8000/api/whatsapp-listings/extract-all-stream"
    params = {"batch_size": batch_size}

    response = requests.post(url, params=params, stream=True, headers={
        'Accept': 'text/event-stream'
    })

    client = SSEClient(response)

    stats = {'extracted': 0, 'skipped': 0, 'failed': 0}

    for event in client.events():
        data = json.loads(event.data)
        event_type = event.event or 'message'  # Get event type

        if event_type == 'start':
            print(f"🚀 Starting batch: {data['batch_size']} messages")

        elif event_type == 'progress':
            status = data['status']
            progress = data['progress']

            if status == 'completed':
                stats['extracted'] += 1
                print(f"✓ {progress} - {data['message_type']}")
            elif status == 'skipped':
                stats['skipped'] += 1
                print(f"⊘ {progress} - {data['message_type']}")
            elif status == 'failed':
                stats['failed'] += 1
                print(f"✗ {progress} - {data['error']}")

        elif event_type == 'complete':
            print(f"\n🎉 Batch Complete!")
            print(f"   Extracted: {data['messages_extracted']}")
            print(f"   Skipped: {data['messages_skipped']}")
            print(f"   Failed: {data['messages_failed']}")
            break

        elif event_type == 'error':
            print(f"❌ Error: {data['message']}")
            break

    return stats

# Usage
if __name__ == "__main__":
    import json

    # Process 10 messages (testing)
    stats = stream_extraction(batch_size=10)
    print(f"\nFinal stats: {stats}")
```

**Using `httpx` (async):**

```bash
pip install httpx
```

```python
import httpx
import json
import asyncio

async def stream_extraction_async(batch_size=100):
    """Async streaming extraction (Named Events)"""

    url = f"http://localhost:8000/api/whatsapp-listings/extract-all-stream"
    params = {"batch_size": batch_size}

    async with httpx.AsyncClient() as client:
        async with client.stream('POST', url, params=params, timeout=300.0) as response:
            event_type = None
            async for line in response.aiter_lines():
                if line.startswith('event: '):
                    event_type = line[7:]  # Extract event name

                elif line.startswith('data: '):
                    json_str = line[6:]  # Remove 'data: ' prefix
                    data = json.loads(json_str)

                    if event_type == 'start':
                        print(f"🚀 Started: {data['batch_size']}")

                    elif event_type == 'progress':
                        print(f"{data['status']} - {data['progress']}")

                    elif event_type == 'complete':
                        print(f"✓ Complete: {data['messages_extracted']} extracted")
                        break

                    elif event_type == 'error':
                        print(f"✗ Error: {data['message']}")
                        break

# Usage
asyncio.run(stream_extraction_async(10))
```

---

## 📋 **Event Schema Reference**

### **Event: `start`**
```
event: start
data: {"batch_size": 100}
```

**Data fields:**
- `batch_size` (integer): Number of messages in this batch

---

### **Event: `progress` - Completed**
```
event: progress
data: {
  "message_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "message_type": "supply_sale",
  "is_relevant": true,
  "progress": "47/100"
}
```

**Data fields:**
- `message_id` (string): UUID of the message
- `status` (string): "completed"
- `message_type` (string): supply_sale, supply_rent, demand_buy, demand_rent
- `is_relevant` (boolean): true for supply/demand messages
- `progress` (string): Current progress "X/Y"

---

### **Event: `progress` - Skipped**
```
event: progress
data: {
  "message_id": "660e8400-e29b-41d4-a716-446655440001",
  "status": "skipped",
  "message_type": "garbage",
  "is_relevant": false,
  "progress": "48/100",
  "reason": "media_omitted"
}
```

**Data fields:**
- `message_id` (string): UUID of the message
- `status` (string): "skipped"
- `message_type` (string): garbage, greeting, generic_info
- `is_relevant` (boolean): false for non-relevant messages
- `progress` (string): Current progress "X/Y"
- `reason` (string, optional): Why it was skipped

---

### **Event: `progress` - Failed**
```
event: progress
data: {
  "message_id": "770e8400-e29b-41d4-a716-446655440002",
  "status": "failed",
  "error": "LLM API timeout after 30 seconds",
  "progress": "49/100"
}
```

**Data fields:**
- `message_id` (string): UUID of the message
- `status` (string): "failed"
- `error` (string): Error description
- `progress` (string): Current progress "X/Y"

---

### **Event: `complete`**
```
event: complete
data: {
  "batch_size": 100,
  "messages_extracted": 85,
  "messages_skipped": 12,
  "messages_failed": 3,
  "message": "Batch complete! Extracted: 85, Skipped: 12, Failed: 3"
}
```

**Data fields:**
- `batch_size` (integer): Total messages in batch
- `messages_extracted` (integer): Successfully extracted (relevant messages)
- `messages_skipped` (integer): Skipped (non-relevant or media)
- `messages_failed` (integer): Failed with errors
- `message` (string): Summary message

---

### **Event: `error`**
```
event: error
data: {"message": "Database connection failed"}
```

**Data fields:**
- `message` (string): Error description

---

## 🎯 **Real-World Example: Processing All Messages**

Process all messages in batches of 100 until done:

```javascript
async function processAllMessages() {
  let totalExtracted = 0;
  let totalSkipped = 0;
  let totalFailed = 0;

  while (true) {
    // Check remaining messages
    const statsResponse = await fetch('http://localhost:8000/api/whatsapp-listings/stats');
    const statsData = await statsResponse.json();

    if (statsData.data.remaining_count === 0) {
      console.log('✓ All messages processed!');
      break;
    }

    console.log(`📊 Remaining: ${statsData.data.remaining_count} messages`);

    // Process next batch (using named events)
    const batchResult = await new Promise((resolve) => {
      const eventSource = new EventSource(
        'http://localhost:8000/api/whatsapp-listings/extract-all-stream?batch_size=100'
      );

      eventSource.addEventListener('complete', (event) => {
        const data = JSON.parse(event.data);
        eventSource.close();
        resolve(data);
      });

      eventSource.addEventListener('error', () => {
        eventSource.close();
        resolve(null);
      });

      eventSource.onerror = () => {
        eventSource.close();
        resolve(null);
      };
    });

    if (!batchResult) {
      console.error('Batch failed, retrying...');
      await new Promise(r => setTimeout(r, 5000)); // Wait 5s
      continue;
    }

    totalExtracted += batchResult.messages_extracted;
    totalSkipped += batchResult.messages_skipped;
    totalFailed += batchResult.messages_failed;

    console.log(`Batch complete: +${batchResult.messages_extracted} extracted`);

    // Small delay between batches
    await new Promise(r => setTimeout(r, 2000));
  }

  console.log('\n🎉 All Done!');
  console.log(`   Total Extracted: ${totalExtracted}`);
  console.log(`   Total Skipped: ${totalSkipped}`);
  console.log(`   Total Failed: ${totalFailed}`);
}

// Run
processAllMessages();
```

---

## 🔍 **Testing & Debugging**

### **Test with small batch:**
```bash
curl -X POST "http://localhost:8000/api/whatsapp-listings/extract-all-stream?batch_size=5" \
  -H "Accept: text/event-stream" \
  --no-buffer
```

### **Monitor in browser DevTools:**
1. Open browser DevTools (F12)
2. Go to Network tab
3. Filter by "EventStream"
4. Run your streaming code
5. Click on the request to see live events

### **Common Issues:**

**Issue:** Events not appearing
- Check `--no-buffer` flag in curl
- Ensure `Accept: text/event-stream` header is set
- Check for proxy/nginx buffering (add `X-Accel-Buffering: no`)

**Issue:** Connection closes immediately
- Check backend logs for errors
- Verify database view exists (`unprocessed_whatsapp_messages`)
- Check LLM API credentials

---

## 📊 **Performance Tips**

**Batch size recommendations:**
- **Testing:** 5-10 messages
- **Development:** 50-100 messages
- **Production:** 100-200 messages

**Rate limiting:**
The endpoint includes a 2-second delay between messages to avoid overwhelming the LLM API.

**Concurrent processing:**
Run multiple streams in parallel (from different clients) to speed up processing:

```javascript
// Process 500 messages across 5 parallel streams
const streams = [];
for (let i = 0; i < 5; i++) {
  streams.push(startExtraction(100));
}
```

---

## 🔗 **Related Endpoints**

After streaming completes, use these to verify:

```bash
# Check updated stats
GET /api/whatsapp-listings/stats

# View extracted data
GET /api/whatsapp-listings?limit=10&offset=0
```

---

**For complete API documentation, see: [docs/UI_INTEGRATION_GUIDE.md](UI_INTEGRATION_GUIDE.md)**
