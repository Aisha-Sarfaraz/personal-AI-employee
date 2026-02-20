# Tasks: Bronze Tier Foundation

**Input**: Design documents from `/specs/001-bronze-tier/`
**Prerequisites**: plan.md, spec.md, data-model.md, contracts/skill-interface.md, research.md, quickstart.md

**Tests**: Included — constitution mandates TDD (S6.1).

**Organization**: Tasks grouped by user story. Each story is independently testable after foundational phase completes.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization — directories, dependencies, configuration

- [x] T001 Create project directory structure: `src/`, `src/core/`, `src/watchers/`, `src/skills/`, `src/actions/`, `tests/`, `config/`, `logs/` with `__init__.py` files
- [x] T002 Create vault folder structure: `vault/Inbox/`, `vault/Needs_Action/`, `vault/Plans/`, `vault/Done/`, `vault/Logs/`, `vault/Pending_Approval/`, `vault/Approved/`, `vault/Rejected/`, `vault/Watch/`, `vault/state/` with `.gitkeep` files
- [x] T003 [P] Create `requirements.txt` with: watchdog, pyyaml, python-dotenv, pytest, pytest-cov
- [x] T004 [P] Create `config/settings.yaml` with all configuration per data-model.md Configuration entity schema
- [x] T005 [P] Create `.env.example` with DEV_MODE=true placeholder

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core libraries that ALL user stories depend on. MUST complete before any user story.

**CRITICAL**: No user story work can begin until this phase is complete.

### Tests for Foundational

- [x] T006 [P] Write tests for vault.py CRUD operations in `tests/test_vault.py` — test read_file, write_file (atomic), move_file, list_folder, read_frontmatter_file, write_frontmatter_file
- [x] T007 [P] Write tests for frontmatter.py parsing in `tests/test_frontmatter.py` — test parse_frontmatter, write_frontmatter, create_standard_metadata, roundtrip, malformed input handling
- [x] T008 [P] Write tests for audit_logger.py in `tests/test_audit_logger.py` — test log_action creates AUDIT_*.md in /Logs with correct frontmatter fields
- [x] T009 [P] Write tests for approval.py in `tests/test_approval.py` — test create_approval_request writes to /Pending_Approval, check_approval_status scans Approved/Rejected/Pending_Approval, 24h expiry detection

### Implementation for Foundational

- [x] T010 [P] Implement `src/core/frontmatter.py` — parse_frontmatter (split on `---`, yaml.safe_load), write_frontmatter (yaml.dump + body), create_standard_metadata (type, source, timestamp, priority, status). All functions with PEP 484 type hints.
- [x] T011 Implement `src/core/vault.py` — read_file, write_file (atomic: tempfile + os.replace), move_file (shutil.move), list_folder (os.listdir filtered to .md), read_frontmatter_file (uses frontmatter.parse_frontmatter), write_frontmatter_file (uses frontmatter.write_frontmatter). Depends on T010.
- [x] T012 [P] Implement `src/core/audit_logger.py` — log_action(vault_root, agent, action, risk_tier, status, details, related_item) writes AUDIT_{timestamp}_{agent}.md to /Logs with frontmatter per data-model.md Audit Entry schema. Uses vault.py for atomic writes.
- [x] T013 Implement `src/core/approval.py` — create_approval_request(vault_root, plan_id, step_number, action_type, description, risk_level) writes APPROVAL_REQUIRED_{uuid}.md to /Pending_Approval. check_approval_status(vault_root, approval_id) scans Approved/Rejected/Pending_Approval, returns status string. Implements 24h expiry check via created timestamp. Uses vault.py + frontmatter.py.

**Checkpoint**: Run `python -m pytest tests/test_vault.py tests/test_frontmatter.py tests/test_audit_logger.py tests/test_approval.py -v` — all pass.

---

## Phase 3: User Story 1 — Drop File Pipeline (Priority: P1) MVP

