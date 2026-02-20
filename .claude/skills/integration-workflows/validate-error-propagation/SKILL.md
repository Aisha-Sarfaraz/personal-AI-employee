---
name: validate-error-propagation
description: Validate error handling and propagation across all system layers using Clean Architecture and DDD best practices
version: 1.0.0
agent: integration-orchestrator
type: validation
inputs:
  - file_paths: Array of file paths to validate (domain, backend, frontend)
  - validation_scope: "full" | "domain-only" | "backend-only" | "frontend-only"
outputs:
  - validation_report: Error propagation validation report with severity levels
  - error_score: Overall error handling score (0-100)
  - critical_issues: List of blocking error handling violations
  - recommendations: Actionable error handling improvements
reusability: extremely-high
framework_agnostic: yes
requires_context7: true
estimated_execution_time: 3-5 minutes
---

# Skill: validate-error-propagation

## 1. Purpose

This skill validates error handling and propagation patterns across all system layers following Clean Architecture, Domain-Driven Design (DDD), and multi-tier application best practices. It ensures errors are properly classified, propagated across layers, mapped to appropriate HTTP status codes, handled gracefully in the frontend, and logged for observability across ANY framework and ANY domain.

**Core Objectives:**
- **Layer-Appropriate Error Handling**: Validate that each layer uses correct error patterns (domain errors, HTTP exceptions, user messages)
- **Error Propagation Validation**: Ensure domain errors flow correctly through backend to frontend
- **HTTP Status Code Mapping**: Verify backend maps domain/validation errors to correct HTTP status codes (400, 403, 422, 500)
- **Frontend Error Handling**: Validate that frontend handles error responses gracefully with user-friendly messages
- **Security Validation**: Ensure no stack traces, internal details, or sensitive data exposed to users
- **Observability Compliance**: Verify errors are logged at appropriate layers for debugging and monitoring
- **Framework/Domain Agnostic**: Works across all frameworks (Next.js, React, FastAPI, Flask, Express) and domains (Todo, E-commerce, SaaS)

**Why This Skill Exists:**

Error handling is a **critical quality attribute** that directly impacts user experience, system reliability, and security. Poor error handling leads to:
- **Security vulnerabilities**: Exposing stack traces and internal implementation details
- **Poor user experience**: Cryptic error messages that confuse users
- **Debugging nightmares**: Missing or inadequate logging making issues hard to diagnose
- **Architectural violations**: Domain layer throwing HTTP exceptions (breaks Clean Architecture)

This skill provides automated, repeatable validation to catch error handling issues before deployment.

**Unlike general code review, this skill:**
- Uses **Context7 MCP** to fetch latest Clean Architecture and DDD error handling patterns
- Validates **layer-appropriate error types** that static analysis tools miss
- Enforces **error propagation contracts** across system boundaries
- Checks **HTTP status code correctness** for different error types
- Verifies **frontend error UX** meets usability standards
- Works across **all frameworks** and **all domains**

---

## 2. When to Use This Skill

### Mandatory Invocation Scenarios

**ALWAYS invoke this skill when:**

1. **After Feature Implementation** - Validate error handling for new features across all layers
2. **Pre-Deployment** - Quality gate before production release
3. **Error Handling Changes** - Any modification to error classes, exception handlers, or error responses
4. **Integration Testing** - Validate end-to-end error workflows
5. **Periodic Audits** - Regular error handling reviews (weekly/sprint-based)

### Specific Trigger Conditions

Invoke immediately when code includes:

**Domain Layer:**
- Custom error classes (e.g., `DomainViolationError`, `ValidationError`, `BusinessRuleError`)
- Domain entity validation logic
- Domain invariant enforcement

**Backend/API Layer:**
- Exception handlers (`@app.exception_handler`, `try/except` blocks)
- HTTP exception raising (`HTTPException`, `raise BadRequest`)
- Error response formatting
- Status code mapping logic

**Frontend Layer:**
- API error handling (`catch` blocks, `.error` handlers)
- Error state management
- User-facing error messages
- Error boundary components

**Observability:**
- Logging statements (`logger.error`, `console.error`)
- Error tracking integration (Sentry, DataDog, etc.)

