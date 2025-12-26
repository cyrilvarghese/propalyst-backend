# Questions Configuration Guide

## Overview

The broker agent now uses a **configuration-driven question system**. Instead of hardcoding questions in multiple files, all questions are defined in a single `questions_config.py` file.

**Benefits:**
- ✅ Add new questions by editing ONE file
- ✅ No need to modify graph.py or service.py
- ✅ Consistent question structure
- ✅ Easy to reorder questions
- ✅ Easy to enable/disable questions
- ✅ Centralized documentation

## Architecture

### Files Involved

1. **`broker_agent/questions_config.py`** - Configuration source of truth
2. **`broker_agent/state.py`** - State field definitions + QuestionDefinition model
3. **`broker_agent/nodes/questions.py`** - Question node implementations
4. **`broker_agent/graph.py`** - Automatically routes based on config
5. **`broker_agent/service.py`** - Maps answers to state (can be refactored to use config)

### Question Definition Structure

Each question in `QUESTIONS_CONFIG` is a `QuestionDefinition` with:

```python
QuestionDefinition(
    id="unique_question_id",           # Used internally
    order=1,                            # Sequence in conversation (1-based)
    state_field="state_field_name",     # Single field question
    state_field_min="min_field",        # Range questions: min field name
    state_field_max="max_field",        # Range questions: max field name
    question="Question text?",          # Shown to user
    label="Short Label",                # UI display label
    control_type="radio",               # UI type: radio, range-slider, toggle-group, tags, etc.
    required=True,                      # Must answer?
    control_data={...},                 # UI-specific data (options, ranges, etc.)
    help_text="Help text",              # Optional guidance
    node_fn="ask_bedroom_count",        # Optional: custom node function name
)
```

## How to Add a New Question

### Step 1: Add State Field

Edit `broker_agent/state.py` - Add field to `RealEstateAgentState` TypedDict:

```python
bedroom_count: Optional[int]  # Or whatever type you need
```

Also initialize in `create_real_estate_state()`:

```python
bedroom_count=None,
```

### Step 2: Create Question Node (Optional)

If you need custom logic, create a function in `broker_agent/nodes/questions.py`:

```python
async def ask_bedroom_count(state: RealEstateAgentState) -> RealEstateAgentState:
    """Ask how many bedrooms user wants."""

    # Skip if already answered
    if state.get("bedroom_count"):
        return state

    question = {
        "id": "bedroom_count",
        "question": "How many bedrooms are you looking for?",
        "label": "Bedroom Count",
        "controlType": "radio",
        "required": True,
        "data": {
            "options": [
                {"value": 1, "label": "1 BHK", "icon": "Door"},
                {"value": 2, "label": "2 BHK", "icon": "Doors"},
                # ... more options
            ],
        },
        "helpText": "Select the number of bedrooms you need",
    }

    return {
        **state,
        "current_question": question,
        "current_question_id": "bedroom_count",
        "conversational_message": question["question"],
        "completed": False,
    }
```

Export it in `broker_agent/nodes/__init__.py`:

```python
from .questions import (
    # ... other imports ...
    ask_bedroom_count,
)

__all__ = [
    # ... other exports ...
    "ask_bedroom_count",
]
```

### Step 3: Add Question to Configuration

Edit `broker_agent/questions_config.py` - Add to `QUESTIONS_CONFIG` list:

```python
QuestionDefinition(
    id="bedroom_count",
    order=5,                           # Position in flow
    state_field="bedroom_count",       # Maps to state field
    question="How many bedrooms are you looking for?",
    label="Bedroom Count",
    control_type="radio",
    required=True,
    control_data={
        "options": [
            {"value": 1, "label": "1 BHK", "icon": "Door"},
            {"value": 2, "label": "2 BHK", "icon": "Doors"},
            # ... etc
        ],
    },
    help_text="Select the number of bedrooms you need",
    node_fn="ask_bedroom_count",       # Function name from Step 2
),
```

**That's it!** The system will automatically:
- ✅ Route to this question when bedroom_count is empty
- ✅ Show it in the correct order
- ✅ Generate the UI from control_data
- ✅ Map the answer to state field

### Step 4: Update Service Layer (Optional)

If you need special handling in `broker_agent/service.py`, add mapping logic. See below for details.

---

## Configuration Details

### control_type Options

| Type | Used For | Example |
|------|----------|---------|
| `radio` | Single choice | Buy/Sell, Bedroom count |
| `toggle-group` | Multiple choice buttons | Property type |
| `range-slider` | Min/Max selection | Budget, Area |
| `location-proximity` | Location-based selection | Proximity preferences |
| `tags` | Multiple text inputs | Special features |
| `text` | Free text input | Custom preferences |
| `checkbox` | Multiple selections | Amenities |

### control_data Structure

Depends on `control_type`:

**Radio Options:**
```python
control_data={
    "options": [
        {"value": "buy", "label": "Buy", "icon": "ShoppingCart"},
        {"value": "sell", "label": "Sell", "icon": "Tag"},
    ],
}
```

**Range Slider:**
```python
control_data={
    "min": 0.5,
    "max": 5,
    "step": 0.1,
    "unit": "Cr",
    "defaultValue": [1.2, 2.5],
    "histogram": [...]  # Optional market data
}
```

**Toggle Group:**
```python
control_data={
    "options": [
        {"value": "apartment", "label": "Apartment", "icon": "Building"},
        {"value": "villa", "label": "Villa", "icon": "Castle"},
    ],
}
```

---

## How the Router Works (Simplified)

The router in `graph.py` is now configuration-driven:

```python
for question in get_all_questions():  # Iterates in order
    # Check if state field is populated
    if state field is empty and question not asked:
        # Ask this question
        return ask_question()

# All answered
return mark_complete()
```

