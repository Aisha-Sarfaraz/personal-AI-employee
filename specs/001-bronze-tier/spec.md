# Bronze Tier Specification: Personal AI Employee FTE System

**Version:** 1.0.0
**Date:** 2026-02-17
**Status:** Draft
**Tier:** BRONZE (Foundation Layer)
**Constitution Reference:** v1.1.0 (`.specify/memory/constitution.md`)

---

## Context

This specification defines the Bronze Tier (Foundation Layer) of the Personal AI Employee FTE system. Bronze establishes the core infrastructure: Obsidian vault as memory/GUI, one working filesystem watcher, Claude Code reasoning via agent skills, file-based HITL approval, audit logging, and a Python orchestrator with health monitoring. Silver/Gold tiers are structurally visible (stub files, folder slots) but not implemented.

All previous implementation was deleted. Only governance files remain (constitution, AGENTS.md, agent/skill definitions, MCP configs).

**Architecture (6 Layers):**
```
External Sources → Perception Layer (Watchers) → Obsidian Vault → Reasoning Layer (Claude Code) → HITL + Action Layer → Orchestration Layer
```

---

## Clarifications

### Session 2026-02-17

- Q: What should the filesystem watcher do with malformed files (binary, empty, unreadable)? → A: Move to `/Inbox` with `type: unknown`, `priority: LOW` — triage skill handles or skips.
- Q: When a user rejects an approval request, what happens to the plan/task? → A: Terminal. Plan marked `status: rejected`, moved to `/Done` with rejection metadata. User re-drops file to retry.
- Q: How should simultaneous file drops in Watch be handled? → A: Sequential FIFO. Watcher creates both Inbox items; orchestrator processes one-at-a-time in order.
- Q: What happens to in-flight items when orchestrator restarts mid-pipeline? → A: Resume from vault state. Orchestrator scans all folders on startup and continues processing items wherever they are.
- Q: What happens when a plan step has an unknown action_type? → A: Skip the step, log warning in `/Logs`, mark step as `skipped: unknown_action`, continue remaining steps.

---

## User Scenarios & Testing

### User Story 1 - Drop File Pipeline (Priority: P1)

User drops a file (e.g., invoice, email text) into `vault/Watch/`. The system detects it, triages it, generates a plan, requests approval if needed, and moves the completed item to `/Done`.

**Why this priority**: This is the core end-to-end workflow proving all 6 architecture layers work together.

**Independent Test**: Drop `test_invoice.txt` into `vault/Watch/` and verify it flows through Inbox → Needs_Action → Plans → Pending_Approval → (approve) → Done.

**Acceptance Scenarios**:

1. **Given** a file is dropped in `vault/Watch/`, **When** the filesystem watcher detects it, **Then** a frontmatter-tagged `.md` file appears in `vault/Inbox/` within 10 seconds.
2. **Given** an item exists in `vault/Inbox/`, **When** triage runs, **Then** the item is classified (type + priority) and moved to `vault/Needs_Action/`.
3. **Given** an item in `vault/Needs_Action/`, **When** the planner runs, **Then** a `PLAN_*.md` is created in `vault/Plans/` with steps and approval flags.
4. **Given** a plan with HIGH/CRITICAL steps, **When** the executor runs, **Then** `APPROVAL_REQUIRED_*.md` files appear in `vault/Pending_Approval/`.
5. **Given** an approval file moved to `vault/Approved/`, **When** the executor re-runs, **Then** the step executes (simulated in DEV_MODE) and the task moves to `vault/Done/`.
6. **Given** any pipeline action, **When** it completes, **Then** an audit log entry is written to `vault/Logs/`.

---

### User Story 2 - Dashboard Status Overview (Priority: P2)

User opens `vault/Dashboard.md` in Obsidian and sees current system status: pending tasks, active workflows, awaiting approvals, recent actions, watcher health.

**Why this priority**: Dashboard is the human's primary interface to the system.

**Independent Test**: Run the dashboard updater and verify Dashboard.md shows accurate counts from all vault folders.

**Acceptance Scenarios**:

1. **Given** items exist across vault folders, **When** the dashboard updater runs, **Then** `Dashboard.md` shows accurate counts for each folder.
2. **Given** the filesystem watcher is running, **When** the dashboard updater runs, **Then** watcher health status shows "running".
3. **Given** approval requests exist in `vault/Pending_Approval/`, **When** dashboard updates, **Then** they appear in an "Awaiting Approval" section with age.

---

### User Story 3 - HITL Approval Workflow (Priority: P2)

