# Interactive Demo Scripts - Guide

Two interactive scripts that show JSON responses from the broker agent at each step.

## Quick Start

### Option 1: Service Layer Demo (No API Server Needed)

```bash
python interactive_broker_agent_demo.py
```

This runs the service layer directly and shows all JSON responses.

**Pros:**
- No server needed
- Fastest execution
- Shows internal state transitions
- Synchronous output

**Output:** Shows JSON at each step

### Option 2: HTTP API Demo (Requires Server)

```bash
# Terminal 1: Start FastAPI server
uvicorn main:app --reload

# Terminal 2: Run the demo
python interactive_api_demo.py
```

This tests the actual HTTP API endpoints.

**Pros:**
- Tests real HTTP layer
- Shows request/response cycle
- Tests all 4 endpoints
- Production-like testing

**Output:** Shows HTTP requests and JSON responses

---

## Script Details

### interactive_broker_agent_demo.py

Tests the service layer directly. Shows all state transitions and JSON responses.

**Features:**
- ✅ No external dependencies needed
- ✅ Instant results
- ✅ Shows internal state
- ✅ 10 detailed steps
- ✅ Complete JSON output

**Run:**
```bash
python interactive_broker_agent_demo.py
```

**Output Example:**
```
================================================================================
  REAL ESTATE AGENT - INTERACTIVE API DEMO
================================================================================

📍 STEP 1: Creating a new session...
────────────────────────────────────────────────────────────────────────────────
✅ Session created: 550e8400-e29b-41d4-a716-446655440000

📋 Initial State:
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "current_question_id": null,
  "transaction_type": null,
  "location": null,
  ...
}

================================================================================
  STEP 2: Getting first question
================================================================================

📋 Current Question:
{
  "id": "transaction_type",
  "question": "Are you looking to buy or sell a property?",
  "label": "Transaction Type",
  "controlType": "radio",
  ...
}

💬 Agent: Are you looking to buy or sell a property?

📋 State After Getting Question:
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "current_question_id": "transaction_type",
  ...
}

...

================================================================================
  ✅ CONVERSATION COMPLETED
================================================================================

📋 Completion Summary:
{
  "status": "completed",
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "completed": true,
  "total_questions_answered": 6,
  "user_preferences": {...},
  "conversation_length": 12
}

================================================================================
```

### interactive_api_demo.py

Tests the HTTP API. Shows request/response for each endpoint.

**Requirements:**
```bash
pip install httpx
```

**Features:**
- ✅ Tests all 4 endpoints
- ✅ Shows HTTP requests
- ✅ Shows HTTP responses
- ✅ 10 API calls
- ✅ Production testing

**Setup:**

1. Start FastAPI server:
```bash
# Add to main.py:
from broker_agent import router
app.include_router(router)

# Then run:
uvicorn main:app --reload
```

2. Run the demo:
```bash
python interactive_api_demo.py
```

**Output Example:**
```
================================================================================
  REAL ESTATE AGENT - INTERACTIVE HTTP API DEMO
================================================================================

📍 STEP 1: Creating a new session...
────────────────────────────────────────────────────────────────────────────────

📤 Request:
   POST /sessions
   Body: {}

📥 Response:
   Status: 200

📋 Response JSON:
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "Welcome to the Real Estate Agent! Let's find your perfect property."
}

✅ Session created: 550e8400-e29b-41d4-a716-446655440000

================================================================================
  STEP 2: Getting current question
================================================================================

📤 Request:
   GET /sessions/550e8400-e29b-41d4-a716-446655440000

📥 Response:
   Status: 200

📋 Response JSON:
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "current_question": {
    "id": "transaction_type",
    "question": "Are you looking to buy or sell a property?",
    ...
  },
  "message": "Are you looking to buy or sell a property?",
  "completed": false,
  "user_summary": {...},
  "messages": []
}

💬 Agent: Are you looking to buy or sell a property?

================================================================================
  STEP 3: Answer Q1 - Transaction Type
================================================================================

📤 Request:
   POST /sessions/550e8400-e29b-41d4-a716-446655440000/answer
   Body: {"answer": "buy", "question_id": "transaction_type"}

👤 User answers: buy

📥 Response:
   Status: 200

📋 Response JSON:
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "current_question": {
    "id": "location",
    "question": "Which area or locality are you interested in?",
    ...
  },
  "message": "Which area or locality are you interested in?",
  "completed": false,
  "user_summary": {
    "transaction_type": "buy",
    ...
  },
  "messages": [
    {"role": "user", "content": "buy"},
    {"role": "agent", "content": "Which area or locality are you interested in?"}
  ]
}

💬 Agent: Which area or locality are you interested in?

📋 User Summary So Far:
{
  "transaction_type": "buy",
  "location": null,
  "price_range": {"min": null, "max": null},
  ...
}

...

================================================================================
  ✅ HTTP API DEMO COMPLETED
================================================================================

📋 Completion Info:
{
  "status": "success",
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "base_url": "http://localhost:8000/api/broker_agent",
  "endpoints_tested": [
    "POST /sessions",
    "GET /sessions/{id}",
    "POST /sessions/{id}/answer",
    "GET /sessions/{id}/summary"
  ],
  "total_requests": 10
}

📝 Available Endpoints:
   POST   http://localhost:8000/api/broker_agent/sessions
   GET    http://localhost:8000/api/broker_agent/sessions/{session_id}
   POST   http://localhost:8000/api/broker_agent/sessions/{session_id}/answer
   GET    http://localhost:8000/api/broker_agent/sessions/{session_id}/summary

================================================================================
  ✅ ALL ENDPOINTS TESTED SUCCESSFULLY
================================================================================
```

