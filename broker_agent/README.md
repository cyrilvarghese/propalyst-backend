# Real Estate Agent

A LangChain-based conversational agent that helps users find their perfect property.

## Overview

The agent conducts a guided conversation with users to understand their property requirements:

1. **Transaction Type**: Buy or Sell
2. **Location**: Preferred area/locality
3. **Price Range**: Budget in lakhs
4. **Property Area**: Size in sq ft
5. **Property Type**: Apartment, House, Villa, etc.
6. **Special Features**: Preferences like gym, pool, parking, etc.

## Architecture

### Folder Structure

```
broker_agent/
├── __init__.py              # Package exports
├── state.py                 # State definitions (Pydantic models + TypedDict)
├── graph.py                 # LangGraph workflow
├── service.py               # Business logic layer
├── router.py                # FastAPI routes
├── nodes/
│   ├── __init__.py
│   ├── questions.py         # Question node functions
│   └── completion.py        # Conversation completion
└── README.md                # This file
```

### Key Components

#### State (state.py)

- **RealEstateAgentState**: TypedDict that flows through the graph
- **ConversationalQuestion**: Pydantic model for UI components
- **PropertyPreference**: Single preference model
- Helper function: `create_real_estate_state()`

#### Graph (graph.py)

- **route_real_estate_agent()**: Router function that decides which question to ask
- **create_real_estate_agent_graph()**: Creates and compiles the LangGraph workflow

Flow:
```
START
  ↓
[ROUTER] → checks what's missing
  ↓
[Q1, Q2, Q3, Q4, Q5, Q6] → one node per request
  ↓
[MARK COMPLETE]
  ↓
END
```

#### Service (service.py)

- **RealEstateAgentService**: Business logic layer
  - `create_session()`: Generate unique session ID
  - `process_user_input()`: Update state with answer and get next question
  - `get_next_question()`: Get next question without processing input
  - `get_user_summary()`: Extract user preferences

#### API Router (router.py)

FastAPI routes for HTTP endpoints:

```
POST   /api/broker_agent/sessions
GET    /api/broker_agent/sessions/{session_id}
POST   /api/broker_agent/sessions/{session_id}/answer
GET    /api/broker_agent/sessions/{session_id}/summary
```

## Usage

### Python API (Async)

```python
from broker_agent.service import RealEstateAgentService

# Create session
session_id = RealEstateAgentService.create_session()
state = RealEstateAgentService.create_initial_state(session_id)

# Get first question
state = await RealEstateAgentService.get_next_question(state)
print(state["current_question"])
# Output: {
#     "id": "transaction_type",
#     "question": "Are you looking to buy or sell a property?",
#     "controlType": "radio",
#     ...
# }

# Process user answer
state = await RealEstateAgentService.process_user_input(
    state, "buy", "transaction_type"
)

# Continue conversation
state = await RealEstateAgentService.process_user_input(
    state, "Indiranagar", "location"
)

state = await RealEstateAgentService.process_user_input(
    state, {"min": 50.0, "max": 100.0}, "price_range"
)

# Get summary
summary = RealEstateAgentService.get_user_summary(state)
print(summary)
# Output: {
#     "transaction_type": "buy",
#     "location": "Indiranagar",
#     "price_range": {"min": 50.0, "max": 100.0},
#     "area_range": {"min": None, "max": None},
#     "property_type": None,
#     "special_features": []
# }
```

### HTTP API

#### 1. Create Session

```bash
curl -X POST http://localhost:8000/api/broker_agent/sessions \
  -H "Content-Type: application/json" \
  -d '{}'
```

Response:
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "Welcome to the Real Estate Agent! Let's find your perfect property."
}
```

#### 2. Get Current Question

```bash
curl http://localhost:8000/api/broker_agent/sessions/550e8400-e29b-41d4-a716-446655440000
```

Response:
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "current_question": {
    "id": "transaction_type",
    "question": "Are you looking to buy or sell a property?",
    "label": "Transaction Type",
    "controlType": "radio",
    "required": true,
    "data": {
      "options": [
        {"value": "buy", "label": "Buy", "icon": "ShoppingCart"},
        {"value": "sell", "label": "Sell", "icon": "Tag"}
      ]
    },
    "helpText": "Select whether you want to buy or sell a property"
  },
  "message": "Are you looking to buy or sell a property?",
  "completed": false,
  "user_summary": {
    "transaction_type": null,
    "location": null,
    "price_range": {"min": null, "max": null},
    "area_range": {"min": null, "max": null},
    "property_type": null,
    "special_features": []
  },
  "messages": []
}
```

#### 3. Submit Answer

```bash
curl -X POST http://localhost:8000/api/broker_agent/sessions/550e8400-e29b-41d4-a716-446655440000/answer \
  -H "Content-Type: application/json" \
  -d '{"answer": "buy", "question_id": "transaction_type"}'
```