User reviews approval requests in `vault/Pending_Approval/` via Obsidian, then moves files to `vault/Approved/` or `vault/Rejected/` to approve or deny actions.

**Why this priority**: HITL is the safety foundation — nothing sensitive happens without human consent.

**Independent Test**: Create an approval request, move it to Approved, verify the system detects and proceeds.

**Acceptance Scenarios**:

1. **Given** a HIGH-risk action, **When** the executor encounters it, **Then** an `APPROVAL_REQUIRED_{uuid}.md` file is created in `vault/Pending_Approval/` with action details, risk tier, and context.
2. **Given** an approval file in `vault/Pending_Approval/`, **When** the user moves it to `vault/Approved/`, **Then** the executor detects approval and proceeds with the action.
3. **Given** an approval file in `vault/Pending_Approval/`, **When** the user moves it to `vault/Rejected/`, **Then** the executor marks the plan as `status: rejected`, moves it to `/Done` with rejection metadata, and logs the rejection. Rejection is terminal — user must re-drop the original file to retry.
4. **Given** an approval request older than 24 hours, **When** checked, **Then** it is marked expired and the action is re-queued.

---

### User Story 4 - Handbook Compliance (Priority: P3)

The system validates all planned actions against `Company_Handbook.md` rules before execution. Financial thresholds, communication rules, and behavioral constraints are enforced.

**Why this priority**: Compliance ensures the system operates within defined business rules.

**Independent Test**: Create a plan with a $5000 financial action, verify it's classified as CRITICAL and requires explicit approval.

**Acceptance Scenarios**:

1. **Given** a financial action of $500, **When** handbook check runs, **Then** risk is classified as HIGH (requires explicit approval).
2. **Given** a financial action of $15,000, **When** handbook check runs, **Then** it is DENIED (system must not process).
3. **Given** a LOW-risk action (read data), **When** handbook check runs, **Then** it auto-approves.

---

### Edge Cases

- **Malformed file in Watch (binary, empty, unreadable):** Watcher moves it to `/Inbox` with `type: unknown`, `priority: LOW`. Triage skill classifies or skips. Human can review in Obsidian.
- **Simultaneous file drops:** Watcher creates both Inbox items independently. Orchestrator processes them sequentially in FIFO order (one pipeline at a time). No parallel execution in Bronze.
- What happens when the vault folder structure is missing (e.g., /Inbox deleted)?
- **Rejection lifecycle:** Rejection is terminal. Plan is marked `status: rejected` and archived to `/Done`. No automatic requeue. User re-drops original file to retry.
- What happens when an approval request has no matching plan?
- **Orchestrator restart mid-pipeline:** Resume from vault state. On startup, orchestrator scans all folders and continues processing items wherever they are. No special recovery logic — vault folder position IS the state. Idempotent re-execution via `step_action_ids` prevents duplicate approvals.
- **Unknown action_type in plan step:** Skip the step, log a warning in `/Logs` with `skipped: unknown_action`, continue executing remaining plan steps. Does not fail the entire plan.

---

## Requirements

### Functional Requirements

#### FR-A: Vault Structure
- **FR-A01**: System MUST use an Obsidian-compatible local Markdown vault at `vault/` as the memory layer and GUI.
- **FR-A02**: Vault MUST contain folders: `/Inbox`, `/Needs_Action`, `/Plans`, `/Done`, `/Logs`, `/Pending_Approval`, `/Approved`, `/Rejected`, `/Watch`.
- **FR-A03**: Vault MUST contain `Dashboard.md` (system status), `Company_Handbook.md` (business rules), `Business_Goals.md` (objectives).
- **FR-A04**: All vault writes MUST use atomic write pattern (write-to-temp + rename) to prevent corruption.
- **FR-A05**: All vault files with machine-readable data MUST use YAML frontmatter format.

#### FR-B: Core Libraries
- **FR-B01**: `vault.py` MUST provide: `read_file`, `write_file`, `move_file`, `list_folder`, `read_frontmatter_file`, `write_frontmatter_file` with atomic writes.
- **FR-B02**: `frontmatter.py` MUST provide: `parse_frontmatter` (YAML→dict), `write_frontmatter` (dict→YAML+body), `create_standard_metadata` (type, source, timestamp, priority, status).
- **FR-B03**: `approval.py` MUST provide: `create_approval_request` (writes to `/Pending_Approval`), `check_approval_status` (scans Approved/Rejected/Pending_Approval), with 24-hour expiry.
- **FR-B04**: `audit_logger.py` MUST provide: `log_action` (writes `AUDIT_*.md` to `/Logs` with timestamp, agent, action, risk_tier, status, details).

