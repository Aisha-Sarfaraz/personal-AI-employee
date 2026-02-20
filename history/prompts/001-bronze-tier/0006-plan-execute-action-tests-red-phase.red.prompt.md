---
id: "0006"
title: "Plan Execute Action Tests Red Phase"
stage: red
date: 2026-02-17
surface: agent
model: claude-sonnet-4-5-20250929
feature: 001-bronze-tier
branch: 001-bronze-tier
user: USER-PC
command: write three test files for plan_task, execute_plan, action_executor
labels: ["red", "tdd", "plan-task", "execute-plan", "action-executor", "hitl", "tests", "bronze-tier"]
links:
  spec: specs/001-bronze-tier/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - tests/test_plan_task.py
  - tests/test_execute_plan.py
  - tests/test_action_executor.py
tests:
  - tests/test_plan_task.py
  - tests/test_execute_plan.py
  - tests/test_action_executor.py
---

## Prompt

Write THREE test files for the Bronze Tier FTE system. Create all three files.

## File 1: D:/gemini-cli/practice/hacathons/fte-employe/tests/test_plan_task.py

Module `src/skills/plan_task.py`:
- `run(vault_root: str) -> dict` — scans /Needs_Action, generates PLAN_{timestamp}_{item_id}.md in /Plans
- Each plan has numbered steps with action_type, description, risk_level, requires_approval
- Financial items get: verify→check_handbook→create_invoice→record steps
- Communication items: draft→review→send steps
- Task items: analyze→execute→verify steps
- General items: review→process steps
- Returns {"processed": int, "errors": list[str], "skipped": int}

Tests for test_plan_task.py:
1. Creates PLAN_*.md in /Plans from item in /Needs_Action
2. Plan has correct frontmatter (id, source_item, type, priority, status:pending, step_count, step_action_ids:{})
3. Financial item generates financial-specific steps with approval flags
4. Communication item generates comm steps
5. Task item generates task steps
6. General item generates general steps
7. Empty Needs_Action returns processed:0
8. Item status updated to "planned"

## File 2: D:/gemini-cli/practice/hacathons/fte-employe/tests/test_execute_plan.py

Module `src/skills/execute_plan.py`:
- `run(vault_root: str) -> dict` — scans /Plans for status:pending plans
- For each plan, iterates steps sequentially
- HIGH/CRITICAL steps: check step_action_ids for existing approval ID, create if needed, check status
- Approved steps → call action_executor
- Rejected steps → mark plan rejected, move to /Done (terminal)
- All complete → move to /Done with status:completed
- Returns {"processed": int, "errors": list[str], "skipped": int}

Tests for test_execute_plan.py:
1. Executes LOW-risk plan steps automatically (no approval needed)
2. Creates approval request for HIGH-risk step
3. Persists step_action_ids in plan frontmatter
4. Re-execution doesn't create duplicate approval requests (idempotent)
5. Approved step gets executed
6. Rejected step → plan marked rejected, moved to /Done
7. Completed plan moved to /Done
8. Empty Plans returns processed:0

## File 3: D:/gemini-cli/practice/hacathons/fte-employe/tests/test_action_executor.py

Module `src/actions/action_executor.py`:
- `execute_action(action_type: str, details: dict, dev_mode: bool = True) -> dict`
- Maps action_type to handler: send_email, create_invoice, post_social, update_calendar, file_operation
- DEV_MODE simulates all (logs intended action)
- Unknown action_type → returns {success: False, action_type, details: "skipped: unknown_action", simulated: dev_mode}
- Returns {success: bool, action_type: str, details: str, simulated: bool}

Tests for test_action_executor.py:
1. send_email returns success with simulated=True in DEV_MODE
2. create_invoice returns success with simulated=True
3. post_social returns success with simulated=True
4. update_calendar returns success with simulated=True
5. file_operation returns success with simulated=True
6. Unknown action_type returns success=False with "skipped: unknown_action"
7. Result dict has all required keys (success, action_type, details, simulated)

Use pytest with tmp_path. Import from src.core.vault for creating test files. Create vault structure with Needs_Action/, Plans/, Done/, Logs/, Pending_Approval/, Approved/, Rejected/ in fixtures.

Write all three complete test files.

## Response snapshot

Created three test files with a total of 102 tests collected cleanly by pytest:

**tests/test_plan_task.py — 35 tests across 8 classes:**
- `TestPlanFileCreation` (5 tests): creates PLAN_*.md in Plans/; filename matches PLAN_ prefix; returns dict with processed count, errors list, skipped count.
- `TestPlanFrontmatter` (7 tests): id, source_item, type, priority, status:pending, step_count positive int, step_action_ids empty dict on creation.
- `TestFinancialItemSteps` (5 tests): verify step, create_invoice step, record step, requires_approval flag, step_count >= 3.
- `TestCommunicationItemSteps` (4 tests): draft step, send step, review step, step_count >= 3.
- `TestTaskItemSteps` (4 tests): analyze step, execute step, verify step, step_count >= 3.
- `TestGeneralItemSteps` (3 tests): review step, process step, step_count >= 2.
- `TestEmptyNeedsAction` (4 tests): processed=0, no plan files created, errors=[], skipped=0.
- `TestSourceItemStatusUpdate` (3 tests): source item status becomes 'planned'; all multi-item statuses updated; already-planned items skipped.

**tests/test_execute_plan.py — 31 tests across 8 classes:**
- `TestLowRiskAutoExecution` (4 tests): LOW-risk plan processed, no approval files, plan moved to Done/, result dict structure.
- `TestHighRiskApprovalCreation` (4 tests): approval file created for HIGH/CRITICAL; plan stays in Plans/ while pending; approval references plan ID.
- `TestStepActionIdsPersistence` (3 tests): step_action_ids populated; value is UUID string; LOW-risk steps have empty step_action_ids.
- `TestIdempotentApprovalCreation` (2 tests): second run does not duplicate approval; step_action_ids unchanged.
- `TestApprovedStepExecution` (2 tests): approved step executes on next run; plan status becomes 'completed'.
- `TestRejectedStepHandling` (3 tests): rejected step moves plan to Done/; status becomes 'rejected'; removed from Plans/.
- `TestCompletedPlanMovedToDone` (4 tests): LOW-risk plan moves to Done/; status=completed; removed from Plans/; mixed step plan completes only after approval.
- `TestEmptyPlans` (4 tests): processed=0, errors=[], no Done files, result dict valid.

**tests/test_action_executor.py — 36 tests across 7 classes:**
- `TestSendEmail` (4 tests): success=True; simulated=True; action_type matches; non-empty details.
- `TestCreateInvoice` (4 tests): same pattern as send_email.
- `TestPostSocial` (4 tests): same pattern.
- `TestUpdateCalendar` (4 tests): same pattern.
- `TestFileOperation` (4 tests): same pattern.
- `TestUnknownActionType` (5 tests + parametrize with 5 values = 9 total): success=False; details='skipped: unknown_action'; simulated matches dev_mode; action_type preserved; parametrized unknown types.
- `TestResultStructure` (8 tests): all required keys present for known/unknown actions; success is bool; simulated is bool; action_type matches input; details is str; default dev_mode=True; no side effects in DEV_MODE.

Helper patterns used consistently across all three files:
- `make_vault(tmp_path)` creates all 7 standard vault directories.
- `parse_yaml_frontmatter(file_path)` used for direct frontmatter inspection.
- `seed_*` functions create test fixtures without going through the module under test.
- `move_approval_to_approved/rejected` simulates HITL decisions for execute_plan tests.
- `assert_valid_result(result, action_type)` validates all four required dict keys and types.

## Outcome

- Impact: Red phase complete for plan_task, execute_plan, and action_executor — 102 contract-specifying tests written before source modules exist; drives Green phase implementation of src/skills/plan_task.py, src/skills/execute_plan.py, and src/actions/action_executor.py.
- Tests: tests/test_plan_task.py (35 tests), tests/test_execute_plan.py (31 tests), tests/test_action_executor.py (36 tests) — 102 total, all collected successfully.
- Files: tests/test_plan_task.py, tests/test_execute_plan.py, tests/test_action_executor.py created.
- Next prompts: Implement src/skills/plan_task.py, src/skills/execute_plan.py, src/actions/action_executor.py (Green phase); run pytest to confirm all 102 tests pass.
- Reflection: The three files follow the exact same codebase style as the existing test files (test_vault.py, test_approval.py, test_audit_logger.py). HITL flow tested via file-system simulation (moving approval files between Pending_Approval/, Approved/, Rejected/) matching the src/core/approval.py contract. Idempotency test verifies no duplicate approval requests — critical for reliability. Parametrized unknown action_type test covers 5 distinct invalid inputs including empty string and wrong case.

## Evaluation notes (flywheel)

- Failure modes observed: None — all 102 tests collected cleanly with no syntax or import errors at collection time.
- Graders run and results (PASS/FAIL): N/A (Red phase — no implementation yet)
- Prompt variant (if applicable): N/A
- Next experiment (smallest change to try): Implement src/actions/action_executor.py first (simplest — pure function with no vault dependencies), verify its 36 tests pass, then implement src/skills/plan_task.py, then src/skills/execute_plan.py.
