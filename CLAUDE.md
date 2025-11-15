# Backend Development Guidelines - Programming Best Practices

---

## Quick Reference

**Check BEFORE coding:**
- **Project Documentation**: Review product specs and requirements docs
- **API Documentation**: Check existing API routes and schemas
- **Data Models**: Review existing models and type definitions

---

## Core Principles

**Four principles working together:**

1. **KISS** - Keep code simple and obvious. Avoid over-engineering.

2. **AHA** - Avoid Hasty Abstractions. Wait for 3 real use cases before abstracting. Duplication > wrong abstraction.

3. **WET** - Write Everything Twice. Write similar code twice to discover true patterns before abstracting.

4. **DRY** - Don't Repeat Yourself. AFTER seeing pattern 3 times, eliminate duplication through abstraction.

**Abstraction flow:**
- Use case 1: Write it (WET)
- Use case 2: Write it again (WET)
- Use case 3: Abstract it (DRY)
- Use case 4+: Reuse it (DRY)

---

## File Organization

**Backend structure:**

```
backend/
  agent/                  # LangGraph agents and workflows
    graph.py              # State machine definition
    state.py              # State models
    nodes/                # Individual graph nodes
  api/
    routes.py             # API endpoint definitions
  routers/                # FastAPI routers organized by feature
  services/               # Business logic layer
  models/                 # Data models and Pydantic schemas
  providers/              # External service integrations (LLM, DB, etc.)
  data/                   # Data files, configs
  utils/                  # Utility functions
```

**Key principles:**
- Group by feature/domain, not by type
- Keep related files together
- Flat is better than nested (avoid deep nesting)
- Separate concerns: routes → services → models

---

## Services Layer (Business Logic)

**ALWAYS abstract business logic into service modules**

Never put complex logic directly in route handlers. Use the service layer for clean separation of concerns.

### Service Structure

```python
# services/feature_service.py
from models.data_models import DataModel
from typing import Optional

class FeatureService:
    """Service for handling feature-related business logic"""

    @staticmethod
    async def get_data(id: str) -> Optional[DataModel]:
        """Retrieve data by ID"""
        # Business logic here
        pass

    @staticmethod
    async def process_data(data: dict) -> DataModel:
        """Process and validate data"""
        # Business logic here
        pass
```

### Service Guidelines

1. **One service per feature/domain** - `propalyst_service.py`, `auth_service.py`, etc.
2. **Static or class methods** - Services are generally stateless
3. **Type hints** - Use type hints for all function parameters and returns
4. **Error handling** - Raise specific exceptions, let routes handle HTTP responses
5. **Async when needed** - Use async/await for I/O operations (DB, API calls)

### Example Usage

```python
# ✅ GOOD: Using service layer
from services.feature_service import FeatureService

@router.post("/api/data")
async def create_data(request: DataRequest):
    try:
        result = await FeatureService.process_data(request.dict())
        return {"status": "success", "data": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

# ❌ BAD: Business logic directly in route
@router.post("/api/data")
async def create_data(request: DataRequest):
    # Complex validation logic...
    # Data transformation...
    # Multiple DB calls...
    # All mixed together in the route handler
```

**Benefits:**
- Single source of truth for business logic
- Easy to test in isolation
- Reusable across multiple routes
- Clear separation of concerns
- Easy to maintain and update

---

## Naming Conventions

**Files:**
- Modules: `user_service.py`, `auth_utils.py` (snake_case)
- Models: `data_models.py`, `state.py` (snake_case)
- Routers: `user_router.py`, `admin_router.py` (snake_case)

**Code:**
- Variables: `user_list`, `is_loading` (snake_case)
- Constants: `MAX_RETRY_COUNT`, `API_BASE_URL` (UPPER_SNAKE_CASE)
- Functions: `get_user_by_id()`, `calculate_total()` (snake_case, verb prefix: get/set/calculate/fetch/update/process)
- Classes: `UserService`, `DataModel` (PascalCase)
- Private methods: `_internal_helper()` (leading underscore)

---

## Type Hints and Pydantic Models

**Use type hints everywhere:**

