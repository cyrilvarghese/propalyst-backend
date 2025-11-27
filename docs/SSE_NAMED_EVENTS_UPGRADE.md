# SSE Named Events Upgrade ✨

We've upgraded the streaming API to use **named SSE events** instead of generic messages. This makes client code **much cleaner and easier to use**.

---

## 🔥 **What Changed?**

### **Before (Generic Messages)**
```
data: {"type": "start", "batch_size": 100}
data: {"type": "progress", "message_id": "...", "status": "completed"}
data: {"type": "complete", "messages_extracted": 85}
```

### **After (Named Events)** ✨
```
event: start
data: {"batch_size": 100}

event: progress
data: {"message_id": "...", "status": "completed"}

event: complete
data: {"messages_extracted": 85}
```

---

## 💡 **Why This Is Better**

### **Before: Manual Type Checking**
```javascript
eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);

  // Have to manually check type for every event
  if (data.type === 'start') {
    // handle start
  } else if (data.type === 'progress') {
    // handle progress
  } else if (data.type === 'complete') {
    // handle complete
  }
};
```

### **After: Clean Event Listeners** ✨
```javascript
// Separate, clean handlers for each event type
eventSource.addEventListener('start', (event) => {
  const data = JSON.parse(event.data);
  // handle start
});

eventSource.addEventListener('progress', (event) => {
  const data = JSON.parse(event.data);
  // handle progress
});

eventSource.addEventListener('complete', (event) => {
  const data = JSON.parse(event.data);
  // handle complete
});
```

---

## ✅ **Benefits**

1. **Cleaner Code**: Separate event listeners instead of one giant switch statement
2. **Standard SSE Practice**: Uses the official SSE specification for named events
3. **Better Type Safety**: TypeScript can infer event types more easily
4. **Easier to Maintain**: Add/remove event handlers without touching other code
5. **No Manual Type Checking**: `data.type` field removed (event name is enough)
6. **More Readable**: Clear separation of concerns

---

## 📝 **Migration Guide**

### **JavaScript/Browser**

**Old Code:**
```javascript
const eventSource = new EventSource(url);

eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);

  switch(data.type) {
    case 'start': console.log('Started'); break;
    case 'progress': console.log('Progress'); break;
    case 'complete': console.log('Done'); break;
  }
};
```

**New Code:**
```javascript
const eventSource = new EventSource(url);

eventSource.addEventListener('start', (e) => {
  const data = JSON.parse(e.data);
  console.log('Started', data);
});

eventSource.addEventListener('progress', (e) => {
  const data = JSON.parse(e.data);
  console.log('Progress', data);
});

eventSource.addEventListener('complete', (e) => {
  const data = JSON.parse(e.data);
  console.log('Done', data);
});
```

---

### **Python (sseclient-py)**

**Old Code:**
```python
for event in client.events():
    data = json.loads(event.data)

    if data['type'] == 'start':
        print('Started')
    elif data['type'] == 'progress':
        print('Progress')
    elif data['type'] == 'complete':
        print('Done')
```

**New Code:**
```python
for event in client.events():
    data = json.loads(event.data)
    event_type = event.event or 'message'

    if event_type == 'start':
        print('Started', data)
    elif event_type == 'progress':
        print('Progress', data)
    elif event_type == 'complete':
        print('Done', data)
```

---

## 🎯 **Event Types**

| Event Name | Purpose | Data Fields |
|------------|---------|-------------|
| `start` | Batch started | `batch_size` |
| `progress` | Message processed | `message_id`, `status`, `progress`, `message_type`, etc. |
| `complete` | Batch finished | `batch_size`, `messages_extracted`, `messages_skipped`, `messages_failed` |
| `error` | Error occurred | `message` |

---

## 🔍 **Example: Full Implementation**

```javascript
function startExtraction(batchSize = 100) {
  const url = `http://localhost:8000/api/whatsapp-listings/extract-all-stream?batch_size=${batchSize}`;
  const eventSource = new EventSource(url);

  // Track stats
  let stats = { extracted: 0, skipped: 0, failed: 0 };

  // Start event
  eventSource.addEventListener('start', (event) => {
    const data = JSON.parse(event.data);
    console.log(`🚀 Starting: ${data.batch_size} messages`);
    updateUI({ status: 'Processing...' });
  });

  // Progress event (fires for each message)
  eventSource.addEventListener('progress', (event) => {
    const data = JSON.parse(event.data);

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

    updateUI(stats);
  });

  // Complete event
  eventSource.addEventListener('complete', (event) => {
    const data = JSON.parse(event.data);
    console.log('🎉 Batch complete!', data);
    eventSource.close();
    showSummary(data);
  });

  // Error event
  eventSource.addEventListener('error', (event) => {
    const data = JSON.parse(event.data);
    console.error('❌ Error:', data.message);
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
const stream = startExtraction(100);

// Stop early if needed
// stream.close();
```

---

## 🚀 **No Breaking Changes for Backend**

The backend now sends:
```python
# Named events
yield f"event: start\ndata: {json.dumps(data)}\n\n"
yield f"event: progress\ndata: {json.dumps(data)}\n\n"
yield f"event: complete\ndata: {json.dumps(data)}\n\n"
```

Instead of:
```python
# Generic messages (old)
yield f"data: {json.dumps({'type': 'start', ...})}\n\n"
```

---

## 📚 **Documentation**

Full examples in:
- [docs/STREAMING_API_EXAMPLES.md](STREAMING_API_EXAMPLES.md) - Complete usage guide
- [docs/UI_INTEGRATION_GUIDE.md](UI_INTEGRATION_GUIDE.md) - API reference

---

## ✨ **Summary**

**Named events = Cleaner code + Standard practice + Better DX**

Instead of checking `if (data.type === 'progress')` in every message, you now have separate, clean event listeners. This is the **standard way** to use Server-Sent Events!