#### FR-C: Perception Layer (Watchers)
- **FR-C01**: `base_watcher.py` MUST define an abstract base class with: `check_for_updates()`, `create_action_file()`, deduplication via processed IDs set + JSON state persistence, configurable poll interval.
- **FR-C02**: `filesystem_watcher.py` MUST monitor `vault/Watch/` using the `watchdog` library, detect new files, create frontmatter-tagged `.md` files in `vault/Inbox/` with file content, name, and timestamp. For malformed files (binary, empty, unreadable), the watcher MUST still create an Inbox entry with `type: unknown` and `priority: LOW`.
- **FR-C03**: `gmail_watcher.py` MUST exist as a stub class inheriting `BaseWatcher`, raising `NotImplementedError` on `check_for_updates()`. [Silver tier placeholder]
- **FR-C04**: `whatsapp_watcher.py` MUST exist as a stub class. [Silver tier placeholder]
- **FR-C05**: `finance_watcher.py` MUST exist as a stub class. [Silver tier placeholder]

#### FR-D: Reasoning Layer (Agent Skills)
- **FR-D01**: `triage_inbox.py` (Inbox Interpreter): MUST scan `/Inbox`, classify each item by type (financial, communication, task, document, general) and priority (CRITICAL, HIGH, MEDIUM, LOW) using keyword analysis, then move to `/Needs_Action` with updated frontmatter.
- **FR-D02**: `check_handbook.py` (Handbook Compliance Checker): MUST read `Company_Handbook.md`, classify action risk per handbook rules (financial thresholds: $0-100 MEDIUM, $100-1K HIGH, $1K-10K CRITICAL, >$10K DENIED), return validation result with risk level and required approval.
- **FR-D03**: `plan_task.py` (Planner): MUST read task from `/Needs_Action` + handbook rules, generate `PLAN_*.md` in `/Plans` with numbered steps, each step having action_type, description, risk_level, and requires_approval flag.
- **FR-D04**: `execute_plan.py` (Plan Executor): MUST read plans from `/Plans`, execute steps sequentially, create approval requests in `/Pending_Approval` for HIGH/CRITICAL steps, check approval status before proceeding, persist `step_action_ids` in plan metadata to prevent duplicate approval requests on re-execution.
- **FR-D05**: `update_dashboard.py` (Dashboard Updater): MUST scan all vault folders, count items per folder, check watcher health, and regenerate `Dashboard.md` with status tables.
- **FR-D06**: All skills MUST have a `run(vault_root)` entry point.

#### FR-E: HITL Approval
- **FR-E01**: HIGH/CRITICAL risk actions MUST produce `APPROVAL_REQUIRED_{uuid}.md` in `/Pending_Approval` containing: action description, risk tier, originating plan, step number, context, and creation timestamp.
- **FR-E02**: Human approves by moving file to `/Approved`, denies by moving to `/Rejected`.
- **FR-E03**: Approval requests MUST expire after 24 hours (configurable).
- **FR-E04**: LOW actions auto-proceed. MEDIUM actions proceed with notification logged.
- **FR-E05**: Re-execution of a plan MUST NOT create duplicate approval requests (use persisted step_action_ids).

#### FR-F: Action Layer
- **FR-F01**: `action_executor.py` MUST map action_type strings to handler functions: `send_email`, `create_invoice`, `post_social`, `update_calendar`, `file_operation`.
- **FR-F02**: In DEV_MODE (default for Bronze), all handlers MUST simulate execution — log the intended action without performing it.
- **FR-F04**: If `action_type` is not recognized, the executor MUST skip the step, log a warning with `skipped: unknown_action` to `/Logs`, and continue with remaining plan steps.
- **FR-F03**: Each handler MUST return a result dict with: `success`, `action_type`, `details`, `simulated` flag.

#### FR-G: Orchestration
- **FR-G01**: `orchestrator.py` MUST start filesystem watcher in a daemon thread, then run a continuous scan loop: triage → plan → execute → dashboard update.
- **FR-G02**: Orchestrator MUST support a multi-watcher registry (dict of name → watcher instance) even though only filesystem_watcher is active in Bronze.
- **FR-G03**: Orchestrator MUST handle graceful shutdown via SIGINT/SIGTERM signal handlers.
- **FR-G06**: On startup, orchestrator MUST scan all vault folders and resume processing items wherever they are in the pipeline. Vault folder position is the authoritative state — no separate state database required.
- **FR-G04**: `watchdog_monitor.py` MUST run as a background thread checking: watcher threads alive, plans not stuck (age > configurable threshold), vault folder integrity.
- **FR-G05**: `ecosystem.config.js` MUST configure PM2 to run the orchestrator as a daemon with auto-restart and log output to `logs/`.