```python
# ✅ GOOD: Explicit types
from typing import List, Optional, Dict, Any
from pydantic import BaseModel

class User(BaseModel):
    id: str
    name: str
    email: str
    age: Optional[int] = None

def get_users(limit: int = 10) -> List[User]:
    """Retrieve list of users"""
    pass

# ❌ BAD: No type hints
def get_users(limit=10):
    pass
```

**Pydantic guidelines:**
- Use Pydantic models for request/response schemas
- Validate data at API boundaries
- Use `Field()` for validation and documentation
- Prefer composition over inheritance

```python
from pydantic import BaseModel, Field

class UserCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: str = Field(..., regex=r'^[\w\.-]+@[\w\.-]+\.\w+$')
    age: Optional[int] = Field(None, ge=0, le=150)
```

---

## Error Handling

**Always handle errors gracefully:**

```python
from fastapi import HTTPException
from typing import Optional

class ServiceError(Exception):
    """Base exception for service layer"""
    pass

class NotFoundError(ServiceError):
    """Resource not found"""
    pass

class ValidationError(ServiceError):
    """Invalid data"""
    pass

# In service layer - raise specific exceptions
def get_user(user_id: str) -> User:
    user = db.get(user_id)
    if not user:
        raise NotFoundError(f"User {user_id} not found")
    return user

# In route handler - convert to HTTP responses
@router.get("/users/{user_id}")
async def get_user_endpoint(user_id: str):
    try:
        user = get_user(user_id)
        return user
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ServiceError as e:
        raise HTTPException(status_code=500, detail=str(e))
```

**Error handling principles:**
- Catch specific exceptions, not generic `Exception`
- Log errors with context for debugging
- Return user-friendly error messages
- Use HTTP status codes correctly (400, 404, 500, etc.)
- Don't expose sensitive information in error messages

---

## API Design

**RESTful endpoints:**

```python
# Resources are nouns, not verbs
GET    /api/users          # List users
POST   /api/users          # Create user
GET    /api/users/{id}     # Get specific user
PUT    /api/users/{id}     # Update user (full)
PATCH  /api/users/{id}     # Update user (partial)
DELETE /api/users/{id}     # Delete user

# Nested resources
GET    /api/users/{id}/posts    # Get user's posts
POST   /api/users/{id}/posts    # Create post for user
```

**Request/Response patterns:**

```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/users", tags=["users"])

class UserResponse(BaseModel):
    id: str
    name: str
    email: str

@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: str):
    """Get user by ID"""
    user = await UserService.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
```

---

## Async/Await Best Practices

**When to use async:**

```python
# ✅ GOOD: Use async for I/O operations
async def fetch_user_data(user_id: str):
    # Database query (I/O)
    user = await db.users.find_one({"id": user_id})

    # External API call (I/O)
    profile = await http_client.get(f"/profiles/{user_id}")

    return combine_data(user, profile)

# ✅ GOOD: Regular function for CPU-bound work
def calculate_statistics(data: List[float]) -> dict:
    # Pure computation, no I/O
    return {
        "mean": sum(data) / len(data),
        "max": max(data),
        "min": min(data)
    }

# ❌ BAD: Async for CPU-bound work (unnecessary overhead)
async def calculate_sum(numbers: List[int]) -> int:
    return sum(numbers)
```

**Async guidelines:**
- Use `async/await` for database queries, API calls, file I/O
- Don't use `async` for pure computation
- Use `asyncio.gather()` for concurrent operations
- Be careful with blocking operations in async functions

---

## Code Readability

**Readability > cleverness > brevity**

- Use full words, not abbreviations (except: `id`, `url`, `db`, etc.)
- Extract complex conditions into named variables
- Add whitespace to group related logic
- Use docstrings for functions and classes
- Write as if explaining to a junior developer

```python
# ✅ GOOD: Clear and readable
def is_user_eligible_for_premium(user_age: int, account_duration_days: int) -> bool:
    """Check if user meets premium eligibility criteria"""
    meets_age_requirement = user_age >= 18
    meets_duration_requirement = account_duration_days >= 30

    return meets_age_requirement and meets_duration_requirement

# ❌ BAD: Too clever, hard to understand
def check(a: int, d: int) -> bool:
    return a >= 18 and d >= 30
```

---

## Testing

**Write testable code:**

