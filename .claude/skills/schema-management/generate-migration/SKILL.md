---
name: generate-migration
description: Generate database migrations from domain model changes using Alembic best practices
version: 1.0.0
agent: data-schema-guardian
reusability: high
---

# Generate Migration

## Purpose

Generate safe, reversible database migration files from domain model changes using Alembic, ensuring schema evolution aligns with domain requirements.

## When to Use

- After domain model changes (new entities, attributes, relationships)
- When domain invariants require schema constraints
- For data model refactoring
- Before backend implementation of domain changes

## Inputs

- **Domain model changes** (new entities, fields, relationships)
- **Current database schema** (existing tables, columns, constraints)
- **Domain invariants** (required fields, uniqueness, foreign keys)
- **Migration message** (description of change)

## Outputs

- **Migration file** (`migrations/versions/XXX_<description>.py`)
- **Migration validation report** (schema ↔ domain alignment)
- **Rollback strategy** (downgrade function)

## Migration Generation Workflow

### 1. Analyze Domain Model Changes

**Identify Schema Impact:**

```python
# Domain model change example
class Task:
    """Task entity with new priority field."""
    title: str
    description: str
    status: TaskStatus
    priority: Priority  # NEW FIELD - requires migration

    def __init__(self, title: str, description: str, priority: Priority):
        if priority is None:
            raise DomainViolationError("Priority required")  # Constraint
        # ...
```

**Schema Impact Analysis:**
- New field: `priority` (string/enum)
- Constraint: NOT NULL (domain requires it)
- Migration needed: ALTER TABLE tasks ADD COLUMN priority

### 2. Generate Migration Using Alembic

**Autogenerate Migration:**

```bash
# Generate migration with autogenerate
alembic revision --autogenerate -m "Add priority field to tasks"

# Creates: migrations/versions/001_add_priority_field_to_tasks.py
```

**Manual Migration (when autogenerate insufficient):**

```bash
# Generate empty migration template
alembic revision -m "Add priority field to tasks"

# Edit generated file to add schema operations
```

### 3. Review and Edit Generated Migration

**Generated Migration File Structure:**

```python
"""Add priority field to tasks

Revision ID: a1b2c3d4e5f6
Revises: prev_revision_id
Create Date: 2025-01-01 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# Revision identifiers
revision = 'a1b2c3d4e5f6'
down_revision = 'prev_revision_id'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Schema upgrade: Add priority column."""
    # Add priority column with NOT NULL constraint
    op.add_column(
        'tasks',
        sa.Column(
            'priority',
            sa.String(length=10),
            nullable=False,
            server_default='medium'  # Safe default for existing rows
        )
    )

    # Remove server_default after backfill (safe for new rows)
    op.alter_column(
        'tasks',
        'priority',
        server_default=None
    )


def downgrade() -> None:
    """Schema downgrade: Remove priority column."""
    op.drop_column('tasks', 'priority')
```

### 4. Handle Existing Data (Backfill Strategy)

**For Non-Nullable Columns on Existing Tables:**

```python
def upgrade() -> None:
    """Add priority with safe backfill."""
    # Step 1: Add column as nullable
    op.add_column(
        'tasks',
        sa.Column('priority', sa.String(length=10), nullable=True)
    )

    # Step 2: Backfill existing rows
    op.execute(
        "UPDATE tasks SET priority = 'medium' WHERE priority IS NULL"
    )

    # Step 3: Make column NOT NULL
    op.alter_column(
        'tasks',
        'priority',
        nullable=False
    )
```

### 5. Add Schema Constraints (From Domain Invariants)

**Translate Domain Constraints to SQL:**

```python
# Domain invariant: Priority must be 'low', 'medium', or 'high'
class Priority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

# Migration: Add CHECK constraint
def upgrade() -> None:
    op.add_column('tasks', sa.Column('priority', sa.String(10), nullable=False))

    # Add CHECK constraint for enum values
    op.create_check_constraint(
        'tasks_priority_check',
        'tasks',
        "priority IN ('low', 'medium', 'high')"
    )


def downgrade() -> None:
    op.drop_constraint('tasks_priority_check', 'tasks', type_='check')
    op.drop_column('tasks', 'priority')
```

