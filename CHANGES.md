# Changes Log - Lead Extraction and Management API

**Date**: December 13, 2025
**Feature**: Lead Extraction and Criteria Detection System
**Scope**: New API for extracting detailed property search criteria and user journey information

---

## Summary of Changes

### New Files (5 total)

| File | Type | Purpose | Size |
|------|------|---------|------|
| `models/lead.py` | Python | Pydantic data models | 4.4 KB |
| `services/lead_extraction_service.py` | Python | Business logic | 13 KB |
| `routers/lead_router.py` | Python | FastAPI endpoints | 4.3 KB |
| `prompts/lead_criteria_extraction.txt` | Text | LLM prompt template | 2.7 KB |
| `data/leads.json` | JSON | Lead storage | 3 bytes |

### Modified Files (2 total)

| File | Changes | Lines Affected |
|------|---------|-----------------|
| `main.py` | Added router import & registration | 46, 98 |
| `routers/__init__.py` | Added router export | 19, 33 |

---

## Detailed Changes

### 1. New File: `models/lead.py`

**Location**: `/home/propalyst/propalyst-backend/models/lead.py`

**Content Summary**:
- 10 Pydantic models for request/response validation
- ~160 lines of code
- Follows existing `models/search.py` pattern

**Classes Added**:
```python
class PropertyCriteria(BaseModel)           # 8 property fields
class ProximityPreferences(BaseModel)       # 4 boolean fields
class UserJourney(BaseModel)                # 3 timeline fields
class DetailedCriteria(BaseModel)           # Nested container
class NearbyLocality(BaseModel)             # Location + distance
class ExtractDetailedCriteriaRequest(BaseModel)
class ExtractDetailedCriteriaResponse(BaseModel)
class CreateLeadRequest(BaseModel)
class CreateLeadResponse(BaseModel)
```

---

### 2. New File: `services/lead_extraction_service.py`

**Location**: `/home/propalyst/propalyst-backend/services/lead_extraction_service.py`

**Content Summary**:
- Single service class: `LeadExtractionService`
- ~330 lines of code
- Follows existing `services/shortlist_service.py` pattern

**Public Methods**:
```python
async def extract_detailed_criteria(query: str) -> Dict[str, Any]
async def find_nearby_localities(location: str, limit: int = 5) -> Dict[str, Any]
async def create_lead(query: str) -> Dict[str, Any]
```

**Private Methods**:
```python
def _load_prompt() -> str                           # With caching
def _get_gemini_client() -> genai.Client            # Singleton
def _detect_missing_criteria(criteria) -> List[str]
def _ensure_data_directory() -> None
def _load_leads() -> List[Dict[str, Any]]
def _save_leads(leads: List[Dict]) -> None
```

---

### 3. New File: `routers/lead_router.py`

**Location**: `/home/propalyst/propalyst-backend/routers/lead_router.py`

**Content Summary**:
- FastAPI router with 2 endpoints
- ~140 lines of code
- Follows existing `routers/search_router.py` pattern

**Endpoints**:
```python
@router.post("/extract-detailed-criteria")
async def extract_detailed_criteria(request: ExtractDetailedCriteriaRequest)

@router.post("/leads/create")
async def create_lead(request: CreateLeadRequest)
```

---

### 4. New File: `prompts/lead_criteria_extraction.txt`

**Location**: `/home/propalyst/propalyst-backend/prompts/lead_criteria_extraction.txt`

**Content Summary**:
- LLM prompt template for Gemini
- ~55 lines
- External prompt file (per CLAUDE.md best practices)

**Sections**:
- Property Criteria extraction (8 fields)
- Proximity Preferences (4 booleans)
- User Journey (3 fields)
- Inference rules
- JSON output format

---

### 5. New File: `data/leads.json`

**Location**: `/home/propalyst/propalyst-backend/data/leads.json`

**Content Summary**:
- JSON array for lead persistence
- Initially empty: `[]`
- Auto-populated by service

**Format**:
```json
[
  {
    "id": "uuid",
    "query": "original query",
    "extracted_criteria": {...},
    "matched_properties": [...],
    "nearby_localities": [...],
    "created_at": "ISO timestamp"
  }
]
```

---

### 6. Modified File: `main.py`

**Location**: `/home/propalyst/propalyst-backend/main.py`

**Changes**:

#### Change 1: Import statement (Line 46)
```python
# ADDED:
from routers.lead_router import router as lead_router
```

#### Change 2: Router registration (Line 98)
```python
# ADDED after matching_supply_router:
app.include_router(lead_router)
```

**Impact**: Registers the new lead management API with the FastAPI application