### User-Requested Scenarios

Users may explicitly request:
- "Validate my error handling across all layers"
- "Review error propagation before deployment"
- "Check if error messages are user-friendly"
- "Audit error handling for security issues"

---

## 3. Inputs

### Required Inputs

| Input | Type | Description | Example |
|-------|------|-------------|---------|
| `file_paths` | `string[]` | Absolute paths to files to validate | `["/domain/task.py", "/backend/api/tasks.py", "/frontend/components/TaskForm.tsx"]` |
| `validation_scope` | `"full" \| "domain-only" \| "backend-only" \| "frontend-only"` | Scope of validation | `"full"` |

### Optional Inputs

| Input | Type | Default | Description |
|-------|------|---------|-------------|
| `framework` | `string` | `"auto-detect"` | Backend framework (FastAPI, Flask, Express, Next.js API) |
| `severity_threshold` | `"low" \| "medium" \| "high" \| "critical"` | `"medium"` | Minimum severity to report |
| `include_recommendations` | `boolean` | `true` | Include non-blocking improvement suggestions |

### Input Validation Rules

- `file_paths` must be non-empty array
- Each path must be absolute (not relative)
- Files must exist and be readable
- `validation_scope` must be one of the four defined values

---

## 4. Outputs

### Validation Report Structure

```typescript
interface ValidationReport {
  summary: {
    total_files_scanned: number;
    total_issues_found: number;
    critical_issues: number;
    high_severity_issues: number;
    medium_severity_issues: number;
    low_severity_issues: number;
    error_score: number; // 0-100
    validation_timestamp: string;
    frameworks_detected: string[];
  };

  critical_issues: ErrorIssue[];
  high_severity_issues: ErrorIssue[];
  medium_severity_issues: ErrorIssue[];
  low_severity_issues: ErrorIssue[];
  recommendations: Recommendation[];
  files_scanned: FileValidationResult[];
}

interface ErrorIssue {
  severity: "critical" | "high" | "medium" | "low";
  category: "domain" | "backend" | "frontend" | "observability" | "security";
  issue_type: string;
  file: string;
  line_number: number;
  description: string;
  impact: string;
  remediation: string;
  code_example: string;
}
```

### Error Score Calculation

```
Error Score = 100 - (
  (critical_issues * 25) +
  (high_severity_issues * 10) +
  (medium_severity_issues * 3) +
  (low_severity_issues * 1)
)

Blocking Threshold: < 70 (deployment blocked)
Warning Threshold: 70-85 (review required)
Acceptable: > 85
```

---

## 5. Workflow

### Step 1: Context7 Integration - Fetch Latest Error Handling Best Practices

**Purpose**: Ensure validation uses current Clean Architecture and DDD error handling patterns.

**Actions**:

1. **Query Context7 MCP for Error Handling Documentation**:
   ```typescript
   const context7Queries = [
     {
       libraryId: "/ardalis/cleanarchitecture",
       query: "error handling exception propagation across layers domain errors validation errors HTTP status code mapping"
     },
     {
       libraryId: "/sairyss/domain-driven-hexagon",
       query: "domain errors exception handling error propagation across layers application errors infrastructure errors Result type"
     },
     {
       libraryId: "/websites/fastapi_tiangolo",
       query: "exception handlers HTTPException status codes error responses validation errors custom error handling RequestValidationError"
     },
     {
       libraryId: "/expressjs/express",
       query: "error handling middleware error propagation HTTP status codes error responses"
     }
   ];
   ```

2. **Extract Current Patterns from Documentation**
3. **Build Reference Pattern Database**

**Key Patterns to Extract:**

**Domain Layer (Clean Architecture / DDD):**
- ✅ Custom error classes for business rules (`DomainViolationError`, `BusinessRuleError`)
- ✅ Validation errors for data validation (`ValidationError`)
- ✅ Result types for expected failures (`Result<T, Error>`)
- ❌ NO HTTP exceptions in domain layer (architecture violation)
- ❌ NO status codes in domain errors (infrastructure concern)