### 6. Handle Relationships (Foreign Keys)

**Domain Relationship → Database Foreign Key:**

```python
# Domain: Task belongs to User
class Task:
    user_id: str  # Reference to User entity

# Migration: Add foreign key constraint
def upgrade() -> None:
    op.add_column(
        'tasks',
        sa.Column('user_id', sa.String(36), nullable=False)
    )

    # Add foreign key constraint
    op.create_foreign_key(
        'fk_tasks_user_id',
        'tasks',      # Source table
        'users',      # Target table
        ['user_id'],  # Source column
        ['id'],       # Target column
        ondelete='CASCADE'  # Delete tasks when user deleted
    )


def downgrade() -> None:
    op.drop_constraint('fk_tasks_user_id', 'tasks', type_='foreignkey')
    op.drop_column('tasks', 'user_id')
```

## Migration Validation Checklist

**Before Finalizing Migration:**

- [ ] **Reversible:** Downgrade function correctly undoes upgrade
- [ ] **Safe for Production:** Handles existing data (backfill if needed)
- [ ] **Constraint Alignment:** Schema constraints match domain invariants
- [ ] **No Data Loss:** Migration preserves existing data
- [ ] **Idempotent:** Can run multiple times safely (with checks)
- [ ] **Performance Aware:** Large table migrations use batching
- [ ] **Tested:** Migration tested on copy of production data

## Migration Patterns

### Pattern 1: Add Column (Safe)

```python
def upgrade():
    op.add_column('tasks', sa.Column('new_field', sa.String(50), nullable=True))

def downgrade():
    op.drop_column('tasks', 'new_field')
```

### Pattern 2: Rename Column (Requires Data Migration)

```python
def upgrade():
    # Don't use alter_column for rename - use two-step process
    op.add_column('tasks', sa.Column('new_name', sa.String(100)))
    op.execute("UPDATE tasks SET new_name = old_name")
    op.drop_column('tasks', 'old_name')

def downgrade():
    op.add_column('tasks', sa.Column('old_name', sa.String(100)))
    op.execute("UPDATE tasks SET old_name = new_name")
    op.drop_column('tasks', 'new_name')
```

### Pattern 3: Change Column Type (Risky)

```python
def upgrade():
    # PostgreSQL-specific type conversion
    op.execute("ALTER TABLE tasks ALTER COLUMN priority TYPE VARCHAR(20)")

def downgrade():
    op.execute("ALTER TABLE tasks ALTER COLUMN priority TYPE VARCHAR(10)")
```

### Pattern 4: Add Index (Performance)

```python
def upgrade():
    op.create_index('idx_tasks_status', 'tasks', ['status'])

def downgrade():
    op.drop_index('idx_tasks_status', table_name='tasks')
```

## Constraints

- **MUST** provide reversible downgrade function
- **MUST** handle existing data safely
- **MUST** align schema constraints with domain invariants
- **DO NOT** delete data in migrations (archive instead)
- **DO NOT** run migrations automatically in production (require approval)

## Reusability

**Database-Agnostic (via Alembic):**
- PostgreSQL
- MySQL
- SQLite
- SQL Server

**Domain-Agnostic:** Works for any domain model requiring persistence

**Evolution:**
- Phase 1: Manual migration review and execution
- Phase 2: Automated migration testing
- Phase 3: Blue-green deployment migrations
- Phase 4: Online schema migrations (zero downtime)

## Integration Points

**Triggered After:**
- Domain Guardian defines new entity/field
- Domain model changes requiring persistence

**Requires:**
- Alembic configuration (`alembic.ini`)
- Database connection
- Domain model definitions

**Outputs To:**
- `migrations/versions/` directory
- Migration execution logs
- Schema validation report