---

### 7. Modified File: `routers/__init__.py`

**Location**: `/home/propalyst/propalyst-backend/routers/__init__.py`

**Changes**:

#### Change 1: Import statement (Line 19)
```python
# ADDED:
from .lead_router import router as lead_router
```

#### Change 2: __all__ export (Line 33)
```python
# ADDED to __all__ list:
"lead_router"
```

**Impact**: Makes lead_router available for import from the routers package

---

## API Changes

### New Endpoints

**Endpoint 1**: Extract Detailed Criteria
```
Method: POST
Path: /api/extract-detailed-criteria
Content-Type: application/json
```

**Request Schema**:
```json
{
  "query": "string (min_length=1)"
}
```

**Response Schema**:
```json
{
  "matched_criteria": {
    "property": {...},
    "proximity": {...},
    "user_journey": {...}
  },
  "missing_criteria": ["string"],
  "nearby_localities": [
    {"name": "string", "distance_km": "float"}
  ] // null if location not detected
}
```

---

**Endpoint 2**: Create Lead
```
Method: POST
Path: /api/leads/create
Content-Type: application/json
```

**Request Schema**:
```json
{
  "query": "string (min_length=1)"
}
```

**Response Schema**:
```json
{
  "lead_id": "string (uuid)",
  "extracted_criteria": {...},
  "matched_properties": ["object"],
  "nearby_localities": ["object"] // null if location not detected,
  "created_at": "string (ISO timestamp)"
}
```

---

## Data Model Changes

### New Request Models
- `ExtractDetailedCriteriaRequest`
- `CreateLeadRequest`

### New Response Models
- `ExtractDetailedCriteriaResponse`
- `CreateLeadResponse`

### New Data Models
- `PropertyCriteria`
- `ProximityPreferences`
- `UserJourney`
- `DetailedCriteria`
- `NearbyLocality`

---

## Environment Variables

**No new environment variables required** (uses existing `GEMINI_API_KEY`)

---

## Dependencies

**No new dependencies added** - Uses existing packages:
- `fastapi`
- `pydantic`
- `google-generativeai` (via `genai`)
- `python-dotenv`

---

## Breaking Changes

**None** - All changes are additive:
- New files created (no deletions)
- New router registered (no route conflicts)
- Existing code unmodified (backward compatible)

---

## Migration Path

No migration needed. Simply:
1. Start the server with existing environment variables
2. New endpoints automatically available via `/docs`
3. No database changes required

---

## Testing

### Endpoints to Test

**Test Extraction**:
```bash
curl -X POST http://localhost:8000/api/extract-detailed-criteria \
  -H "Content-Type: application/json" \
  -d '{"query": "3BHK near Indiranagar, budget 4-7 crores"}'
```

**Test Lead Creation**:
```bash
curl -X POST http://localhost:8000/api/leads/create \
  -H "Content-Type: application/json" \
  -d '{"query": "3BHK in Whitefield, budget 5 crores"}'
```

---

## Documentation

- **Comprehensive Summary**: `IMPLEMENTATION_SUMMARY.md`
- **This File**: `CHANGES.md`
- **Plan Document**: `/root/.claude/plans/zesty-wondering-valley.md`

---

## Performance Impact

- **Memory**: Minimal (singleton Gemini client, cached prompts)
- **Storage**: ~30 KB for new code, grows with leads.json
- **API Response Time**: Dependent on Gemini API latency

---

## Future Changes

### Planned Enhancements
1. Integration with WhatsApp listings API
2. Lead listing and retrieval endpoints
3. Lead update and delete operations
4. Database migration (JSON → SQLite → PostgreSQL)
5. Enhanced locality search with amenities

### Backward Compatibility
All planned changes will maintain backward compatibility with existing endpoints.

---

## Rollback Instructions

If needed, to rollback all changes:

```bash
# Remove new files
rm models/lead.py
rm services/lead_extraction_service.py
rm routers/lead_router.py
rm prompts/lead_criteria_extraction.txt
rm data/leads.json
rm IMPLEMENTATION_SUMMARY.md
rm CHANGES.md

# Restore main.py and __init__.py to original state
git checkout main.py routers/__init__.py
```

---

## Sign-off

✅ **Implementation Status**: Complete
✅ **Testing Status**: Ready for testing
✅ **Code Quality**: Follows codebase standards
✅ **Documentation**: Comprehensive
✅ **Backward Compatibility**: Maintained

**Ready for deployment and integration with WhatsApp listings API**

---

**Created**: 2025-12-13
**Framework**: FastAPI + Pydantic + Google Gemini API
**Implementation**: Claude Code