**Backend/API Layer (Infrastructure):**
- ✅ Exception handlers mapping domain errors to HTTP status codes
- ✅ Error response formatting (JSON, consistent structure)
- ✅ Logging at error boundaries
- ❌ NO stack traces in error responses (security issue)
- ❌ NO internal implementation details exposed

**Frontend Layer:**
- ✅ Error state management
- ✅ User-friendly error messages
- ✅ Error boundary components (React)
- ❌ NO raw error objects displayed to users
- ❌ NO technical jargon in user messages

---

### Step 2: Pattern Detection - Scan Code for Error Handling

**Domain Layer Patterns:**

**Expected (✅):**
```python
# Custom domain error classes
class DomainViolationError(Exception):
    """Raised when domain invariant is violated"""
    pass

class TaskTitleTooLongError(DomainViolationError):
    """Raised when task title exceeds maximum length"""
    def __init__(self, title_length: int, max_length: int):
        self.title_length = title_length
        self.max_length = max_length
        super().__init__(f"Title length {title_length} exceeds maximum {max_length}")

# Domain entity validation
class Task:
    MAX_TITLE_LENGTH = 200

    def __init__(self, title: str):
        if len(title) > self.MAX_TITLE_LENGTH:
            raise TaskTitleTooLongError(len(title), self.MAX_TITLE_LENGTH)
        self.title = title
```

**Anti-Patterns (❌):**
```python
# WRONG: HTTP exception in domain layer
from fastapi import HTTPException

class Task:
    def __init__(self, title: str):
        if not title:
            raise HTTPException(status_code=400, detail="Title required")  # ❌ Architecture violation
```

**Backend Layer Patterns:**

**Expected (✅):**
```python
# FastAPI exception handler mapping domain errors to HTTP status codes
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI()

@app.exception_handler(TaskTitleTooLongError)
async def task_title_too_long_handler(request: Request, exc: TaskTitleTooLongError):
    logger.error(f"Task title validation failed: {exc}")  # ✅ Logging
    return JSONResponse(
        status_code=400,  # ✅ Correct status code for validation error
        content={
            "error": "validation_error",
            "message": f"Task title must be {exc.max_length} characters or less",  # ✅ User-friendly
            "field": "title"
        }
    )

@app.exception_handler(DomainViolationError)
async def domain_violation_handler(request: Request, exc: DomainViolationError):
    logger.error(f"Domain violation: {exc}", exc_info=True)  # ✅ Log with stack trace
    return JSONResponse(
        status_code=400,
        content={
            "error": "domain_error",
            "message": "Invalid request. Please check your input."  # ✅ Generic user message
        }
    )
```

**Anti-Patterns (❌):**
```python
# WRONG: Exposing stack trace to user
@app.exception_handler(Exception)
async def generic_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"error": str(exc), "traceback": traceback.format_exc()}  # ❌ Security issue
    )
```

**Frontend Layer Patterns:**

**Expected (✅):**
```typescript
// React component with error handling
async function handleCreateTask(title: string) {
  try {
    const response = await fetch('/api/tasks', {
      method: 'POST',
      body: JSON.stringify({ title })
    });

    if (!response.ok) {
      const errorData = await response.json();

      // ✅ User-friendly error message
      if (response.status === 400 && errorData.field === 'title') {
        setError(`Task title ${errorData.message}`);
      } else {
        setError('Failed to create task. Please try again.');
      }
      return;
    }

    const task = await response.json();
    setSuccess(`Task "${task.title}" created successfully!`);
  } catch (error) {
    // ✅ Generic network error message
    console.error('Network error:', error);  // ✅ Log for debugging
    setError('Network error. Please check your connection and try again.');
  }
}
```

**Anti-Patterns (❌):**
```typescript
// WRONG: Displaying raw error to user
async function handleCreateTask(title: string) {
  try {
    const response = await fetch('/api/tasks', { method: 'POST', body: JSON.stringify({ title }) });
    const task = await response.json();
  } catch (error) {
    alert(error.toString());  // ❌ Shows "TypeError: Failed to fetch" to user
  }
}
```

---

### Step 3: Security Validation - Analyze Error Exposure

