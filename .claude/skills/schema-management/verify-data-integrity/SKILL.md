---
name: verify-data-integrity
description: Validate data consistency and integrity after schema changes or migrations
version: 1.0.0
agent: data-schema-guardian
reusability: high
---

# Verify Data Integrity

## Purpose

Validate that database data remains consistent and intact after schema changes, migrations, or rollbacks, detecting orphaned records, constraint violations, and data corruption.

## When to Use

- After executing migrations
- After migration rollbacks
- Before deploying to production
- During data recovery operations

## Inputs

- **Database connection** (to query data)
- **Schema definition** (current tables and constraints)
- **Expected integrity rules** (domain invariants)

## Outputs

- **Data integrity report** (✅ valid, ❌ violations)
- **Orphaned records detection**
- **Constraint violation details**
- **Data corruption assessment**

## Integrity Validation Workflow

### 1. Referential Integrity Checks

**Verify Foreign Key Relationships:**

```sql
-- Check for orphaned tasks (user_id references non-existent user)
SELECT COUNT(*) FROM tasks t
LEFT JOIN users u ON t.user_id = u.id
WHERE u.id IS NULL;

-- Should return 0 (no orphaned records)
```

**Validation Template:**

```python
def check_referential_integrity(table: str, fk_column: str, ref_table: str):
    """Check for orphaned records violating foreign key."""
    query = f"""
        SELECT COUNT(*) as orphan_count
        FROM {table} t
        LEFT JOIN {ref_table} r ON t.{fk_column} = r.id
        WHERE r.id IS NULL
    """

    result = db.execute(query).scalar()

    if result > 0:
        return IntegrityViolation(
            type="orphaned_records",
            table=table,
            count=result,
            severity="CRITICAL",
            fix=f"Delete orphaned records or restore referenced {ref_table}"
        )

    return IntegrityValid()
```

### 2. Uniqueness Constraint Validation

**Check for Duplicate Values:**

```sql
-- Check for duplicate task IDs (should be PRIMARY KEY)
SELECT id, COUNT(*) as count
FROM tasks
GROUP BY id
HAVING COUNT(*) > 1;

-- Should return 0 rows (no duplicates)
```

**Validation:**

```python
def check_uniqueness(table: str, column: str):
    """Verify uniqueness constraint."""
    query = f"""
        SELECT {column}, COUNT(*) as count
        FROM {table}
        GROUP BY {column}
        HAVING COUNT(*) > 1
    """

    duplicates = db.execute(query).fetchall()

    if duplicates:
        return IntegrityViolation(
            type="duplicate_values",
            table=table,
            column=column,
            duplicates=[(row[0], row[1]) for row in duplicates],
            severity="CRITICAL"
        )

    return IntegrityValid()
```

### 3. NULL Constraint Validation

**Check for NULL Values in NOT NULL Columns:**

```sql
-- Check for NULL titles (NOT NULL constraint)
SELECT COUNT(*) FROM tasks WHERE title IS NULL;

-- Should return 0 (no NULL values)
```

**Validation:**

```python
def check_not_null_constraints(table: str, schema: dict):
    """Verify no NULL values in NOT NULL columns."""
    violations = []

    for column, spec in schema.items():
        if not spec.nullable:
            query = f"SELECT COUNT(*) FROM {table} WHERE {column} IS NULL"
            null_count = db.execute(query).scalar()

            if null_count > 0:
                violations.append(IntegrityViolation(
                    type="null_value",
                    table=table,
                    column=column,
                    count=null_count,
                    severity="CRITICAL"
                ))

    return violations
```

### 4. Check Constraint Validation

**Verify CHECK Constraints:**

```sql
-- Check for invalid priority values (should be 'low', 'medium', 'high')
SELECT COUNT(*) FROM tasks
WHERE priority NOT IN ('low', 'medium', 'high');

-- Should return 0 (all values valid)
```

**Validation:**

```python
def check_enum_constraints(table: str, column: str, valid_values: List[str]):
    """Verify enum/CHECK constraint values."""
    placeholders = ', '.join([f"'{v}'" for v in valid_values])
    query = f"""
        SELECT COUNT(*) FROM {table}
        WHERE {column} NOT IN ({placeholders})
    """

    invalid_count = db.execute(query).scalar()

    if invalid_count > 0:
        return IntegrityViolation(
            type="invalid_enum_value",
            table=table,
            column=column,
            count=invalid_count,
            severity="HIGH"
        )

    return IntegrityValid()
```

### 5. Data Type Consistency

**Check for Data Type Violations:**

