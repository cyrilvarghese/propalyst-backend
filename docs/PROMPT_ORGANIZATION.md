# Prompt Organization - Centralized Prompt Management

## Overview
All LLM prompts have been extracted to separate files in `providers/scrapers/prompts/` for better organization, maintainability, and reusability.

## Prompt Files Structure

```
providers/scrapers/prompts/
├── schema_generation_prompt.txt           # SquareYards schema generation
├── magicbricks_schema_generation_prompt.txt # MagicBricks schema generation
└── relevance_scoring_prompt.txt           # Property relevance scoring
```

## Prompts

### 1. Schema Generation Prompts

**Purpose:** Guide LLMs to generate CSS/XPath extraction schemas for web scraping

#### SquareYards (`schema_generation_prompt.txt`)
- **Used by:** `providers/scrapers/squareyards_scraper.py`
- **Task:** Generate CSS selectors for extracting property data from SquareYards
- **Key instruction:** "Look for icons to identify fields"
- **Example:** Icon `.icon-beds` indicates bedrooms field

#### MagicBricks (`magicbricks_schema_generation_prompt.txt`)
- **Used by:** `providers/scrapers/magicbricks_scraper.py`
- **Task:** Generate CSS/XPath selectors for extracting property data from MagicBricks
- **Key instruction:** "Look for label text and create attribute selectors based on label value"
- **Example:** Find label "Parking" to extract parking value

### 2. Relevance Scoring Prompt

**File:** `relevance_scoring_prompt.txt`

**Purpose:** Guide LLM to score property relevance against user queries

**Used by:** `services/relevance_scoring_service.py`

**Template Variables:**
- `{user_query}` - The user's search query
- `{property_summary}` - JSON-formatted property details

**Scoring Criteria:**
- Bedrooms/BHK matching
- Area/size matching (±20% tolerance)
- Facing direction
- Parking availability
- Price range
- Location
- Furnishing type
- Property type

**Output:** JSON with `relevance_score` (1-10) and `relevance_reason`

## How It Works

### Schema Generation Flow

```
1. Scraper initializes
2. Check if schema file exists
   - Yes: Load schema from file
   - No: Continue to generation
3. Load sample HTML from file
4. Load prompt template from providers/scrapers/prompts/*.txt
5. Call LLM with (prompt + sample HTML)
6. LLM generates extraction schema
7. Save schema to file
8. Use schema for subsequent scrapes
```

### Relevance Scoring Flow

```
1. Service initializes
2. Load prompt template from relevance_scoring_prompt.txt
3. For each property:
   - Create property summary
   - Format prompt template with {user_query} and {property_summary}
   - Call LLM with formatted prompt
   - Parse JSON response
   - Add score and reason to property
```

## Advantages

✅ **Separation of Concerns:** Prompts are separate from code logic
✅ **Easy Maintenance:** Edit prompts without touching code
✅ **Consistency:** All LLM interactions follow same pattern
✅ **Reusability:** Prompts can be shared or versioned
✅ **Readability:** Code is cleaner without embedded strings
✅ **Documentation:** Prompts are self-documenting

## Template Variables

### In Prompts

Prompts use Python f-string style variables wrapped in curly braces:

```
{user_query}        # Replaced with actual user query
{property_summary}  # Replaced with JSON-formatted property data
```

### Loading and Formatting

```python
# Load template
with open(PROMPT_PATH, 'r') as f:
    template = f.read()

# Format with data
prompt = template.format(
    user_query=user_query,
    property_summary=json.dumps(property_summary, indent=2)
)
```

## Adding New Prompts

To add a new LLM prompt:

1. **Create the prompt file** in `providers/scrapers/prompts/`
   ```
   providers/scrapers/prompts/my_new_prompt.txt
   ```

2. **Define template variables** using `{variable_name}` syntax

3. **Update the service/scraper** to:
   - Import `Path` from `pathlib`
   - Define `PROMPT_PATH` constant
   - Load prompt in `__init__()`
   - Format prompt with data when calling LLM

Example:
```python
from pathlib import Path

PROMPT_PATH = Path(__file__).parent / "prompts" / "my_prompt.txt"

def __init__(self):
    with open(self.PROMPT_PATH, 'r') as f:
        self.prompt_template = f.read()

def use_prompt(self, query):
    prompt = self.prompt_template.format(query=query)
    # Call LLM with prompt
```

## Files Modified

- ✅ Created: `providers/scrapers/prompts/relevance_scoring_prompt.txt`
- ✅ Updated: `services/relevance_scoring_service.py` (loads from prompt file)
- ✅ Existing: `providers/scrapers/prompts/schema_generation_prompt.txt`
- ✅ Existing: `providers/scrapers/prompts/magicbricks_schema_generation_prompt.txt`

## Benefits Summary

| Aspect | Before | After |
|--------|--------|-------|
| Prompt Location | Embedded in code | Separate `.txt` files |
| Code Length | Long f-strings | Clean and concise |
| Maintenance | Edit code to change prompt | Edit text file directly |
| Reusability | Only within service | Can be referenced anywhere |
| Documentation | Hidden in code | Visible and organized |
| Versioning | With code changes | Can version separately |
