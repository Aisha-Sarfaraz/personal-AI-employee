---
name: validate-integration-points
description: Verify contracts and interfaces between system layers are correctly implemented
version: 1.0.0
agent: integration-orchestrator
reusability: high
---

# Validate Integration Points

## Purpose

Validate that interfaces and contracts between system layers (frontend ↔ backend, backend ↔ domain, domain ↔ persistence) are correctly implemented and compatible.

## When to Use

- After multi-layer implementation
- Before integration testing
- When interface contracts change
- During cross-layer refactoring

## Inputs

- Domain model definitions
- Backend API contracts (OpenAPI/route definitions)
- Frontend data fetching code
- Database schema definitions
- Repository interfaces

## Outputs

- **Contract compatibility report** (✅ compatible, ❌ mismatched)
- **Interface validation results**
- **Type safety verification**
- **Missing integration detection**

## Validation Checklist

### 1. Frontend ↔ Backend Integration

**API Contract Validation:**

```typescript
// Frontend expects this API response:
interface TaskResponse {
  id: string
  title: string
  status: "pending" | "complete"
  priority?: "high" | "medium" | "low"
}

// Backend provides:
GET /api/tasks/{id} → TaskResponse

// Validation:
✅ Response type matches frontend expectation
✅ All required fields present
✅ Optional fields correctly typed
✅ Enum values match
```

**Validation Steps:**
1. Extract frontend TypeScript types
2. Extract backend response schemas
3. Compare field names, types, optionality
4. Report mismatches

**Common Mismatches:**
- Frontend expects `snake_case`, backend provides `camelCase`
- Frontend expects array, backend provides single object
- Backend returns extra fields frontend doesn't use (okay)
- Backend missing fields frontend requires (CRITICAL)

### 2. Backend ↔ Domain Integration

**Service-Domain Contract:**

```python
# Backend ApplicationService expects:
class TaskService:
    def create_task(self, title: str, description: str) -> Task:
        # Calls domain
        task = Task.create(title=title, description=description)
        return task

# Domain provides:
class Task:
    @staticmethod
    def create(title: str, description: str) -> "Task":
        # Enforces invariants
        if not title:
            raise DomainViolationError("Title required")
        return Task(title=title, description=description)

# Validation:
✅ Service calls domain method that exists
✅ Service passes correct parameter types
✅ Service handles domain exceptions
✅ Service doesn't bypass domain logic
```

**Validation Steps:**
1. Identify domain method calls in backend
2. Verify domain methods exist with matching signatures
3. Check exception handling
4. Ensure no direct entity instantiation bypassing domain logic

### 3. Domain ↔ Persistence Integration

**Repository Interface Contract:**

```python
# Domain defines interface:
class TaskRepository(Protocol):
    def save(self, task: Task) -> None: ...
    def find_by_id(self, task_id: str) -> Optional[Task]: ...
    def find_all(self) -> List[Task]: ...

# Infrastructure implements:
class PostgresTaskRepository:
    def save(self, task: Task) -> None:
        # Maps Task to database row
        pass

    def find_by_id(self, task_id: str) -> Optional[Task]:
        # Queries database, returns Task domain object
        pass

# Validation:
✅ Repository implements all interface methods
✅ Method signatures match exactly
✅ Returns domain objects (not ORM models)
✅ Handles not-found cases correctly
```

**Validation Steps:**
1. Extract repository interface from domain
2. Verify infrastructure implementation exists
3. Check method signature compatibility
4. Validate domain object mapping

### 4. End-to-End Data Flow Validation

**Complete Request Flow:**

```
1. Frontend → POST /api/tasks {title: "New task"}
2. Backend API → TaskService.create_task(title)
3. TaskService → Task.create(title) [domain]
4. Task validates invariants
5. TaskService → repository.save(task)
6. Repository → Database INSERT
7. Repository returns saved Task
8. Backend API → TaskResponse {id, title, status}
9. Frontend receives response
```

**Validation Points:**
- [ ] Frontend sends correct request format
- [ ] Backend deserializes correctly
- [ ] Backend calls domain with correct parameters
- [ ] Domain enforces invariants
- [ ] Backend persists via repository
- [ ] Repository maps domain to database
- [ ] Backend returns correct response format
- [ ] Frontend receives expected type

## Validation Workflow

### Step 1: Extract All Interface Definitions

```bash
# Frontend types
grep -r "interface.*Response\|type.*Response" frontend/

# Backend API schemas
grep -r "@app.post\|@app.get" backend/api/

# Domain interfaces
grep -r "class.*Protocol\|class.*ABC" domain/

# Repository implementations
grep -r "class.*Repository" infrastructure/
```

### Step 2: Build Integration Map

```yaml
integration_map:
  frontend_backend:
    - endpoint: "/api/tasks"
      frontend_type: "TaskResponse"
      backend_response: "TaskResponseSchema"
      status: COMPATIBLE

  backend_domain:
    - service: "TaskService.create_task"
      domain_method: "Task.create"
      status: COMPATIBLE

  domain_persistence:
    - interface: "TaskRepository"
      implementation: "PostgresTaskRepository"
      status: COMPATIBLE
```

### Step 3: Validate Each Integration Point

For each integration:
1. Compare interface definitions
2. Check type compatibility
3. Verify error handling
4. Validate data transformations

### Step 4: Report Violations

```markdown
## Integration Validation Report

### ✅ Compatible Integrations (3)
- Frontend ↔ Backend: /api/tasks (GET)
- Backend ↔ Domain: TaskService → Task.create
- Domain ↔ Persistence: TaskRepository interface

### ❌ Incompatible Integrations (1)
- Frontend ↔ Backend: /api/tasks (POST)
  - Issue: Frontend expects {priority?: string}, Backend requires {priority: string}
  - Severity: CRITICAL
  - Fix: Make priority optional in backend schema

### ⚠️ Warnings (1)
- Backend ↔ Domain: TaskService bypasses domain validation
  - Issue: Direct Task() instantiation in update method
  - Severity: MEDIUM
  - Fix: Use Task.update() domain method
```

## Constraints

- **DO NOT** validate implementation details (only interfaces)
- **DO NOT** require perfect naming consistency (camelCase vs snake_case okay)
- **MUST** flag type incompatibilities (CRITICAL)
- **MUST** flag missing error handling (HIGH)

## Reusability

**Domain-Agnostic:** Works for any multi-layer system

**Applicable To:**
- Web applications
- API services
- Microservices
- Any layered architecture

## Integration Points

**Triggered After:**
- Multi-agent workflow completion
- Interface contract changes
- Before integration tests

**Invokes:**
- File reading tools (to extract interfaces)
- Grep tool (to find interface definitions)
- Code analysis (type compatibility)

**Outputs To:**
- Integration validation report
- Contract mismatch detection
- Remediation recommendations