**No hardcoded if/elif chains!**

---

## Range Questions (Min/Max)

For questions with min and max (budget, area):

```python
QuestionDefinition(
    id="budget",
    state_field_min="price_min",       # NOT state_field
    state_field_max="price_max",       # BOTH min and max
    question="What's your budget?",
    control_type="range-slider",
    # ...
)
```

The router checks:
```python
if not state["price_min"] or not state["price_max"]:
    ask_budget()
```

---

## Reordering Questions

Simply change the `order` field in `QUESTIONS_CONFIG`:

```python
QuestionDefinition(
    id="bedroom_count",
    order=3,  # Was 5, now 3 - move it earlier
    # ...
)
```

The router automatically uses the new order!

---

## Making Questions Optional

Set `required=False`:

```python
QuestionDefinition(
    # ...
    required=False,
)
```

Users can skip if they don't want to answer.

**Note:** The router still asks these questions. To truly skip, either:
1. Remove from config entirely, OR
2. Refactor router logic (not recommended - keep simple)

---

## Querying Question Configuration

In code, use helpers from `questions_config.py`:

```python
from broker_agent.questions_config import (
    get_question_by_id,              # Find by ID
    get_all_questions,               # Get all in order
    get_question_ids_sorted,         # Just IDs
    get_state_fields_for_question,   # Get state field(s)
)

# Example: Get the next question
question = get_question_by_id("bedroom_count")
if question:
    print(f"Question {question.order}: {question.question}")

# Example: Check all required questions
for q in get_all_questions():
    if q.required:
        print(f"Required: {q.label}")
```

---

## Service Layer Integration

The `broker_agent/service.py` currently has hardcoded field mapping. To make it configuration-driven:

### Current Approach (Hardcoded)

```python
# broker_agent/service.py
if question_id == "req_type":
    state["req_type"] = answer
elif question_id == "proximity_location":
    state["proximity_location"] = answer
elif question_id == "budget":
    state["price_min"], state["price_max"] = answer
# ... etc (hardcoded for each question)
```

### Refactored Approach (Configuration-Driven)

```python
from broker_agent.questions_config import get_question_by_id

async def process_answer(state, question_id, answer):
    """Universal answer processor using config."""
    question = get_question_by_id(question_id)
    if not question:
        raise ValueError(f"Unknown question: {question_id}")

    # Handle range questions (min/max)
    if question.state_field_min and question.state_field_max:
        state[question.state_field_min] = answer[0]
        state[question.state_field_max] = answer[1]
    else:
        # Single field
        state[question.state_field] = answer

    return state
```

This eliminates hardcoded mapping!

---

## Example: Adding "Parking Spaces" Question

### File 1: `broker_agent/state.py`

Add field:
```python
parking_spaces: Optional[int]
```

Initialize:
```python
parking_spaces=None,
```

### File 2: `broker_agent/nodes/questions.py`

Add function:
```python
async def ask_parking_spaces(state: RealEstateAgentState) -> RealEstateAgentState:
    if state.get("parking_spaces") is not None:
        return state

    question = {
        "id": "parking_spaces",
        "question": "How many parking spaces do you need?",
        "label": "Parking Spaces",
        "controlType": "radio",
        "required": False,
        "data": {
            "options": [
                {"value": 0, "label": "No parking"},
                {"value": 1, "label": "1 space"},
                {"value": 2, "label": "2 spaces"},
                {"value": 3, "label": "3+ spaces"},
            ],
        },
        "helpText": "Select number of parking spaces needed",
    }

    return {
        **state,
        "current_question": question,
        "current_question_id": "parking_spaces",
        "conversational_message": question["question"],
        "completed": False,
    }
```

Export in `broker_agent/nodes/__init__.py`.

### File 3: `broker_agent/questions_config.py`

Add to `QUESTIONS_CONFIG`:
```python
QuestionDefinition(
    id="parking_spaces",
    order=6,  # After bedroom, before property type
    state_field="parking_spaces",
    question="How many parking spaces do you need?",
    label="Parking Spaces",
    control_type="radio",
    required=False,
    control_data={
        "options": [
            {"value": 0, "label": "No parking"},
            {"value": 1, "label": "1 space"},
            {"value": 2, "label": "2 spaces"},
            {"value": 3, "label": "3+ spaces"},
        ],
    },
    help_text="Select number of parking spaces needed",
    node_fn="ask_parking_spaces",
),
```

**Done!** The system automatically:
- Routes to parking spaces question
- Shows it in position 6
- Generates UI from control_data
- Maps answer to state
- Continues to next question

---

## Troubleshooting

### Question not showing up?

1. Check `order` field - is it unique?
2. Check state field name - does it exist in RealEstateAgentState?
3. Check `node_fn` - does the function exist and is it exported?
4. Check `control_type` - is it supported by frontend?

### Router skipping questions?

The router checks `state[field] is not None`. Make sure:
1. State field is properly initialized (not missing)
2. Previous question actually populated it
3. Try clearing session state and retrying

### Custom logic not running?

1. Make sure `node_fn="function_name"` matches import
2. Check `broker_agent/nodes/__init__.py` has the export
3. Verify async function signature: `async def name(state) -> RealEstateAgentState`

---

## Summary

**Before (Hardcoded):**
```
Add question → Edit state.py → Edit questions.py → Edit graph.py → Edit service.py
(5 files, error-prone)
```

**After (Configuration-Driven):**
```
Add question → Edit questions_config.py (mostly, optionally state.py and questions.py)
(1-2 files, much simpler!)
```

The system is now extensible and maintainable. Enjoy! 🚀
