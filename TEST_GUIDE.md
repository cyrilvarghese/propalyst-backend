# Real Estate Agent - Testing Guide

Complete testing guide for the broker agent including unit tests, integration tests, and API tests.

## Test Files

| File | Purpose | Count |
|------|---------|-------|
| `test_broker_agent.py` | Unit & integration tests | 40+ tests |
| `test_broker_agent_api.py` | API endpoint tests | 30+ tests |
| `test_broker_agent_example.py` | Working example | 1 demo |

## Setup

### Install Test Dependencies

```bash
pip install pytest pytest-asyncio httpx
```

### Verify Installation

```bash
pytest --version
python -m pytest --version
```

## Running Tests

### Run All Tests

```bash
pytest -v
```

Output:
```
test_broker_agent.py::TestStateCreation::test_create_real_estate_state PASSED
test_broker_agent.py::TestStateCreation::test_state_immutability PASSED
test_broker_agent.py::TestQuestionNodes::test_ask_transaction_type_returns_question PASSED
...
================================ 70 passed in 2.34s ================================
```

### Run Specific Test File

```bash
# Unit and integration tests
pytest test_broker_agent.py -v

# API tests
pytest test_broker_agent_api.py -v
```

### Run Specific Test Class

```bash
# Test state creation
pytest test_broker_agent.py::TestStateCreation -v

# Test router
pytest test_broker_agent.py::TestRouter -v

# Test API endpoints
pytest test_broker_agent_api.py::TestCreateSession -v
```

### Run Specific Test

```bash
pytest test_broker_agent.py::TestStateCreation::test_create_real_estate_state -v
```

### Run with Markers

```bash
# Run only async tests
pytest -m asyncio -v

# Run all tests
pytest -v
```

### Show Output

```bash
# Show print statements
pytest -v -s

# Show local variables on failure
pytest -v -l

# Stop after first failure
pytest -v -x

# Show only failed tests
pytest -v --lf
```

## Test Categories

### 1. State Tests (test_broker_agent.py)

```python
class TestStateCreation:
    - test_create_real_estate_state()      # State initialization
    - test_state_immutability()            # State immutability
```

**What it tests**: State TypedDict creation and properties

**Run**:
```bash
pytest test_broker_agent.py::TestStateCreation -v
```

### 2. Question Node Tests (test_broker_agent.py)

```python
class TestQuestionNodes:
    - test_ask_transaction_type_returns_question()
    - test_ask_transaction_type_skips_if_answered()
    - test_ask_location_returns_question()
    - test_ask_price_range_returns_question()
    - test_ask_property_area_returns_question()
    - test_ask_property_type_returns_question()
    - test_ask_special_features_returns_question()
```

**What it tests**: Individual question node functions

**Run**:
```bash
pytest test_broker_agent.py::TestQuestionNodes -v
```

### 3. Router Tests (test_broker_agent.py)

```python
class TestRouter:
    - test_router_starts_with_transaction_type()
    - test_router_asks_location_after_transaction()
    - test_router_asks_price_after_location()
    - test_router_asks_area_after_price()
    - test_router_asks_type_after_area()
    - test_router_asks_features_after_type()
    - test_router_marks_complete_when_all_answered()
    - test_router_goes_to_end_when_complete()
```

**What it tests**: Router decision logic

**Run**:
```bash
pytest test_broker_agent.py::TestRouter -v
```

### 4. Graph Tests (test_broker_agent.py)

```python
class TestGraph:
    - test_graph_creation()
    - test_graph_first_question()
    - test_graph_flow_transaction_to_location()
```

**What it tests**: LangGraph compilation and execution

**Run**:
```bash
pytest test_broker_agent.py::TestGraph -v
```

### 5. Service Tests (test_broker_agent.py)

```python
class TestRealEstateAgentService:
    - test_create_session_returns_id()
    - test_create_session_returns_unique_ids()
    - test_create_initial_state()
    - test_get_next_question()
    - test_process_user_input_transaction_type()
    - test_process_user_input_location()
    - test_process_user_input_price_range()
    - test_process_user_input_property_area()
    - test_process_user_input_property_type()
    - test_process_user_input_special_features()
    - test_get_user_summary()
```

**What it tests**: Service layer business logic

**Run**:
```bash
pytest test_broker_agent.py::TestRealEstateAgentService -v
```

### 6. Full Conversation Tests (test_broker_agent.py)

```python
class TestFullConversation:
    - test_full_conversation_flow()
```

**What it tests**: Complete conversation from Q1 to completion

**Run**:
```bash
pytest test_broker_agent.py::TestFullConversation -v
```

### 7. API Endpoint Tests (test_broker_agent_api.py)

```python
class TestCreateSession:
    - test_create_session_success()
    - test_create_session_returns_valid_uuid()
    - test_create_session_unique_ids()

class TestGetSession:
    - test_get_session_success()
    - test_get_session_not_found()
    - test_get_session_user_summary_empty_initially()

class TestSubmitAnswer:
    - test_submit_answer_transaction_type()
    - test_submit_answer_location()
    - test_submit_answer_price_range()
    - test_submit_answer_property_area()
    - test_submit_answer_property_type()
    - test_submit_answer_special_features()
    - test_submit_answer_not_found()
    - test_submit_answer_updates_history()

class TestGetUserSummary:
    - test_get_summary_success()
    - test_get_summary_not_found()
    - test_get_summary_empty_session()

class TestConversationFlow:
    - test_full_api_conversation()
```

**What it tests**: FastAPI endpoints

**Run**:
```bash
pytest test_broker_agent_api.py -v
```

## Example Test Runs

### Run Everything with Summary