```python
def check_data_type_consistency(table: str, column: str, expected_type: str):
    """Verify data conforms to expected type."""
    # Example: Check dates are valid
    if expected_type == "datetime":
        query = f"""
            SELECT COUNT(*) FROM {table}
            WHERE {column} IS NOT NULL
            AND NOT {column}::text ~ '^\d{{4}}-\d{{2}}-\d{{2}}'
        """
        invalid_count = db.execute(query).scalar()

        if invalid_count > 0:
            return IntegrityViolation(
                type="invalid_date_format",
                table=table,
                column=column,
                count=invalid_count
            )

    return IntegrityValid()
```

### 6. Row Count Verification

**Verify Expected Row Counts:**

```python
def verify_row_counts(pre_migration_counts: dict, post_migration_counts: dict):
    """Ensure row counts match expectations after migration."""
    mismatches = []

    for table, expected_count in pre_migration_counts.items():
        actual_count = post_migration_counts.get(table, 0)

        if expected_count != actual_count:
            mismatches.append({
                "table": table,
                "expected": expected_count,
                "actual": actual_count,
                "delta": actual_count - expected_count
            })

    return mismatches
```

## Data Integrity Report

**Report Template:**

```markdown
# Data Integrity Validation Report

**Date:** 2025-01-01 15:00:00
**Migration:** Add priority column (revision: a1b2c3d4e5f6)
**Status:** ✅ VALID

## Referential Integrity (5 checks)

✅ tasks.user_id → users.id (0 orphaned records)
✅ subtasks.task_id → tasks.id (0 orphaned records)
✅ task_tags.task_id → tasks.id (0 orphaned records)
✅ task_tags.tag_id → tags.id (0 orphaned records)
✅ task_comments.task_id → tasks.id (0 orphaned records)

## Uniqueness Constraints (3 checks)

✅ tasks.id (PRIMARY KEY) - No duplicates
✅ users.email (UNIQUE) - No duplicates
✅ tags.name (UNIQUE) - No duplicates

## NOT NULL Constraints (8 checks)

✅ tasks.title - No NULL values
✅ tasks.status - No NULL values
✅ tasks.priority - No NULL values
✅ tasks.user_id - No NULL values
✅ tasks.created_at - No NULL values
✅ tasks.updated_at - No NULL values
✅ users.email - No NULL values
✅ users.created_at - No NULL values

## CHECK Constraints (2 checks)

✅ tasks.status IN ('pending', 'complete') - All values valid
✅ tasks.priority IN ('low', 'medium', 'high') - All values valid

## Row Count Verification

| Table | Before Migration | After Migration | Delta |
|-------|------------------|-----------------|-------|
| tasks | 1,234 | 1,234 | 0 ✅ |
| users | 456 | 456 | 0 ✅ |
| tags | 89 | 89 | 0 ✅ |

**Total Rows:** 1,779 (all preserved)

---

**Overall Status:** ✅ DATA INTEGRITY VERIFIED
```

**Violations Report (if issues found):**

```markdown
# Data Integrity Validation Report

**Status:** ❌ VIOLATIONS DETECTED

## ❌ Critical Violations (2)

### 1. Orphaned Records: tasks.user_id
- **Count:** 15 tasks
- **Issue:** user_id references deleted users
- **Severity:** CRITICAL
- **Fix:**
  ```sql
  -- Option 1: Delete orphaned tasks
  DELETE FROM tasks WHERE user_id NOT IN (SELECT id FROM users);

  -- Option 2: Reassign to default user
  UPDATE tasks SET user_id = 'default-user-id'
  WHERE user_id NOT IN (SELECT id FROM users);
  ```

### 2. NULL Values: tasks.priority
- **Count:** 342 tasks
- **Issue:** NULL values in NOT NULL column
- **Severity:** CRITICAL
- **Fix:**
  ```sql
  -- Backfill with default value
  UPDATE tasks SET priority = 'medium' WHERE priority IS NULL;
  ```

## Remediation Required

1. Fix orphaned task records (15 rows)
2. Backfill NULL priority values (342 rows)
3. Re-run integrity validation
4. Investigate why violations occurred
```

## Constraints

- **MUST** validate after every migration
- **MUST** detect all referential integrity violations
- **DO NOT** auto-fix violations without approval
- **MUST** report all data inconsistencies

## Reusability

**Database-Agnostic:** Works with any SQL database

**Domain-Agnostic:** Validates integrity for any data model

**Applicable To:**
- Post-migration validation
- Data recovery verification
- Production health checks
- Pre-deployment validation

## Integration Points

**Triggered After:**
- Migration execution
- Migration rollback
- Data import operations
- Production incidents

**Requires:**
- Database connection
- Schema definition
- Expected constraint rules

**Outputs To:**
- Data integrity report
- Violation details with severity
- Remediation SQL scripts