#### FR-H: Configuration
- **FR-H01**: `config/settings.yaml` MUST define: vault folder paths, watcher settings (poll_interval, watch_folder), orchestrator settings (scan_interval, max_plan_age), approval settings (expiry_hours), and dev_mode flag.
- **FR-H02**: All operational parameters MUST be configurable (no hardcoded thresholds).

### Key Entities

- **Vault Item**: A Markdown file with YAML frontmatter (type, source, timestamp, priority, status, metadata). Lives in vault folders, moves through the pipeline.
- **Plan**: A Markdown file in `/Plans` with ordered steps. Each step has action_type, description, risk_level, requires_approval. Contains step_action_ids for idempotent re-execution.
- **Approval Request**: A Markdown file in `/Pending_Approval` with action details, risk tier, UUID, creation timestamp, and expiry.
- **Audit Entry**: A Markdown file in `/Logs` recording agent, action, risk_tier, status, timestamp, details.
- **Watcher State**: A JSON file persisting processed item IDs for deduplication across restarts.

---

## Project Structure

```
fte-employe/
├── vault/                              # OBSIDIAN VAULT
│   ├── Dashboard.md                    # System status overview
│   ├── Company_Handbook.md             # Business rules for Claude
│   ├── Business_Goals.md               # Business objectives
│   ├── Inbox/                          # Raw watcher outputs
│   ├── Needs_Action/                   # Triaged actionable items
│   ├── Plans/                          # Execution plans
│   ├── Done/                           # Completed archive
│   ├── Logs/                           # Audit trail
│   ├── Pending_Approval/               # HITL approval requests
│   ├── Approved/                       # Human-approved actions
│   ├── Rejected/                       # Human-denied actions
│   └── Watch/                          # Drop folder for filesystem watcher
│
├── src/
│   ├── core/                           # Core libraries
│   │   ├── vault.py                    # Vault CRUD + atomic writes
│   │   ├── frontmatter.py             # YAML frontmatter parser
│   │   ├── approval.py                # HITL approval management
│   │   └── audit_logger.py            # Markdown audit logging
│   │
│   ├── watchers/                       # Perception Layer
│   │   ├── base_watcher.py            # Abstract base class
│   │   ├── filesystem_watcher.py      # [IMPLEMENTED] Drop folder watcher
│   │   ├── gmail_watcher.py           # [STUB] Silver tier
│   │   ├── whatsapp_watcher.py        # [STUB] Silver tier
│   │   └── finance_watcher.py         # [STUB] Gold tier
│   │
│   ├── skills/                         # Reasoning Layer (Agent Skills)
│   │   ├── triage_inbox.py            # Inbox Interpreter
│   │   ├── check_handbook.py          # Handbook Compliance Checker
│   │   ├── plan_task.py               # Planner
│   │   ├── execute_plan.py            # Plan Executor with HITL gates
│   │   └── update_dashboard.py        # Dashboard Updater
│   │
│   ├── actions/                        # Action Layer
│   │   └── action_executor.py         # DEV_MODE dispatcher
│   │
│   ├── orchestrator.py                # Master process
│   └── watchdog_monitor.py            # Health monitor
│
├── tests/                              # All tests
├── config/
│   └── settings.yaml                  # Configuration
├── ecosystem.config.js                # PM2 process config
├── requirements.txt                   # Python dependencies
└── logs/                              # PM2 log output
```

---

## Implementation Order

### Phase 1: Setup
- Create all directories with `__init__.py` files
- Create `requirements.txt` (watchdog, pyyaml, python-dotenv, pytest, pytest-cov)
- Create `config/settings.yaml`
- Create vault folders with `.gitkeep`

### Phase 2: Core Libraries
- `src/core/vault.py` — CRUD + atomic writes
- `src/core/frontmatter.py` — YAML frontmatter parser/writer
- `src/core/audit_logger.py` — Markdown audit logging to `/Logs`
- `src/core/approval.py` — HITL approval management in `/Pending_Approval`

### Phase 3: Vault Knowledge Files
- `vault/Dashboard.md` — Initial system status template
- `vault/Company_Handbook.md` — Business rules (communication, financial thresholds, approval requirements, behavioral constraints)
- `vault/Business_Goals.md` — Business objectives

### Phase 4: Watcher Layer
- `src/watchers/base_watcher.py` — Abstract base with dedup + state persistence
- `src/watchers/filesystem_watcher.py` — Full watchdog implementation
- `src/watchers/gmail_watcher.py` — Stub
- `src/watchers/whatsapp_watcher.py` — Stub
- `src/watchers/finance_watcher.py` — Stub