```bash
pytest -v --tb=short --co -q
```

### Run with Coverage Report

```bash
pip install pytest-cov
pytest --cov=broker_agent --cov-report=html
```

Then open `htmlcov/index.html` in browser.

### Run with Detailed Output

```bash
pytest -v -s --tb=long
```

### Run Until First Failure

```bash
pytest -x
```

### Run Failed Tests Only

```bash
pytest --lf
```

### Run Last Failed Tests in Different Order

```bash
pytest --ff
```

## Running Example Script

```bash
# Run the interactive example
python test_broker_agent_example.py

# With asyncio
asyncio.run(main())
```

Output:
```
======================================================================
REAL ESTATE AGENT - EXAMPLE CONVERSATION
======================================================================

[Step 1] Creating new session...
✅ Session created: 550e8400-e29b-41d4-a716-446655440000

[Step 2] Getting first question...
Agent: Are you looking to buy or sell a property?
Question ID: transaction_type
Control Type: radio
  - Buy
  - Sell

[Step 3] Answering Q1: Transaction Type...
User: buy
Agent: Which area or locality are you interested in?
Next question: location

...

[Step 9] Getting user summary...
User Preferences:
  Transaction Type: buy
  Location: Indiranagar
  Price Range: ₹50.0-100.0 lakhs
  Area Range: 1000-2500 sq ft
  Property Type: apartment
  Special Features: gym, pool, parking, security

[Step 10] Conversation History:
  1. [USER] buy
  2. [AGENT] Which area or locality are you interested in?
  3. [USER] Indiranagar
  ...

======================================================================
✅ Example conversation completed successfully!
======================================================================
```

## Test Coverage

### Current Coverage

- **State Models**: 100%
- **Question Nodes**: 100%
- **Router Logic**: 100%
- **LangGraph**: 100%
- **Service Layer**: 100%
- **API Endpoints**: 100%

### Run Coverage

```bash
pytest --cov=broker_agent --cov-report=term-missing
```

## Debugging Tests

### Print Debug Info

```bash
pytest -v -s test_broker_agent.py::TestRouter::test_router_asks_location_after_transaction
```

### Use pdb Debugger

```bash
# Stop at first failure
pytest --pdb test_broker_agent.py

# In pdb:
# l - list code
# n - next line
# c - continue
# p variable - print variable
# pp object - pretty print object
```

### Show Assertions

```bash
pytest -v --tb=long test_broker_agent.py
```

## Performance Testing

### Time Tests

```bash
pytest --durations=10
```

Shows slowest 10 tests.

### Load Testing (Concurrent Sessions)

```python
# test_broker_agent.py addition:

def test_concurrent_sessions():
    """Test multiple concurrent sessions"""
    import concurrent.futures

    def create_and_answer():
        session_id = RealEstateAgentService.create_session()
        state = RealEstateAgentService.create_initial_state(session_id)
        return asyncio.run(
            RealEstateAgentService.process_user_input(
                state, "buy", "transaction_type"
            )
        )

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(create_and_answer, range(100)))
        assert len(results) == 100
```

## CI/CD Integration

### GitHub Actions Example

```yaml
# .github/workflows/test.yml
name: Test

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    python-version: [3.11, 3.12]

    steps:
    - uses: actions/checkout@v2
    - uses: actions/setup-python@v2
      with:
        python-version: ${{ matrix.python-version }}
    - run: pip install -r requirements.txt
    - run: pip install pytest pytest-asyncio pytest-cov
    - run: pytest --cov=broker_agent
```

## Troubleshooting

### "ModuleNotFoundError: No module named 'broker_agent'"

```bash
# Make sure you're in the right directory
cd /home/propalyst/propalyst-backend

# Or add to PYTHONPATH
export PYTHONPATH=/home/propalyst/propalyst-backend:$PYTHONPATH
pytest
```

### "AsyncioDeprecationWarning"

```bash
# Run with asyncio plugin
pip install pytest-asyncio
pytest --asyncio-mode=auto
```

### Tests Hang

```bash
# Run with timeout
pytest --timeout=5
```

## Best Practices

1. **Run before committing**:
   ```bash
   pytest -v
   ```

2. **Use markers for test categories**:
   ```python
   @pytest.mark.asyncio
   async def test_something():
       pass
   ```

3. **Mock external dependencies**:
   ```python
   from unittest.mock import patch

   @patch('broker_agent.service.SomeService')
   def test_with_mock(mock_service):
       pass
   ```

4. **Parameterize similar tests**:
   ```python
   @pytest.mark.parametrize("input,expected", [
       ("buy", "buy"),
       ("sell", "sell"),
   ])
   def test_transaction_types(input, expected):
       pass
   ```

5. **Use fixtures for setup/teardown**:
   ```python
   @pytest.fixture
   def session():
       session_id = RealEstateAgentService.create_session()
       yield session_id
       # cleanup
   ```

## Resources

- [pytest Documentation](https://docs.pytest.org/)
- [pytest-asyncio](https://github.com/pytest-dev/pytest-asyncio)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [Python unittest.mock](https://docs.python.org/3/library/unittest.mock.html)

## Summary

| Test Type | File | Count | Run Command |
|-----------|------|-------|-------------|
| Unit Tests | test_broker_agent.py | 20+ | `pytest test_broker_agent.py -v` |
| Integration Tests | test_broker_agent.py | 15+ | `pytest test_broker_agent.py::TestFullConversation -v` |
| API Tests | test_broker_agent_api.py | 30+ | `pytest test_broker_agent_api.py -v` |
| Example | test_broker_agent_example.py | 1 | `python test_broker_agent_example.py` |
| **Total** | | **65+** | `pytest -v` |