```python
# services/user_service.py
class UserService:
    @staticmethod
    async def create_user(data: dict) -> User:
        """Create new user"""
        # Validation
        if not data.get("email"):
            raise ValidationError("Email is required")

        # Create user
        user = User(**data)
        await db.save(user)
        return user

# tests/test_user_service.py
import pytest
from services.user_service import UserService

@pytest.mark.asyncio
async def test_create_user_success():
    data = {"email": "test@example.com", "name": "Test User"}
    user = await UserService.create_user(data)
    assert user.email == "test@example.com"

@pytest.mark.asyncio
async def test_create_user_missing_email():
    data = {"name": "Test User"}
    with pytest.raises(ValidationError):
        await UserService.create_user(data)
```

---

## Environment Configuration

**Use environment variables for configuration:**

```python
# config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    API_BASE_URL: str
    DATABASE_URL: str
    SECRET_KEY: str
    DEBUG: bool = False

    class Config:
        env_file = ".env"

settings = Settings()

# Usage
from config import settings

async def connect_db():
    return await create_connection(settings.DATABASE_URL)
```

---

## Git Commits

**Use conventional commits:**
```
feat: add user authentication endpoint
fix: correct validation logic in user service
refactor: extract database logic into separate module
docs: update API documentation
test: add unit tests for user service
chore: update dependencies
```

**Types:** `feat`, `fix`, `refactor`, `docs`, `test`, `chore`, `style`, `perf`

**Rules:**
- One logical change per commit
- Imperative mood ("add" not "added" or "adds")
- First line < 50 chars (summary)
- Blank line, then detailed explanation if needed
- Reference issue numbers when applicable (`fixes #123`)

---

## Performance & Optimization - Teaching Moments

**When files get too large, use it as a teaching opportunity**

As a senior developer and mentor, recognize code smells and scalability issues proactively. When you notice performance problems or growing file sizes, suggest optimizations using the core programming principles.

### Recognizing Scalability Issues

**File Size Warning Signs:**
- JSON data files > 500KB
- Loading entire dataset into memory for every operation
- Linear growth in file size with usage
- Performance degradation as data grows
- No pagination or data expiry strategy

**Example: `scraped_properties.json` at 305KB and growing**

```bash
# Check file size
ls -lh data/scraped_properties.json
# Output: -rw-r--r-- 1 user user 305K Nov 15 12:01 scraped_properties.json

# Check line count
wc -l data/scraped_properties.json
# Output: 4279 data/scraped_properties.json
```

### Teaching Moment: Apply Core Principles

**1. KISS (Keep It Simple, Stupid)**
- **Problem**: Loading 300KB+ JSON into memory for every API call
- **Solution**: Add pagination, implement lazy loading, or switch to a database
- **Teaching**: "We're keeping it simple now, but at 500KB+ we should consider SQLite for better performance"

