---
name: validate-schema-alignment
description: Verify database schema aligns with domain model and enforces domain invariants
version: 1.0.0
agent: data-schema-guardian
reusability: high
---

# Validate Schema Alignment

## Purpose

Verify that database schema structure, constraints, and types correctly map to and enforce domain model requirements and invariants.

## When to Use

- After generating migrations
- Before executing migrations
- After domain model changes
- During schema audits

## Inputs

- **Domain model definitions** (entities, value objects, invariants)
- **Database schema** (current or target)
- **Migration files** (pending or executed)

## Outputs

- **Alignment validation report** (✅ aligned, ❌ misaligned)
- **Missing constraints detection**
- **Schema drift identification**
- **Remediation recommendations**

## Validation Workflow

### 1. Extract Domain Model Structure

**Parse Domain Entities:**

```python
# Domain model example
class Task:
    """Task entity."""
    id: str              # PRIMARY KEY
    title: str           # NOT NULL, MAX 200 chars
    description: str     # NULLABLE, MAX 2000 chars
    status: TaskStatus   # NOT NULL, ENUM
    priority: Priority   # NOT NULL, ENUM
    user_id: str         # NOT NULL, FOREIGN KEY -> users.id
    created_at: datetime # NOT NULL, DEFAULT now()
    updated_at: datetime # NOT NULL, DEFAULT now()

    def __init__(self, title: str, priority: Priority, user_id: str):
        if not title:
            raise DomainViolationError("Title required")  # → NOT NULL
        if len(title) > 200:
            raise DomainViolationError("Title max 200")   # → VARCHAR(200)
        if priority is None:
            raise DomainViolationError("Priority required")  # → NOT NULL
```

**Expected Schema:**

```sql
CREATE TABLE tasks (
    id VARCHAR(36) PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    description VARCHAR(2000),
    status VARCHAR(20) NOT NULL,
    priority VARCHAR(10) NOT NULL CHECK (priority IN ('low', 'medium', 'high')),
    user_id VARCHAR(36) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT now(),
    updated_at TIMESTAMP NOT NULL DEFAULT now(),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
```

### 2. Compare Domain Model to Schema

**Domain Invariants → Schema Constraints:**

| Domain Invariant | Schema Constraint | Validation |
|------------------|-------------------|------------|
| Title required | `NOT NULL` | ✅ Check column nullable=False |
| Title max 200 chars | `VARCHAR(200)` | ✅ Check column max_length=200 |
| Priority enum | `CHECK (priority IN (...))` | ✅ Check constraint exists |
| User must exist | `FOREIGN KEY → users` | ✅ Check foreign key exists |
| ID unique | `PRIMARY KEY` | ✅ Check primary key exists |

### 3. Detect Schema Drift

**Schema Drift = Database schema diverges from domain model**

```python
# Scenario: Domain field not in database
domain_fields = {"id", "title", "status", "priority"}
schema_columns = {"id", "title", "status"}
drift = domain_fields - schema_columns
# Result: {"priority"} - migration needed
```

## Alignment Validation Report

**Report Template:**

```markdown
# Schema Alignment Validation Report

**Entity:** Task
**Table:** tasks
**Status:** ⚠️ DRIFT DETECTED

## ✅ Correctly Aligned (5)

- `id` (PRIMARY KEY, VARCHAR(36), NOT NULL)
- `title` (VARCHAR(200), NOT NULL)
- `description` (VARCHAR(2000), NULL)
- `status` (VARCHAR(20), NOT NULL, CHECK constraint)
- `created_at` (TIMESTAMP, NOT NULL, DEFAULT)

## ❌ Misalignments (2)

### 1. Missing Column: `priority`
- **Domain:** priority: Priority (NOT NULL, ENUM)
- **Schema:** Column does not exist
- **Fix:** Generate migration to add column
- **Command:** `alembic revision --autogenerate -m "Add priority column"`

### 2. Missing Constraint: Foreign Key
- **Domain:** user_id references User entity
- **Schema:** Column exists but no FK constraint
- **Fix:** Add foreign key constraint

## Remediation Steps

1. Generate migration for missing `priority` column
2. Add foreign key constraint for `user_id`
3. Consider adding performance index for (user_id, status)
4. Re-run validation after migrations
```

## Constraints

- **MUST** validate all domain fields exist in schema
- **MUST** verify NOT NULL constraints match domain requirements
- **MUST** check foreign keys exist for relationships
- **DO NOT** auto-fix misalignments (generate migrations instead)

## Reusability

**ORM-Agnostic:** Works with any database schema

**Domain-Agnostic:** Validates alignment for any domain model

**Database Support:**
- PostgreSQL
- MySQL
- SQLite
- Any SQLAlchemy-supported database

## Integration Points

**Triggered After:**
- Migration generation
- Domain model changes
- Before migration execution

**Requires:**
- Domain model definitions
- Database connection (to inspect schema)
- Alembic configuration

**Outputs To:**
- Validation report
- Drift detection log
- Migration recommendations