**Goal**: Drop a file in vault/Watch/ → full pipeline flows through Inbox → Needs_Action → Plans → Pending_Approval → Approved → Done

**Independent Test**: `echo "Process invoice for $500 from vendor ABC" > vault/Watch/test_invoice.txt` → verify file flows through entire pipeline

### Tests for User Story 1

- [x] T014 [P] [US1] Write tests for base_watcher.py in `tests/test_watcher.py` — test ABC interface, dedup via processed IDs, state persistence (save/load JSON), create_action_file creates frontmatter .md
- [x] T015 [P] [US1] Write tests for filesystem_watcher.py in `tests/test_watcher.py` — test file detection in Watch/, Inbox .md creation with correct frontmatter, binary/empty file handling (type:unknown), dedup across restarts
- [x] T016 [P] [US1] Write tests for triage_inbox.py in `tests/test_triage.py` — test keyword classification (financial/communication/task/document/general/unknown), priority scoring (CRITICAL/HIGH/MEDIUM/LOW), move from Inbox to Needs_Action with updated frontmatter
- [x] T017 [P] [US1] Write tests for plan_task.py in `tests/test_plan_task.py` — test plan generation from Needs_Action item, step creation with action_type/risk_level/requires_approval, financial plans get approval flags
- [x] T018 [P] [US1] Write tests for execute_plan.py in `tests/test_execute_plan.py` — test step execution, approval request creation for HIGH/CRITICAL, approval status checking, step_action_ids persistence for idempotent re-execution, rejection terminal flow, plan completion to /Done
- [x] T019 [P] [US1] Write tests for action_executor.py in `tests/test_action_executor.py` — test DEV_MODE simulation for each handler (send_email, create_invoice, post_social, update_calendar, file_operation), unknown action_type skip + warning, result dict format

### Implementation for User Story 1

- [x] T020 [P] [US1] Implement `src/watchers/base_watcher.py` — ABC with check_for_updates(), create_action_file(), _processed_ids set, _state_file path, save_state/load_state (JSON), configurable poll_interval, run() loop with error isolation per item
- [x] T021 [US1] Implement `src/watchers/filesystem_watcher.py` — extends BaseWatcher, uses watchdog Observer + FileSystemEventHandler on vault/Watch/, on_created handler queues files, check_for_updates returns queued files + directory scan, creates FILE_{timestamp}_{name}.md in /Inbox with content or "[Binary file]" for non-text. Depends on T020.
- [x] T022 [P] [US1] Implement watcher stubs: `src/watchers/gmail_watcher.py` (class GmailWatcher(BaseWatcher), NotImplementedError), `src/watchers/whatsapp_watcher.py` (class WhatsAppWatcher), `src/watchers/finance_watcher.py` (class FinanceWatcher)
- [x] T023 [US1] Implement `src/skills/triage_inbox.py` — run(vault_root): scan /Inbox, for each .md file: extract content, classify type by keyword dict scoring (financial: invoice/payment/$, communication: email/message/reply, task: todo/assign/deadline, document: report/summary/pdf), classify priority by keyword scoring (CRITICAL: urgent/emergency/critical, HIGH: important/deadline/asap, MEDIUM: default, LOW: info/fyi/optional), update frontmatter status→triaged, move to /Needs_Action, log via audit_logger. Returns {processed, errors, skipped}.
- [x] T024 [US1] Implement `src/skills/check_handbook.py` — classify_action_risk(action_type, details): return risk per handbook rules. classify_financial_risk(amount): $0-100→MEDIUM, $100-1K→HIGH, $1K-10K→CRITICAL, >$10K→DENIED. validate_action(vault_root, action_type, details): read Company_Handbook.md, return ValidationResult(allowed, risk_level, requires_approval, reason).
- [x] T025 [US1] Implement `src/skills/plan_task.py` — run(vault_root): scan /Needs_Action, for each .md: read item + check_handbook, generate PLAN_{timestamp}_{item_id}.md in /Plans with numbered steps per type (financial→verify+check_handbook+create_invoice+record, communication→draft+review+send, task→analyze+execute+verify, general→review+process). Each step has action_type, description, risk_level, requires_approval. Update item status→planned. Log audit. Returns {processed, errors, skipped}.
- [x] T026 [US1] Implement `src/actions/action_executor.py` — _handlers dict mapping action_type→function. execute_action(action_type, details, dev_mode=True): lookup handler, if not found skip+log warning with "skipped: unknown_action", if dev_mode simulate (log intended action), return {success, action_type, details, simulated}. Handlers: _send_email, _create_invoice, _post_social, _update_calendar, _file_operation — all simulate in DEV_MODE.
- [x] T027 [US1] Implement `src/skills/execute_plan.py` — run(vault_root): scan /Plans for status:pending plans, for each plan: iterate steps, for HIGH/CRITICAL steps check step_action_ids for existing approval ID (if exists check status, else create_approval_request and persist ID in step_action_ids), for approved steps call action_executor, for rejected steps mark plan status:rejected and move to /Done, for all-complete plans mark status:completed and move to /Done. Log all actions. Returns {processed, errors, skipped}.