**Validation Categories:**

1. **Stack Trace Exposure**
   - ✅ Stack traces logged server-side only
   - ❌ Stack traces in API error responses
   - ❌ Stack traces displayed to users

2. **Internal Details Exposure**
   - ✅ Generic user-facing messages
   - ❌ Database column names in errors
   - ❌ File paths or internal IDs exposed
   - ❌ SQL queries or ORM errors exposed

3. **Sensitive Data Exposure**
   - ✅ Error messages don't leak user data
   - ❌ Passwords, tokens, or credentials in logs
   - ❌ PII in error responses

---

### Step 4: HTTP Status Code Mapping Validation

**Correct Status Code Mapping:**

| Error Type | HTTP Status | Example |
|------------|-------------|---------|
| **Validation Error** | 400 Bad Request | Title too long, invalid email format |
| **Authentication Required** | 401 Unauthorized | Missing or invalid auth token |
| **Permission Denied** | 403 Forbidden | User lacks permission to delete task |
| **Resource Not Found** | 404 Not Found | Task ID doesn't exist |
| **Conflict** | 409 Conflict | Email already registered |
| **Validation Failure** | 422 Unprocessable Entity | Invalid JSON structure (FastAPI default) |
| **Server Error** | 500 Internal Server Error | Database connection failed, unhandled exception |

**Validation Rules:**
- Domain validation errors (e.g., title too long) → 400
- Business rule violations (e.g., can't delete completed task) → 400
- Authentication failures → 401
- Authorization failures → 403
- Entity not found → 404
- Duplicate entity → 409
- Unexpected errors → 500

---

### Step 5: Observability Validation

**Logging Requirements:**

1. **Domain Layer**
   - ✅ Log domain violations at WARN level
   - ✅ Include context (entity ID, violating value)

2. **Backend Layer**
   - ✅ Log all errors at ERROR level
   - ✅ Include request context (user ID, endpoint, method)
   - ✅ Log stack traces for unexpected errors
   - ❌ Do NOT log sensitive data (passwords, tokens)

3. **Frontend Layer**
   - ✅ Log errors to console (development)
   - ✅ Send critical errors to error tracking (production)
   - ❌ Do NOT log sensitive user data

---

### Step 6: Generate Report

**Markdown Report Example**:

```markdown
# Error Propagation Validation Report

**Error Score**: 82/100 ⚠️

## Summary
- Critical Issues: 0
- High Severity: 3
- Medium Severity: 5
- Low Severity: 2

## High Severity Issues

### 🔴 Stack Trace Exposed in API Response
**File**: `src/backend/api/tasks.py:45`
**Category**: Security
**Impact**: Exposes internal implementation details and file paths to users

**Current Code**:
```python
@app.exception_handler(Exception)
async def generic_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"error": str(exc), "traceback": traceback.format_exc()}
    )
```

**Remediation**:
```python
@app.exception_handler(Exception)
async def generic_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)  # Log with stack trace
    return JSONResponse(
        status_code=500,
        content={"error": "internal_server_error", "message": "An unexpected error occurred. Please try again later."}
    )
```

---

### 🔴 HTTP Exception in Domain Layer
**File**: `src/domain/task.py:23`
**Category**: Architecture
**Impact**: Violates Clean Architecture - domain layer coupled to HTTP infrastructure

**Current Code**:
```python
from fastapi import HTTPException

class Task:
    def __init__(self, title: str):
        if not title:
            raise HTTPException(status_code=400, detail="Title required")
```

**Remediation**:
```python
class TaskValidationError(DomainViolationError):
    """Raised when task data is invalid"""
    pass

class Task:
    def __init__(self, title: str):
        if not title:
            raise TaskValidationError("Title is required")
```

Then map to HTTP in backend layer:
```python
@app.exception_handler(TaskValidationError)
async def task_validation_handler(request: Request, exc: TaskValidationError):
    return JSONResponse(status_code=400, content={"error": str(exc)})