**2. DRY (Don't Repeat Yourself)**
- **Problem**: Duplicate property entries for same URL/scrape
- **Solution**: Add deduplication logic, use URL as unique key
- **Teaching**: "Notice we're storing the same property multiple times? Let's deduplicate by property_url"

**3. Separation of Concerns**
- **Problem**: Data persistence mixed with business logic
- **Solution**: Already using DataPersistenceService - good! Now consider data archiving service
- **Teaching**: "Our service layer is clean, but now we need an archival strategy"

### Optimization Strategies (Progressive)

**Stage 1: Simple JSON (0-500KB) ✓ Current**
```python
# Keep current approach - simple and works
data = json.load(f)  # Load all into memory
```
- **Pros**: Simple, no dependencies, easy to debug
- **Cons**: Doesn't scale, slow for large datasets
- **When to move on**: File > 500KB or performance issues

**Stage 2: Indexed JSON (500KB-5MB)**
```python
# Split into separate files by date or source
data/
  scraped_properties_2025_01.json
  scraped_properties_2025_02.json
  index.json  # Maps URLs to file locations
```
- **Pros**: Still simple, better performance
- **Cons**: More file management complexity
- **When to move on**: Multiple files getting large

**Stage 3: SQLite (5MB-100MB)**
```python
# Add SQLite with proper indexes
import sqlite3

CREATE TABLE properties (
    id INTEGER PRIMARY KEY,
    url TEXT UNIQUE,
    source TEXT,
    scraped_at TIMESTAMP,
    data JSON
);
CREATE INDEX idx_url ON properties(url);
CREATE INDEX idx_scraped_at ON properties(scraped_at);
```
- **Pros**: Fast queries, ACID compliance, still file-based
- **Cons**: Need migration, slightly more complex
- **When to move on**: Need concurrent writes or distributed access

**Stage 4: PostgreSQL/MySQL (100MB+)**
- Full database with connection pooling
- Proper normalization and relationships
- Backup and replication strategies

### Suggesting Optimizations - Communication Template

**When you notice a file getting large:**

```
🔍 **Performance Note**: I notice `scraped_properties.json` is now 305KB with 4,279 lines.

**Current Status**: ✅ Working fine for now

**Future Optimization** (when file reaches ~500KB):
We should consider one of these approaches:

1. **Add Data Expiry** (Simplest - KISS principle)
   - Auto-delete entries older than 30 days
   - Keeps file size manageable
   - Pros: Simple, no architecture change
   - Cons: Lose historical data

2. **Switch to SQLite** (Recommended for growth)
   - Better performance with indexing
   - Query by date, source, or URL efficiently
   - Pros: Scales to 100MB+, fast queries
   - Cons: Need migration script

3. **Implement Pagination** (Medium complexity)
   - Load data in chunks instead of all at once
   - Better memory usage
   - Pros: Works with current JSON approach
   - Cons: More complex API logic

**Recommendation**: Monitor file size. When it hits 500KB, let's implement #1 (expiry) first (KISS), then move to #2 (SQLite) if we need better query performance.

Would you like me to implement data expiry now, or wait until we hit the threshold?
```

### Key Teaching Points

1. **Premature Optimization is Evil**
   - Don't optimize before you have a problem
   - JSON files < 500KB are perfectly fine
   - Measure first, optimize later

2. **Progressive Enhancement**
   - Start simple (JSON files)
   - Add complexity only when needed
   - Each stage solves specific problems

3. **Trade-offs Matter**
   - Simple JSON: Easy to debug, doesn't scale
   - SQLite: Better performance, more complexity
   - PostgreSQL: Best performance, much more complexity

4. **Use Principles as Guide**
   - **KISS**: Start with simplest solution
   - **AHA**: Don't abstract until 3rd use case
   - **WET**: Write it twice before optimizing
   - **DRY**: Remove duplication once pattern is clear

### Monitoring & Metrics

**Add to your service:**
```python
class DataPersistenceService:
    @classmethod
    async def get_file_stats(cls) -> Dict[str, Any]:
        """Get statistics about data file size and growth"""
        if not cls.DATA_FILE_PATH.exists():
            return {"size_kb": 0, "entry_count": 0}

        file_size = cls.DATA_FILE_PATH.stat().st_size / 1024  # KB
        data = cls._load_existing_data()

        return {
            "size_kb": round(file_size, 2),
            "size_mb": round(file_size / 1024, 2),
            "entry_count": len(data),
            "warning": file_size > 500,  # Warn at 500KB
            "critical": file_size > 5000  # Critical at 5MB
        }
```

### Summary: Be Proactive But Not Premature

✅ **DO:**
- Monitor file sizes and performance
- Suggest optimizations when thresholds are reached
- Explain trade-offs using programming principles
- Use it as a teaching moment

❌ **DON'T:**
- Optimize before there's a problem
- Jump straight to complex solutions
- Ignore warning signs of scaling issues
- Leave the user confused about why changes are needed

**Remember**: Every optimization suggestion is an opportunity to teach software engineering principles in a real-world context.

---

## Summary

**Golden Rules:**
1. **KISS** - Keep it simple
2. **AHA** - Wait for 3 use cases before abstracting
3. **WET→DRY** - Write twice, then eliminate duplication
4. **Services layer** - Abstract business logic into service modules
5. **Type hints everywhere** - Use Pydantic models and type annotations
6. **Error handling** - Use specific exceptions and proper HTTP status codes
7. **Async for I/O** - Use async/await for database and API calls
8. **Test your code** - Write unit tests for services and integration tests for routes
9. **Readability over brevity** - Clear names, explicit types, good documentation
10. **Remember:** Code is read 10x more than it's written. Optimize for the next developer (including future you).

---

**End of Backend Development Guidelines**
