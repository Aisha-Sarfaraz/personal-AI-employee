---
name: aggregate-workflow-results
description: Collect and summarize results from multi-agent workflows into actionable reports
version: 1.0.0
agent: integration-orchestrator
reusability: high
---

# Aggregate Workflow Results

## Purpose

Collect, aggregate, and summarize results from multi-agent coordination workflows, providing clear status reports and actionable next steps.

## When to Use

- After multi-agent workflow completion
- When workflow partially completes
- When workflow fails
- For status reporting to user

## Inputs

- Individual agent results (from each agent in workflow)
- Test execution results
- Integration validation results
- Error logs and failure details

## Outputs

- **Workflow summary report** (status, completed steps, pending steps)
- **Artifact inventory** (files created/modified)
- **Next steps** (what user should do)
- **Failure analysis** (if workflow failed)

## Aggregation Workflow

### 1. Collect Agent Results

```python
# Example agent result structure
@dataclass
class AgentResult:
    agent_name: str
    status: str  # SUCCESS, FAILED, SKIPPED, PARTIAL
    artifacts: List[str]  # Files created/modified
    errors: List[str]
    warnings: List[str]
    duration: float  # seconds
    output: str  # Agent's response

workflow_results = [
    AgentResult(
        agent_name="Domain Guardian",
        status="SUCCESS",
        artifacts=["domain/task.py", "domain/priority.py"],
        errors=[],
        warnings=[],
        duration=15.3,
        output="Created Priority value object, updated Task entity"
    ),
    AgentResult(
        agent_name="Data Schema Guardian",
        status="SUCCESS",
        artifacts=["migrations/001_add_priority.py"],
        errors=[],
        warnings=["Migration not executed yet"],
        duration=8.7,
        output="Generated migration for priority column"
    ),
    # ... more results
]
```

### 2. Calculate Workflow Status

**Status Determination Logic:**

```python
def calculate_workflow_status(results: List[AgentResult]) -> str:
    """
    Determine overall workflow status from agent results.

    Returns: "SUCCESS", "PARTIAL", "FAILED"
    """
    if all(r.status == "SUCCESS" for r in results):
        return "SUCCESS"

    if any(r.status == "FAILED" for r in results):
        return "FAILED"

    if any(r.status == "PARTIAL" for r in results):
        return "PARTIAL"

    if all(r.status == "SKIPPED" for r in results):
        return "SKIPPED"

    return "UNKNOWN"
```

### 3. Generate Workflow Summary Report

**Report Template:**

```markdown
# Workflow Execution Report

**Feature:** {feature_name}
**Status:** {workflow_status}
**Started:** {start_time}
**Completed:** {end_time}
**Duration:** {total_duration}

## Execution Summary

| Agent | Status | Artifacts | Duration |
|-------|--------|-----------|----------|
| Domain Guardian | ✅ SUCCESS | 2 files | 15.3s |
| Data Schema Guardian | ✅ SUCCESS | 1 file | 8.7s |
| Python Backend Architect | ✅ SUCCESS | 3 files | 22.1s |
| Next.js Frontend Architect | ✅ SUCCESS | 4 files | 18.9s |
| Integration Orchestrator | ✅ SUCCESS | 1 test | 12.4s |

**Total Artifacts Created:** 11 files

## Files Created/Modified

### Domain Layer
- `domain/task.py` (modified)
- `domain/priority.py` (created)

### Database Layer
- `migrations/001_add_priority.py` (created)

### Backend Layer
- `backend/services/task_service.py` (modified)
- `backend/schemas/task_schema.py` (modified)
- `backend/api/tasks.py` (modified)

### Frontend Layer
- `app/tasks/page.tsx` (modified)
- `app/tasks/components/PrioritySelector.tsx` (created)
- `app/tasks/components/TaskCard.tsx` (modified)
- `app/tasks/types.ts` (modified)

### Tests
- `tests/integration/test_task_priority.py` (created)

## Test Results

**Integration Tests:** ✅ 5/5 passed
**E2E Tests:** ✅ 2/2 passed

## Warnings

- Migration file created but not executed (run `alembic upgrade head`)

## Next Steps

1. Review generated code in each layer
2. Execute database migration: `alembic upgrade head`
3. Run full test suite: `pytest tests/`
4. Test manually in development environment
5. Create pull request when ready

---

**Workflow Status:** ✅ COMPLETE
```

### 4. Handle Partial/Failed Workflows

**Partial Success Report:**