**Checkpoint**: Run `python -m pytest tests/test_watcher.py tests/test_triage.py tests/test_plan_task.py tests/test_execute_plan.py tests/test_action_executor.py -v` — all pass. Manual test: drop file in vault/Watch/ → verify full pipeline flow.

---

## Phase 4: User Story 2 — Dashboard Status Overview (Priority: P2)

**Goal**: Dashboard.md shows accurate system status — folder counts, watcher health, pending approvals with age

**Independent Test**: Run update_dashboard skill, open Dashboard.md in Obsidian, verify accurate counts

### Tests for User Story 2

- [x] T028 [P] [US2] Write tests for update_dashboard.py in `tests/test_dashboard.py` — test folder counting, watcher health detection, approval age calculation, Dashboard.md generation with correct sections (System Status, Pending Tasks, Active Plans, Awaiting Approval, Recent Logs)

### Implementation for User Story 2

- [x] T029 [US2] Implement `src/skills/update_dashboard.py` — run(vault_root): scan all vault folders (list_folder for each), count items per folder, check watcher health (read vault/state/watcher_state.json for last_updated), scan /Pending_Approval for approval age, scan /Logs for recent entries. Regenerate Dashboard.md with tables: System Status (watcher health, last scan), Pending Tasks (/Needs_Action count), Active Plans (/Plans count), Awaiting Approval (list with age), Recent Actions (last 10 from /Logs), folder summary table. Use atomic write.

**Checkpoint**: Run `python -m pytest tests/test_dashboard.py -v` — all pass. Open vault/Dashboard.md in Obsidian.

---

## Phase 5: User Story 3 — HITL Approval Workflow (Priority: P2)

**Goal**: Approval requests appear in /Pending_Approval, human moves to Approved/Rejected, system detects and acts

**Independent Test**: Create approval request, move to Approved, verify executor detects and proceeds

**Note**: Most HITL functionality is already built in Phase 3 (approval.py in Phase 2, execute_plan.py in Phase 3). This phase covers vault knowledge files that define the rules and the orchestrator integration.

### Implementation for User Story 3

- [x] T030 [US3] Create `vault/Company_Handbook.md` — 6 sections: Communication Rules (response time, tone, disclosure), Financial Thresholds ($0-100 MEDIUM, $100-1K HIGH, $1K-10K CRITICAL, >$10K DENIED), Approval Requirements (LOW auto, MEDIUM notify, HIGH explicit, CRITICAL explicit+confirm), Behavioral Constraints (no deception, no impersonation, no silent execution), Task Processing Rules (FIFO, sequential, one pipeline at a time), Changelog
- [x] T031 [P] [US3] Create `vault/Business_Goals.md` — Business objectives document with sections: Mission, Current Priorities, Success Metrics, Operational Guidelines
- [x] T032 [P] [US3] Create `vault/Dashboard.md` — Initial template with placeholder sections (will be auto-regenerated by update_dashboard.py)

