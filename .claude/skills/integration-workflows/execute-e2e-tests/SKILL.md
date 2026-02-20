---
name: execute-e2e-tests
description: Run end-to-end integration tests across all system layers
version: 1.0.0
agent: integration-orchestrator
reusability: high
---

# Execute End-to-End Tests

## Purpose

Execute integration and end-to-end tests that verify complete workflows across frontend, backend, domain, and persistence layers.

## When to Use

- After multi-layer feature implementation
- Before marking workflow as complete
- During regression testing
- Pre-deployment validation

## Inputs

- Test suite location (`tests/integration/`, `tests/e2e/`)
- Feature being tested
- Test environment configuration
- Database test fixtures

## Outputs

- **Test execution results** (pass/fail counts)
- **Failed test details** with error messages
- **Test coverage report**
- **Performance metrics** (optional)

## E2E Test Strategy

### Test Levels

**1. Integration Tests (Layer-to-Layer)**
- Backend → Domain integration
- Backend → Database integration
- API endpoint contracts

**2. End-to-End Tests (Full Workflow)**
- User journey simulation
- Complete request/response cycle
- Database state verification

### Test Execution Workflow

```bash
# 1. Setup test environment
export DATABASE_URL="postgresql://localhost/test_db"
export BETTER_AUTH_SECRET="test-secret"

# 2. Run database migrations for test DB
alembic upgrade head --database test_db

# 3. Seed test data
python tests/fixtures/seed_test_data.py

# 4. Run integration tests
pytest tests/integration/ -v --tb=short

# 5. Run E2E tests
pytest tests/e2e/ -v --tb=short

# 6. Cleanup test environment
alembic downgrade base --database test_db
```

## Test Categories

### 1. Domain Layer Tests (Unit)

```python
# tests/domain/test_task_creation.py
def test_task_requires_title():
    """Domain enforces invariant: title required."""
    with pytest.raises(DomainViolationError, match="Title required"):
        Task.create(title="", description="Test")

def test_task_state_transitions():
    """Domain enforces valid state transitions."""
    task = Task.create(title="Test", description="Desc")
    task.complete()
    assert task.status == TaskStatus.COMPLETE

    # Cannot complete already completed task
    with pytest.raises(StateTransitionError):
        task.complete()
```

### 2. Backend Integration Tests

```python
# tests/integration/test_task_service.py
def test_create_task_persists_to_database(db_session):
    """TaskService creates task and saves to database."""
    service = TaskService(db_session)

    task = service.create_task(
        title="Integration test task",
        description="Testing persistence"
    )

    # Verify saved to database
    saved_task = db_session.query(TaskModel).filter_by(id=task.id).first()
    assert saved_task is not None
    assert saved_task.title == "Integration test task"
```

### 3. API Contract Tests

```python
# tests/integration/test_api_tasks.py
def test_create_task_api_contract(client):
    """POST /api/tasks returns correct schema."""
    response = client.post("/api/tasks", json={
        "title": "API test task",
        "description": "Testing API"
    })

    assert response.status_code == 201
    data = response.json()

    # Verify response schema
    assert "id" in data
    assert data["title"] == "API test task"
    assert data["status"] == "pending"
    assert "createdAt" in data
```

### 4. End-to-End Workflow Tests

```python
# tests/e2e/test_task_lifecycle.py
def test_complete_task_lifecycle(client, db_session):
    """Complete task workflow: create → update → complete → delete."""

    # 1. Create task
    create_response = client.post("/api/tasks", json={
        "title": "E2E test task",
        "description": "Full lifecycle test"
    })
    assert create_response.status_code == 201
    task_id = create_response.json()["id"]

    # 2. Get task
    get_response = client.get(f"/api/tasks/{task_id}")
    assert get_response.status_code == 200
    assert get_response.json()["status"] == "pending"

    # 3. Update task
    update_response = client.patch(f"/api/tasks/{task_id}", json={
        "title": "Updated title"
    })
    assert update_response.status_code == 200
    assert update_response.json()["title"] == "Updated title"

    # 4. Complete task
    complete_response = client.post(f"/api/tasks/{task_id}/complete")
    assert complete_response.status_code == 200
    assert complete_response.json()["status"] == "complete"

    # 5. Delete task
    delete_response = client.delete(f"/api/tasks/{task_id}")
    assert delete_response.status_code == 204

    # 6. Verify deleted from database
    deleted_task = db_session.query(TaskModel).filter_by(id=task_id).first()
    assert deleted_task is None
```

## Test Execution Commands

### Run All Tests

```bash
# Run all tests with coverage
pytest tests/ --cov=app --cov-report=html --cov-report=term

# Run only integration tests
pytest tests/integration/ -v

# Run only E2E tests
pytest tests/e2e/ -v

# Run specific test file
pytest tests/integration/test_task_service.py -v
```

### Test Result Interpretation

**Exit Codes:**
- `0` - All tests passed ✅
- `1` - Tests failed ❌
- `2` - Test execution interrupted
- `5` - No tests collected

**Output Parsing:**
```
tests/integration/test_task_service.py::test_create_task PASSED [ 50%]
tests/integration/test_task_service.py::test_update_task FAILED [100%]

FAILED tests/integration/test_task_service.py::test_update_task - AssertionError
```

## Failure Analysis Workflow

### When Tests Fail

**1. Identify Failure Layer**

```
Frontend test failed → Frontend issue
API contract test failed → Backend issue
Integration test failed → Backend or Domain issue
Unit test failed → Domain logic issue
```

**2. Extract Error Details**

```python
# Example pytest output
FAILED tests/e2e/test_task_lifecycle.py::test_complete_task_lifecycle
AssertionError: assert 422 == 200
Expected status 200, got 422 Unprocessable Entity

# Indicates: Backend validation failed
# Likely cause: Domain invariant violated
# Fix: Check domain validation rules
```

**3. Recommend Remediation**

```
Test: test_create_task_with_empty_title
Status: FAILED
Layer: Domain
Error: DomainViolationError: Title required
Fix: Update domain test or fix domain validation logic
Agent: Domain Guardian (re-run to fix)
```

## Constraints

- **MUST** run tests in clean environment (isolated database)
- **MUST** cleanup test data after execution
- **DO NOT** run tests against production database
- **MUST** validate test results programmatically (not manual review)

## Reusability

**Domain-Agnostic:** Test execution pattern works for any domain

**Applicable To:**
- Web applications
- API services
- CLI applications
- Any testable system

**Evolution:**
- Phase 1: Manual test execution
- Phase 2: Automated test runs on workflow completion
- Phase 3: Parallel test execution
- Phase 4: AI-driven test generation

## Integration Points

**Triggered After:**
- Multi-agent workflow completion
- Code changes to any layer

**Requires:**
- Test framework (pytest)
- Test database
- Test fixtures

**Outputs To:**
- Test results report
- Failed test analysis
- Remediation recommendations
