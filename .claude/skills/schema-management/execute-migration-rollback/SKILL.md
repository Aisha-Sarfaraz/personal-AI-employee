---
name: execute-migration-rollback
description: Safely rollback database migrations with data preservation and validation
version: 1.0.0
agent: data-schema-guardian
reusability: high
---

# Execute Migration Rollback

## Purpose

Safely rollback database migrations when issues are detected, preserving data integrity and providing clear rollback strategies.

## When to Use

- Migration fails during execution
- Post-migration issues detected in production
- Testing migration reversibility
- Recovering from schema errors

## Inputs

- **Target revision** (which migration to rollback to)
- **Current database state**
- **Rollback reason** (why rolling back)
- **Data backup confirmation**

## Outputs

- **Rollback execution log**
- **Data preservation report** (what data was affected)
- **Schema validation** (schema state after rollback)
- **Post-rollback checklist**

## Rollback Workflow

### 1. Pre-Rollback Validation

**Safety Checks Before Rolling Back:**

```python
def pre_rollback_validation(target_revision: str) -> bool:
    """Validate it's safe to rollback to target revision."""

    # Check 1: Target revision exists
    if not revision_exists(target_revision):
        raise RollbackError(f"Revision {target_revision} not found")

    # Check 2: Downgrade path exists
    current = get_current_revision()
    path = get_downgrade_path(current, target_revision)
    if not path:
        raise RollbackError(f"No downgrade path from {current} to {target_revision}")

    # Check 3: Backup recommended
    if data_will_be_lost(path):
        print("⚠️  WARNING: Rollback may cause data loss")
        print("   Affected tables:", get_affected_tables(path))
        confirm = input("   Create backup first? (y/n): ")
        if confirm.lower() == 'y':
            create_backup()

    return True
```

### 2. Backup Strategy

**Before Rolling Back:**

```bash
# Create database dump
pg_dump -U postgres -d myapp_db -f backup_before_rollback_$(date +%Y%m%d_%H%M%S).sql

# Or use Alembic stamp to mark current version
alembic stamp head
```

**Document Current State:**

```python
def document_current_state():
    """Record current schema state before rollback."""
    state = {
        "current_revision": get_current_revision(),
        "timestamp": datetime.now().isoformat(),
        "table_counts": get_row_counts_all_tables(),
        "schema_checksum": compute_schema_checksum()
    }

    with open(f"rollback_state_{state['timestamp']}.json", "w") as f:
        json.dump(state, f, indent=2)

    return state
```

### 3. Execute Rollback

**Alembic Downgrade Commands:**

```bash
# Rollback one revision
alembic downgrade -1

# Rollback to specific revision
alembic downgrade a1b2c3d4e5f6

# Rollback to base (empty database)
alembic downgrade base

# Rollback with SQL output (dry-run)
alembic downgrade -1 --sql
```

**Programmatic Rollback:**

```python
from alembic import command
from alembic.config import Config

def execute_rollback(target_revision: str):
    """Execute migration rollback with logging."""
    config = Config("alembic.ini")

    try:
        # Log rollback start
        logger.info(f"Starting rollback to {target_revision}")

        # Execute downgrade
        command.downgrade(config, target_revision)

        # Verify rollback success
        current = command.current(config)
        if current == target_revision:
            logger.info("✅ Rollback successful")
            return True
        else:
            logger.error(f"❌ Rollback failed: at {current}, expected {target_revision}")
            return False

    except Exception as e:
        logger.error(f"❌ Rollback error: {e}")
        raise RollbackError(f"Migration rollback failed: {e}")
```

### 4. Data Preservation During Rollback

**Strategies to Minimize Data Loss:**

#### Strategy 1: Archive Instead of Delete

```python
# DON'T: Drop column (data lost forever)
def downgrade():
    op.drop_column('tasks', 'priority')

# DO: Archive column to backup table
def downgrade():
    # Create archive table
    op.create_table(
        'tasks_archived_priority',
        sa.Column('task_id', sa.String(36)),
        sa.Column('priority', sa.String(10)),
        sa.Column('archived_at', sa.DateTime, default=datetime.now)
    )

    # Copy data to archive
    op.execute("""
        INSERT INTO tasks_archived_priority (task_id, priority)
        SELECT id, priority FROM tasks
    """)

    # Now safe to drop
    op.drop_column('tasks', 'priority')
```

#### Strategy 2: Conditional Data Preservation

```python
def downgrade():
    """Rollback with data preservation option."""
    # Check if data exists before deleting
    result = op.get_bind().execute(
        "SELECT COUNT(*) FROM tasks WHERE priority IS NOT NULL"
    )
    count = result.scalar()

    if count > 0:
        print(f"⚠️  {count} tasks have priority data")
        preserve = input("Preserve in archive table? (y/n): ")

        if preserve.lower() == 'y':
            # Archive data before removing column
            archive_priority_data()

    op.drop_column('tasks', 'priority')
```

#### Strategy 3: Partial Rollback