---

## Comparison

| Feature | Service Demo | HTTP Demo |
|---------|--------------|-----------|
| **Requires Server** | ❌ No | ✅ Yes |
| **Setup Time** | 0 minutes | 2 minutes |
| **Execution Time** | < 1 second | 1-2 seconds |
| **Shows Internal State** | ✅ Yes | ❌ No |
| **Tests HTTP Layer** | ❌ No | ✅ Yes |
| **Shows Requests** | ❌ No | ✅ Yes |
| **Production Testing** | ❌ No | ✅ Yes |
| **Dependencies** | Default | httpx |

---

## Step-by-Step Walkthrough

Both demos follow the same 10-step conversation:

### Step 1: Create Session
- Creates new conversation session
- Gets unique session ID
- Shows initial state

### Step 2: Get First Question
- Fetches first question (transaction type)
- Shows question structure
- Shows agent message

### Steps 3-8: Answer Questions
For each question (Q1-Q6):
- Shows user answer
- Shows next question
- Updates user summary
- Shows conversation messages

### Step 9: Get Final Summary
- Shows complete user preferences
- All 6 answers collected

### Step 10: Completion
- Shows completion status
- Summary of conversation
- Available endpoints

---

## Common Scenarios

### Running Service Demo

```bash
python interactive_broker_agent_demo.py
```

Output shows ~3000+ lines of JSON with 10 sections.

### Running HTTP Demo with Server

**Terminal 1:**
```bash
# First, add to main.py (if not already done):
# from broker_agent import router
# app.include_router(router)

uvicorn main:app --reload
```

**Terminal 2:**
```bash
python interactive_api_demo.py
```

Output shows HTTP requests/responses with JSON.

### Testing Specific Endpoint

If you want to test manually:

```bash
# Create session
curl -X POST http://localhost:8000/api/broker_agent/sessions \
  -H "Content-Type: application/json" \
  -d '{}'

# Get question (use session_id from above)
curl http://localhost:8000/api/broker_agent/sessions/{session_id}

# Submit answer
curl -X POST http://localhost:8000/api/broker_agent/sessions/{session_id}/answer \
  -H "Content-Type: application/json" \
  -d '{"answer": "buy", "question_id": "transaction_type"}'
```

---

## Output Formats

### Service Demo Output

```
================================================================================
  STEP X: Description
================================================================================

📍 Setup info
📤 Request details
📥 Response details
📋 JSON data
💬 Agent message
👤 User input

📋 State/Summary labels with formatted JSON
```

### HTTP Demo Output

```
📤 Request:
   METHOD /endpoint
   Body: {...}

📥 Response:
   Status: 200

📋 Response JSON:
{
  ...
}
```

---

## Troubleshooting

### "ModuleNotFoundError: No module named 'broker_agent'"

```bash
cd /home/propalyst/propalyst-backend
python interactive_broker_agent_demo.py
```

### "Connection refused" (for HTTP demo)

Make sure FastAPI server is running:
```bash
# Terminal 1
uvicorn main:app --reload

# Terminal 2
python interactive_api_demo.py
```

### "ModuleNotFoundError: No module named 'httpx'" (for HTTP demo)

```bash
pip install httpx
```

---

## Integration with Main App

To use the HTTP demo with your main.py:

```python
# main.py
from fastapi import FastAPI
from broker_agent import router  # Add this

app = FastAPI()

# Include the broker agent router
app.include_router(router)  # Add this

# Your existing routes...
```

Then run:
```bash
uvicorn main:app --reload
```

---

## Example Conversations

### Conversation 1: Buying Apartment
- Transaction: **buy**
- Location: **Indiranagar**
- Price: **50-100 lakhs**
- Area: **1000-2500 sq ft**
- Type: **apartment**
- Features: **gym, pool, parking, security**

### Conversation 2: Selling Villa
- Transaction: **sell**
- Location: **Whitefield**
- Price: **100-200 lakhs**
- Area: **2000-4000 sq ft**
- Type: **villa**
- Features: **garden, north_facing, solar_panels**

---

## Next Steps

1. **Run Service Demo:**
   ```bash
   python interactive_broker_agent_demo.py
   ```

2. **Set up API Server:**
   ```bash
   # Add to main.py
   from broker_agent import router
   app.include_router(router)

   # Run
   uvicorn main:app --reload
   ```

3. **Run HTTP Demo:**
   ```bash
   python interactive_api_demo.py
   ```

4. **Build Frontend:**
   - Use JSON responses as reference
   - See BROKER_AGENT_INTEGRATION.md for React example

5. **Deploy:**
   - Configure database persistence
   - Set up production environment
   - Monitor conversations

---

## Support

See:
- `BROKER_AGENT_SETUP.md` - Quick start
- `BROKER_AGENT_INTEGRATION.md` - Integration examples
- `broker_agent/README.md` - Full documentation
- `TEST_GUIDE.md` - Testing guide