**Checkpoint**: Company_Handbook.md readable in Obsidian with all 6 sections. check_handbook.py can parse and apply rules from it.

---

## Phase 6: User Story 4 — Handbook Compliance (Priority: P3)

**Goal**: All planned actions validated against Company_Handbook.md rules before execution

**Independent Test**: Create plan with $5000 action → classified CRITICAL, $15000 → DENIED

### Tests for User Story 4

- [x] T033 [P] [US4] Write tests for check_handbook.py in `tests/test_handbook.py` — test financial thresholds ($50→MEDIUM, $500→HIGH, $5000→CRITICAL, $15000→DENIED), communication risk classification, action validation against handbook rules, handbook parsing

### Implementation for User Story 4

**Note**: check_handbook.py core logic was built in T024. This phase adds integration testing and handbook-specific edge cases.

- [x] T034 [US4] Enhance `src/skills/check_handbook.py` — add parse_handbook(vault_root) to dynamically read rules from Company_Handbook.md instead of hardcoded thresholds. Extract financial thresholds, communication rules, approval matrix from handbook markdown sections. Fallback to hardcoded defaults if parsing fails.

**Checkpoint**: Run `python -m pytest tests/test_handbook.py -v` — all pass. Financial threshold tests verify exact boundaries.

---

## Phase 7: Orchestration & Integration

**Purpose**: Wire everything together — orchestrator, watchdog, PM2, E2E test

### Tests for Integration

- [x] T035 [P] Write E2E test in `tests/test_e2e.py` — test full pipeline: create temp vault, drop file in Watch/, run triage→plan→execute→dashboard in sequence, verify file moves through Inbox→Needs_Action→Plans→Done, verify audit entries in /Logs, verify Dashboard.md updated. Test approval flow: drop financial file, verify approval request created, simulate approval (move file), re-run executor, verify completion.

### Implementation for Orchestration

- [x] T036 Implement `src/orchestrator.py` — load settings.yaml, init watcher registry (dict of name→instance, only filesystem_watcher enabled), start watchers as daemon threads, start watchdog_monitor as daemon thread, main scan loop: while running → triage_inbox.run() → plan_task.run() → execute_plan.run() → update_dashboard.run() → sleep(scan_interval). Signal handlers: SIGINT/SIGTERM set running=False for graceful shutdown. On startup: scan all vault folders to resume in-flight items. Log startup/shutdown to /Logs.
- [x] T037 Implement `src/watchdog_monitor.py` — WatchdogMonitor class with run() method as thread target. Checks: watcher threads alive (is_alive()), plans not stuck (scan /Plans for age > max_plan_age_hours), vault folder integrity (all 9 folders exist). Logs warnings for issues. Configurable check interval from settings.yaml.
- [x] T038 [P] Create `ecosystem.config.js` — PM2 config: name "fte-orchestrator", script "src/orchestrator.py", interpreter "python", cwd to project root, auto-restart true, max_restarts 10, log output to logs/fte-orchestrator-out.log and logs/fte-orchestrator-error.log

**Checkpoint**: Run `python -m pytest tests/ -v` — ALL tests pass. Run `python src/orchestrator.py` — starts without error, watcher + watchdog running. Drop file in vault/Watch/ → full pipeline completes. `pm2 start ecosystem.config.js` — process stays alive.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Final validation, cleanup, documentation