```python
def downgrade():
    """Rollback schema but keep data-related changes."""
    # Rollback schema change
    op.drop_index('idx_tasks_priority')

    # Keep data (don't drop column)
    # Column remains but is no longer indexed
    # Can be removed in future migration if truly unused
```

### 5. Post-Rollback Validation

**Verify Schema State After Rollback:**

```python
def post_rollback_validation(expected_revision: str):
    """Validate database state after rollback."""

    # Check 1: Revision matches target
    current = get_current_revision()
    if current != expected_revision:
        return ValidationResult(
            passed=False,
            error=f"Revision mismatch: {current} != {expected_revision}"
        )

    # Check 2: Schema integrity
    schema_valid = validate_schema_integrity()
    if not schema_valid:
        return ValidationResult(
            passed=False,
            error="Schema integrity check failed"
        )

    # Check 3: Data integrity
    data_valid = validate_data_integrity()
    if not data_valid:
        return ValidationResult(
            passed=False,
            error="Data integrity check failed (orphaned records, etc.)"
        )

    # Check 4: Application compatibility
    app_compatible = test_application_startup()
    if not app_compatible:
        return ValidationResult(
            passed=False,
            error="Application fails to start with rolled-back schema"
        )

    return ValidationResult(passed=True)
```

### 6. Rollback Decision Matrix

**When to Rollback:**

| Scenario | Rollback? | Action |
|----------|-----------|--------|
| Migration fails midway | ✅ YES | Immediate rollback, investigate failure |
| Production errors after deploy | ✅ YES | Rollback, fix migration, redeploy |
| Performance degradation | ⚠️ MAYBE | Investigate first, rollback if critical |
| Minor bug in migration | ❌ NO | Forward fix in new migration |
| Data loss detected | ✅ YES | Immediate rollback, restore from backup |
| Migration succeeded but app fails | ✅ YES | Rollback both migration and deployment |

## Rollback Execution Report

**Report Template:**

```markdown
# Migration Rollback Report

**Date:** 2025-01-01 14:30:00
**Reason:** Post-deployment errors detected
**Executed By:** System Admin

## Rollback Details

**From Revision:** a1b2c3d4e5f6 (Add priority column)
**To Revision:** prev_revision_id (Before priority changes)
**Method:** `alembic downgrade -1`

## Pre-Rollback State

- **Current Revision:** a1b2c3d4e5f6
- **Tables Affected:** tasks
- **Row Count (tasks):** 1,234 rows
- **Backup Created:** backup_20250101_143000.sql (size: 2.5 MB)

## Rollback Execution

```bash
$ alembic downgrade -1
INFO  [alembic.runtime.migration] Context impl PostgreSQLImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running downgrade a1b2c3d4e5f6 -> prev_revision_id
INFO  [alembic.env] Archiving priority data to tasks_archived_priority
INFO  [alembic.env] Dropping column tasks.priority
INFO  [alembic.runtime.migration] Downgrade complete
```

## Post-Rollback Validation

✅ **Revision Check:** Current = prev_revision_id (expected)
✅ **Schema Integrity:** All tables and constraints valid
✅ **Data Integrity:** 1,234 rows preserved, 1,234 priority values archived
✅ **Application Test:** Application starts successfully
⚠️ **Data Archived:** Priority data moved to tasks_archived_priority table

## Data Preservation

**Archived Data:**
- Table: `tasks_archived_priority`
- Rows: 1,234
- Can be restored if needed

**Restore Command (if needed):**
```sql
-- Re-add priority column
ALTER TABLE tasks ADD COLUMN priority VARCHAR(10);

-- Restore from archive
UPDATE tasks t
SET priority = a.priority
FROM tasks_archived_priority a
WHERE t.id = a.task_id;
```

## Next Steps

1. ✅ Rollback complete
2. ⏳ Investigate original migration failure
3. ⏳ Fix migration downgrade logic
4. ⏳ Test migration in staging environment
5. ⏳ Re-deploy with fixed migration

**Status:** ROLLBACK SUCCESSFUL
```

## Constraints

- **MUST** create backup before risky rollbacks
- **MUST** validate post-rollback schema integrity
- **MUST** preserve data when possible (archive strategy)
- **DO NOT** rollback if data loss is unacceptable without backup
- **DO NOT** rollback production without incident record

## Reusability

**Database-Agnostic:** Works with Alembic-supported databases

**Applicable To:**
- Development rollbacks (frequent)
- Staging rollbacks (testing)
- Production rollbacks (emergency)

**Evolution:**
- Phase 1: Manual rollback with checklist
- Phase 2: Automated rollback on failure
- Phase 3: Blue-green migration strategies (no rollback needed)
- Phase 4: Online schema changes with zero downtime

## Integration Points

**Triggered When:**
- Migration execution fails
- Post-migration issues detected
- Testing migration reversibility

**Requires:**
- Alembic configuration
- Database backup capability
- Rollback approval (production)

**Outputs To:**
- Rollback execution log
- Data preservation report
- Post-rollback validation results