```

---

### 🔴 Missing Error Handling in Frontend
**File**: `src/frontend/components/TaskForm.tsx:67`
**Category**: User Experience
**Impact**: Users see generic "Failed to fetch" errors instead of helpful messages

**Current Code**:
```typescript
async function handleSubmit() {
  const response = await fetch('/api/tasks', { method: 'POST', body: JSON.stringify(formData) });
  const task = await response.json();
  // No error checking
}
```

**Remediation**:
```typescript
async function handleSubmit() {
  try {
    const response = await fetch('/api/tasks', {
      method: 'POST',
      body: JSON.stringify(formData)
    });

    if (!response.ok) {
      const errorData = await response.json();
      setError(errorData.message || 'Failed to create task. Please try again.');
      return;
    }

    const task = await response.json();
    setSuccess(`Task "${task.title}" created successfully!`);
  } catch (error) {
    console.error('Network error:', error);
    setError('Network error. Please check your connection.');
  }
}
```

## Deployment Recommendation
⚠️ **REVIEW REQUIRED** - Address 3 high-severity issues before deployment
```

---

## 6. Constraints & Limitations

**This skill validates:**
- Error classification and custom error classes
- Error propagation across layers
- HTTP status code mapping correctness
- Frontend error handling and UX
- Error logging and observability
- Security (stack trace exposure, sensitive data)

**This skill does NOT validate:**
- Runtime error scenarios
- Network failure handling (retries, timeouts)
- Rate limiting or throttling
- Error recovery strategies (circuit breakers)
- Third-party API error handling

---

## 7. Reusability & Extensibility

**Cross-Project Reusability: Extremely High**

Works across:
- **Any backend framework**: FastAPI, Flask, Django, Express, Fastify, Hono, Next.js API Routes
- **Any frontend framework**: React, Vue, Svelte, Angular, Solid, Next.js
- **Any domain**: Todo, E-commerce, Healthcare, SaaS, FinTech
- **Any error taxonomy**: Custom domain errors, validation errors, business rule violations

**CI/CD Integration Example**:
```bash
claude-code skill validate-error-propagation \
  --files "domain/**/*.py,backend/**/*.py,frontend/**/*.tsx" \
  --validation-scope full \
  --severity-threshold high \
  --output-format json > error-report.json

SCORE=$(jq '.summary.error_score' error-report.json)
if [ $SCORE -lt 70 ]; then
  echo "❌ Error handling score too low: $SCORE/100"
  exit 1
fi
```

---

## 8. Integration Points

**Agent Integration**: Owned by `integration-orchestrator` (Operational Agent)

**Blocking Authority**:
- Integration Orchestrator has **YES** blocking authority for critical error handling violations
- If `critical_issues.length > 0`, Integration Orchestrator **MUST** block work
- High-severity issues trigger **WARN** (user discretion)

**Multi-Agent Coordination**:
- **Domain Guardian**: Integration Orchestrator validates that domain errors are domain-specific (no HTTP coupling)
- **Backend Architect**: Integration Orchestrator validates error mapping to HTTP status codes
- **Frontend Architect**: Integration Orchestrator validates user-facing error messages and error handling
- **Error & Reliability Architect**: Integration Orchestrator uses error taxonomy defined by Error Architect

---

## Appendix: Pattern Reference

### Error Anti-Patterns (Blocking)

| Pattern | Severity | Remediation |
|---------|----------|-------------|
| Stack trace in API response | Critical | Log server-side; return generic message |
| HTTP exception in domain layer | Critical | Use custom domain errors; map in backend |
| Missing error handling in API calls | High | Add try/catch with user-friendly messages |
| Exposing internal details | High | Return generic messages; log details server-side |
| Wrong HTTP status codes | Medium | Map domain errors correctly (400/403/404/500) |
| Missing error logging | Medium | Add logger.error() at error boundaries |

### Current Best Practices

| Pattern | Purpose |
|---------|---------|
| Custom domain error classes | Domain-specific validation and business rules |
| Exception handlers in backend | Map domain errors to HTTP status codes |
| Result types (Ok/Err) | Explicit success/failure without exceptions |
| User-friendly frontend messages | Improve UX; avoid technical jargon |
| Comprehensive logging | Debugging and observability |

---

**End of Skill Definition**