- [x] T039 Run full test suite: `python -m pytest tests/ -v --tb=short` — verify all tests pass
- [x] T040 [P] Run quickstart.md validation — follow all steps in `specs/001-bronze-tier/quickstart.md` and verify they work
- [x] T041 [P] Verify all stub watchers importable: `python -c "from src.watchers.gmail_watcher import GmailWatcher; from src.watchers.whatsapp_watcher import WhatsAppWatcher; from src.watchers.finance_watcher import FinanceWatcher"`
- [x] T042 Verify SC-001 through SC-009 success criteria from spec.md all pass

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 — BLOCKS all user stories
- **US1 Drop File Pipeline (Phase 3)**: Depends on Phase 2 — this is the MVP
- **US2 Dashboard (Phase 4)**: Depends on Phase 2 — can run parallel with US1
- **US3 HITL/Vault Files (Phase 5)**: Depends on Phase 2 — can run parallel with US1
- **US4 Handbook Compliance (Phase 6)**: Depends on Phase 2 + T024 from US1
- **Orchestration (Phase 7)**: Depends on Phases 3, 4, 5, 6 — wires everything together
- **Polish (Phase 8)**: Depends on Phase 7

### User Story Dependencies

- **US1 (P1)**: Can start after Foundational — no dependencies on other stories
- **US2 (P2)**: Can start after Foundational — independent of US1
- **US3 (P2)**: Can start after Foundational — independent of US1, US2
- **US4 (P3)**: Depends on T024 (check_handbook.py from US1) — enhances it with dynamic parsing

### Within Each User Story

- Tests FIRST (TDD: write failing tests before implementation)
- Core modules before dependent modules
- Skills before orchestration integration

### Parallel Opportunities

**Phase 2 parallel group**: T006, T007, T008, T009 (all test files), T010, T012 (frontmatter + audit_logger)
**Phase 3 parallel group**: T014-T019 (all US1 test files), T020+T022 (base_watcher + stubs)
**Phase 4+5 can run parallel**: US2 (dashboard) and US3 (vault files) are independent
**Phase 7**: T035 + T038 can run parallel (E2E test + PM2 config)

---

## Parallel Example: User Story 1

```bash
# Launch all US1 tests in parallel:
Task: "Write tests for base_watcher.py in tests/test_watcher.py"
Task: "Write tests for filesystem_watcher.py in tests/test_watcher.py"
Task: "Write tests for triage_inbox.py in tests/test_triage.py"
Task: "Write tests for plan_task.py in tests/test_plan_task.py"
Task: "Write tests for execute_plan.py in tests/test_execute_plan.py"
Task: "Write tests for action_executor.py in tests/test_action_executor.py"

# After tests, launch independent implementations in parallel:
Task: "Implement src/watchers/base_watcher.py"
Task: "Implement watcher stubs (gmail, whatsapp, finance)"
Task: "Implement src/actions/action_executor.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (core libraries)
3. Complete Phase 3: User Story 1 (drop file pipeline)
4. **STOP and VALIDATE**: Drop file in vault/Watch/ → verify full pipeline
5. Demo the MVP

### Incremental Delivery

1. Setup + Foundational → Core libraries ready
2. Add US1 (Drop File Pipeline) → Test pipeline → MVP!
3. Add US2 (Dashboard) → Dashboard shows live status
4. Add US3 (Vault Files) → Handbook + goals in place
5. Add US4 (Handbook Compliance) → Dynamic rule parsing
6. Add Orchestration → Full system running as daemon
7. Polish → All success criteria verified

### Task Summary

| Phase | Story | Task Count | Parallel Tasks |
|-------|-------|-----------|----------------|
| Phase 1: Setup | — | 5 | 3 |
| Phase 2: Foundational | — | 8 | 6 |
| Phase 3: US1 Pipeline | US1 | 14 | 10 |
| Phase 4: US2 Dashboard | US2 | 2 | 1 |
| Phase 5: US3 HITL/Vault | US3 | 3 | 2 |
| Phase 6: US4 Handbook | US4 | 2 | 1 |
| Phase 7: Orchestration | — | 4 | 2 |
| Phase 8: Polish | — | 4 | 2 |
| **Total** | | **42** | **27** |

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Constitution mandates TDD: write tests FIRST, verify they FAIL, then implement
- Each user story should be independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