Response:
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "current_question": {
    "id": "location",
    "question": "Which area or locality are you interested in?",
    "controlType": "autocomplete",
    ...
  },
  "message": "Which area or locality are you interested in?",
  "completed": false,
  "user_summary": {
    "transaction_type": "buy",
    "location": null,
    ...
  },
  "messages": [
    {"role": "user", "content": "buy"},
    {"role": "agent", "content": "Which area or locality are you interested in?"}
  ]
}
```

#### 4. Get User Summary

```bash
curl http://localhost:8000/api/broker_agent/sessions/550e8400-e29b-41d4-a716-446655440000/summary
```

Response:
```json
{
  "transaction_type": "buy",
  "location": "Indiranagar",
  "price_range": {
    "min": 50.0,
    "max": 100.0
  },
  "area_range": {
    "min": 1000,
    "max": 2500
  },
  "property_type": "apartment",
  "special_features": ["gym", "pool", "parking"]
}
```

## Integration

### Add to FastAPI App

```python
from fastapi import FastAPI
from broker_agent import router

app = FastAPI()
app.include_router(router)

# Now available at /api/broker_agent/*
```

## State Flow

### Example: User Journey

```
Request 1: POST /sessions
↓
Create session, get first question (transaction_type)

Request 2: POST /sessions/{id}/answer
Input: {"answer": "buy", "question_id": "transaction_type"}
↓
Update state[transaction_type] = "buy"
Router runs → detects location is missing
↓
Return Q2 (location)

Request 3: POST /sessions/{id}/answer
Input: {"answer": "Indiranagar", "question_id": "location"}
↓
Update state[location] = "Indiranagar"
Router runs → detects price_range is missing
↓
Return Q3 (price_range)

... continue until all questions answered ...

Final Request: All fields filled
↓
Router runs → all questions complete
↓
Return completion message with summary
```

## Question Types and Data Formats

### Q1: Transaction Type
- **Control**: Radio buttons
- **Input**: "buy" or "sell"

### Q2: Location
- **Control**: Autocomplete dropdown
- **Input**: String (area name)
- **Examples**: "Indiranagar", "Koramangala", "Whitefield"

### Q3: Price Range
- **Control**: Range slider (dual)
- **Input**: `{"min": 50.0, "max": 100.0}` (in lakhs)

### Q4: Property Area
- **Control**: Range slider (dual)
- **Input**: `{"min": 1000, "max": 2500}` (in sq ft)

### Q5: Property Type
- **Control**: Toggle group
- **Input**: "apartment" | "house" | "villa" | "penthouse" | "townhouse" | "plot"

### Q6: Special Features
- **Control**: Checkbox group (multi-select)
- **Input**: `["gym", "pool", "parking"]`
- **Options**: gym, pool, parking, garden, security, lift, playground, study_room, balcony, pet_friendly, north_facing, power_backup, water_harvesting, solar_panels

## Customization

### Add New Question

1. Create node function in `nodes/questions.py`:

```python
async def ask_custom_question(state: RealEstateAgentState) -> RealEstateAgentState:
    if state.get("custom_field"):
        return state

    question = {
        "id": "custom_field",
        "question": "Your question here?",
        "controlType": "text",
        ...
    }

    return {
        **state,
        "current_question": question,
        "current_question_id": "custom_field",
        "conversational_message": question["question"],
    }
```

2. Update `graph.py` router:

```python
if not state.get("custom_field"):
    return "ask_custom_question"
```

3. Add node to graph:

```python
workflow.add_node("ask_custom_question", ask_custom_question)
workflow.add_edge("ask_custom_question", END)
```

4. Update router mapping in `set_conditional_entry_point()`

### Change Question Order

Edit the `route_real_estate_agent()` function in `graph.py` to check fields in desired order.

### Customize Welcome Message

Edit the welcome message in `router.py`:

```python
message="Your custom welcome message here!"
```

## Best Practices

1. **Session Management**: In production, use a database (PostgreSQL, Redis) instead of in-memory `_sessions` dict
2. **State Persistence**: Save/load state from database between requests
3. **Error Handling**: Add validation for user inputs
4. **Logging**: Monitor conversation flows and user patterns
5. **Testing**: Add unit tests for service layer

## Debugging

Enable debug logging:

```python
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("broker_agent")
```

## Performance Notes

- Graph is cached after first creation (class variable `_graph`)
- State flows through graph without recompilation
- Each request handles exactly ONE question
- No infinite loops (explicit edge to END)

## Files

| File | Purpose |
|------|---------|
| `state.py` | State definitions and models |
| `graph.py` | LangGraph workflow and routing |
| `service.py` | Business logic layer |
| `router.py` | FastAPI HTTP endpoints |
| `nodes/questions.py` | Question node functions |
| `nodes/completion.py` | Conversation completion |