### Phase 5: Reasoning Skills
- `src/skills/triage_inbox.py` — Classify type + priority, move Inbox → Needs_Action
- `src/skills/check_handbook.py` — Risk classification per handbook rules
- `src/skills/plan_task.py` — Generate Plan.md with steps + approval flags
- `src/skills/execute_plan.py` — Execute steps with HITL gates + step_action_ids persistence
- `src/skills/update_dashboard.py` — Scan vault → refresh Dashboard.md

### Phase 6: Action Layer
- `src/actions/action_executor.py` — DEV_MODE dispatcher with stubs

### Phase 7: Orchestration
- `src/orchestrator.py` — Multi-watcher registry + scan loop + signal handlers
- `src/watchdog_monitor.py` — Health monitor thread
- `ecosystem.config.js` — PM2 config

### Phase 8: Tests
- Unit tests for all core modules
- E2E integration test (drop file → full pipeline → Done)

---

## Success Criteria

### Measurable Outcomes

- **SC-001**: `python -m pytest tests/ -v` — all tests pass with 0 failures.
- **SC-002**: `python src/orchestrator.py` starts without error, filesystem watcher + watchdog running.
- **SC-003**: Drop a file in `vault/Watch/` → full pipeline completes within 60 seconds (excluding human approval wait time).
- **SC-004**: `Dashboard.md` accurately reflects vault state after each scan cycle.
- **SC-005**: Every pipeline action produces an audit entry in `vault/Logs/`.
- **SC-006**: HIGH/CRITICAL actions block until human moves approval file to `/Approved` or `/Rejected`.
- **SC-007**: Re-running the executor on the same plan does not create duplicate approval requests.
- **SC-008**: `pm2 start ecosystem.config.js` keeps the orchestrator running as a daemon.
- **SC-009**: Silver/Gold stub watchers exist as importable classes that raise `NotImplementedError`.

---

## Silver/Gold Tier Design (NOT IMPLEMENTED — Structure Only)

### Silver Tier Additions
- `gmail_watcher.py` — Gmail API polling, OAuth2, writes to `/Inbox`
- `whatsapp_watcher.py` — WhatsApp Business API, writes to `/Inbox`
- Multiple MCP servers (email-mcp active)
- LinkedIn sales posts via browser-mcp
- Cron scheduling for periodic operations
- Idempotency keys for external actions
- Queue with persistence (`vault/state/queue.json`)
- Quarantine folder for failed items

### Gold Tier Additions
- `finance_watcher.py` — Odoo JSON-RPC + bank API polling
- Cross-domain (Personal + Business) with domain isolation
- Full 15-agent system (10 dev + 5 LifeOps)
- Weekly audit reports + CEO briefing
- Circuit breakers per MCP server
- Ralph Wiggum persistence loop
- Vault encryption for sensitive files
- JSON structured audit logging

---

## Constitution Traceability

| Requirement | Constitution Section | Status |
|-------------|---------------------|--------|
| B1: Obsidian vault + Dashboard + Handbook | S2.1(1-3), S4.2(L1) | Specified |
| B2: One working watcher (filesystem) | S2.1(5), S4.2(L2) | Specified |
| B3: Claude reads/writes vault | S2.1(6), S4.2(L5) | Specified |
| B4: Folder structure /Inbox, /Needs_Action, /Done | S2.1(4), S4.2(L1) | Specified (expanded with /Logs, /Pending_Approval, /Approved, /Rejected, /Plans, /Watch) |
| B5: All AI as Agent Skills | S2.1(7), S5.3 | Specified (5 skills with run() entry points) |
| DEV_MODE sandboxing | S8.2(SEC6), S8.5 | Specified |
| Atomic writes | S4.4(3) | Specified |
| Audit logging | S10.1 | Specified (Markdown format per Bronze tier) |
| HITL 4-tier risk model | S9.1 | Specified |
| Financial thresholds | S9.2 | Specified |

---

## Risks & Follow-ups

1. **Risk**: File-based HITL is manual (user must move files in Obsidian). Mitigation: Clear naming convention (`APPROVAL_REQUIRED_*`) and Dashboard.md highlights pending approvals.
2. **Risk**: Keyword-based triage (no LLM) may misclassify items. Mitigation: Conservative classification (default to MEDIUM), human reviews in Obsidian.
3. **Follow-up**: After Bronze validation, user will provide credentials for Gmail/WhatsApp watchers (Silver tier).