```markdown
# Workflow Execution Report (PARTIAL)

**Status:** ⚠️ PARTIAL SUCCESS

## Completed Steps

✅ Domain Guardian - SUCCESS
✅ Data Schema Guardian - SUCCESS
✅ Python Backend Architect - SUCCESS

## Failed Steps

❌ Next.js Frontend Architect - FAILED
   Error: Type mismatch in TaskResponse interface
   Details: Expected 'priority' to be optional, but marked as required

❌ Integration Orchestrator - SKIPPED
   Reason: Prerequisites not met (frontend implementation failed)

## Artifacts Created

- Domain layer: 2 files ✅
- Database layer: 1 migration ✅
- Backend layer: 3 files ✅
- Frontend layer: 0 files ❌

## Remediation Steps

1. **Fix Frontend Type Mismatch**
   - File: `app/tasks/types.ts`
   - Change: Make `priority` optional in `TaskResponse`
   - Agent: Re-run Next.js Frontend Architect

2. **After Frontend Fix**
   - Re-run Integration Orchestrator
   - Execute E2E tests

## Rollback Instructions (if needed)

```bash
# Rollback domain changes
git checkout domain/

# Rollback database migration
alembic downgrade -1

# Rollback backend changes
git checkout backend/
```

---

**Workflow Status:** ⚠️ INCOMPLETE - Manual intervention required
```

### 5. Artifact Inventory

**Categorize All Created/Modified Files:**

```python
artifact_inventory = {
    "domain": [
        {"path": "domain/task.py", "action": "modified", "lines_changed": 45},
        {"path": "domain/priority.py", "action": "created", "lines_added": 30}
    ],
    "database": [
        {"path": "migrations/001_add_priority.py", "action": "created", "lines_added": 25}
    ],
    "backend": [
        {"path": "backend/services/task_service.py", "action": "modified", "lines_changed": 60},
        {"path": "backend/schemas/task_schema.py", "action": "modified", "lines_changed": 15},
        {"path": "backend/api/tasks.py", "action": "modified", "lines_changed": 8}
    ],
    "frontend": [
        {"path": "app/tasks/page.tsx", "action": "modified", "lines_changed": 30},
        {"path": "app/tasks/components/PrioritySelector.tsx", "action": "created", "lines_added": 75},
        {"path": "app/tasks/components/TaskCard.tsx", "action": "modified", "lines_changed": 12},
        {"path": "app/tasks/types.ts", "action": "modified", "lines_changed": 5}
    ],
    "tests": [
        {"path": "tests/integration/test_task_priority.py", "action": "created", "lines_added": 120}
    ]
}
```

## Report Output Formats

### Console Output (Concise)

```
✅ Workflow COMPLETE: Add Task Priority

Agents Executed: 5/5
Tests Passed: 7/7
Files Created: 3
Files Modified: 8

Next: Review code, run `alembic upgrade head`, create PR
```

### Detailed Report (Markdown File)

Save to: `reports/workflow-{feature-name}-{timestamp}.md`

### JSON Output (Programmatic)

```json
{
  "workflow_id": "add-task-priority-20250101-120000",
  "status": "SUCCESS",
  "feature": "task-priority",
  "agents": [
    {
      "name": "Domain Guardian",
      "status": "SUCCESS",
      "duration": 15.3,
      "artifacts": ["domain/task.py", "domain/priority.py"]
    }
  ],
  "tests": {
    "integration": {"passed": 5, "failed": 0},
    "e2e": {"passed": 2, "failed": 0}
  },
  "total_duration": 77.4,
  "artifacts_created": 11
}
```

## Constraints

- **MUST** include all agent results in report
- **MUST** clearly indicate failed/partial workflows
- **MUST** provide actionable next steps
- **DO NOT** hide errors or warnings

## Reusability

**Domain-Agnostic:** Report aggregation works for any workflow

**Applicable To:**
- Multi-agent feature implementations
- CI/CD pipeline reporting
- Deployment validation
- Any multi-step workflow

**Evolution:**
- Phase 1: Basic text reports
- Phase 2: Rich markdown reports with links
- Phase 3: HTML/web dashboard
- Phase 4: Real-time workflow monitoring

## Integration Points

**Triggered After:**
- Multi-agent workflow completion (success or failure)

**Inputs From:**
- All agent results
- Test execution results
- File system (to verify artifacts)

**Outputs To:**
- Console (user-facing summary)
- Report file (detailed analysis)
- Logging system (workflow audit trail)
