# Agent Invocation & Coordination Protocol

**Version**: 1.0
**Last Updated**: 2026-01-02
**Status**: AUTHORITATIVE EXECUTION PROTOCOL
**Based On**: CrewAI Process.sequential + LangChain Supervisor Pattern

This document defines the **mandatory execution sequence** for agent coordination in the TODO app architecture.

---

## Table of Contents

1. [Standard Execution Sequence](#1-standard-execution-sequence)
2. [Agent Handoff Contracts](#2-agent-handoff-contracts)
3. [Execution Rules](#3-execution-rules)
4. [Invocation Decision Tree](#4-invocation-decision-tree)
5. [Phase-Based Protocol Constraints](#5-phase-based-protocol-constraints)

---

## 1. Standard Execution Sequence

**Pattern**: CrewAI Process.sequential (agents execute sequentially, each receiving output from previous)

For a **typical multi-layer feature** (e.g., "Add task priority field"), agents execute in this order:

```
┌─────────────────────────────────────────────────────────────────┐
│  STANDARD AGENT EXECUTION SEQUENCE (CrewAI Sequential Pattern)  │
└─────────────────────────────────────────────────────────────────┘

1. Spec Governance Enforcer
   ├─ Validates: Specification exists and is complete
   ├─ Blocks if: No approved spec, missing sections, spec drift
   ├─ Output: ✅ Approved spec.md, plan.md, tasks.md
   └─ Next: Domain Guardian

2. Domain Guardian
   ├─ Validates: Domain model changes respect domain purity
   ├─ Blocks if: Domain pollution, invariant violations, invalid state transitions
   ├─ Output: ✅ Domain interface contracts, validation rules, invariants
   └─ Next: Data & Schema Guardian

3. Data & Schema Guardian
   ├─ Validates: Database schema aligns with domain model
   ├─ Blocks if: Schema conflicts with domain, no rollback migration
   ├─ Output: ✅ Migration scripts, schema documentation, persistence contracts
   └─ Next: Backend Architect (if backend changes needed)

4. Backend Architect (conditional: if backend changes needed)
   ├─ Validates: Backend implementation uses domain correctly
   ├─ Cannot block: Others (can be blocked by Domain, Schema, Integration, Test)
   ├─ Output: ✅ Backend services, API endpoints, persistence coordination
   └─ Next: Frontend Architect (if frontend changes needed)

5. Frontend Architect (conditional: if frontend changes needed)
   ├─ Validates: Frontend uses backend API contracts correctly
   ├─ Cannot block: Others (can be blocked by Integration, Test)
   ├─ Output: ✅ Frontend components, pages, API integration
   └─ Next: Better Auth Guardian (if auth changes needed)

6. Better Auth Guardian (conditional: if auth changes needed)
   ├─ Validates: Auth requirements defined, session handling secure
   ├─ Blocks if: Security requirements not met, session violations
   ├─ Output: ✅ Auth configuration, session contracts, permission rules
   └─ Next: Error & Reliability Architect

7. Error & Reliability Architect (always runs for review)
   ├─ Reviews: Error handling across all layers
   ├─ Advises: On resilience improvements, observability gaps
   ├─ Cannot block: (Advisory only)
   ├─ Output: ⚠️ Error taxonomy validation, observability recommendations
   └─ Next: Test Strategy Architect

8. Test Strategy Architect (always runs for validation)
   ├─ Validates: TDD compliance (tests before code), coverage requirements
   ├─ Blocks if: TDD violated, critical tests missing, coverage below minimum
   ├─ Output: ✅ Test validation report, coverage assessment
   └─ Next: Integration Orchestrator

9. Integration Orchestrator (always runs last)
   ├─ Validates: All integration points, cross-layer contracts
   ├─ Blocks if: Contract violations, integration test failures
   ├─ Executes: Integration tests (Backend + DB), E2E tests (full stack)
   ├─ Output: ✅ Integration validation report, E2E test results
   └─ Next: COMPLETE ✅

```

**Total Agents**: 9 (6 always run, 3 conditional)

---

## 2. Agent Handoff Contracts

Each agent transition requires explicit **input contracts** (what agent receives) and **output contracts** (what agent produces).

### 2.1 Spec Governance → Domain Guardian

**Input Contract**:
- User request with feature requirements
- Existing specs (if updating existing feature)

**Output Contract**:
- ✅ Approved `spec.md` (requirements, acceptance criteria, boundaries)
- ✅ Approved `plan.md` (architecture decisions, integration points)
- ✅ Approved `tasks.md` (atomic, testable tasks)

**Validation**:
- Domain Guardian confirms: Spec is implementable without domain pollution
- Domain Guardian receives: Complete domain requirements from spec

**Handoff Example**:
```
Spec Governance: "Feature requires adding 'priority' attribute to Task entity"
Domain Guardian receives: Spec section defining priority values, validation rules
Domain Guardian validates: Priority belongs in domain (not infrastructure concern)
```

---

### 2.2 Domain Guardian → Data & Schema Guardian

**Input Contract**:
- Domain model changes (new attributes, state transitions, invariants)
- Domain interface contracts (methods, parameters, return types)
- Domain validation rules

**Output Contract**:
- ✅ Domain model validation (APPROVE/REJECT with reasons)
- ✅ Domain interface definitions
- ✅ Domain invariants that schema must support

**Validation**:
- Data & Schema Guardian confirms: Schema can support domain model
- Domain Guardian verifies: Schema doesn't leak into domain

**Handoff Example**:
```
Domain Guardian: "Task entity now has 'priority' attribute (enum: low, medium, high)"
Data & Schema Guardian receives: Domain attribute definition
Data & Schema Guardian designs: tasks.priority column (VARCHAR(20), CHECK constraint)
Domain Guardian validates: Task entity doesn't reference database columns
```

---

### 2.3 Data & Schema Guardian → Backend Architect

**Input Contract**:
- Database schema design (tables, columns, constraints)
- Migration scripts (upgrade/downgrade)
- Persistence contracts (repository interfaces)

**Output Contract**:
- ✅ Database schema aligned with domain model
- ✅ Migration scripts (tested upgrade/downgrade)
- ✅ Repository interface contracts

**Validation**:
- Backend Architect confirms: Persistence contracts support application needs
- Data & Schema Guardian verifies: Backend uses repository contracts correctly

**Handoff Example**:
```
Data & Schema Guardian: "TaskRepository.create(task) -> Task with id and created_at"
Backend Architect receives: Repository interface contract
Backend Architect implements: TaskApplicationService calls TaskRepository.create()
Data & Schema Guardian validates: Backend doesn't write raw SQL
```

---

### 2.4 Backend Architect → Frontend Architect

**Input Contract**:
- Backend service implementation
- API contracts (endpoints, request/response schemas, auth requirements)
- Error response formats

**Output Contract**:
- ✅ Backend services implementing domain operations
- ✅ API endpoint contracts (HTTP methods, paths, payloads)
- ✅ Error handling (HTTP status codes, error bodies)

**Validation**:
- Frontend Architect confirms: API contracts are consumable
- Backend Architect verifies: Frontend uses API contracts correctly

**Handoff Example**:
```
Backend Architect: "POST /api/tasks: {title, priority} -> 201 Created {id, title, priority}"
Frontend Architect receives: API contract specification
Frontend Architect implements: Form submission calls POST /api/tasks
Backend Architect validates: Frontend request matches expected schema
```

---

### 2.5 Better Auth Guardian → Backend/Frontend Architects

**Input Contract** (to Backend/Frontend):
- Auth configuration (Better Auth setup)
- Session contracts (how to verify sessions)
- Permission rules (who can access what)

**Output Contract** (from Better Auth Guardian):
- ✅ Auth requirements definition
- ✅ Better Auth API usage contracts
- ✅ Session verification patterns

**Validation**:
- Backend Architect implements: `session = auth.api.getSession()`
- Frontend Architect implements: `const { data: session } = useSession()`
- Better Auth Guardian validates: Auth flows are secure

**Handoff Example**:
```
Better Auth Guardian: "Protected endpoints must call auth.api.getSession() and verify user"
Backend Architect receives: Auth contract
Backend Architect implements: Session check + ownership validation
Frontend Architect implements: useSession() hook for auth state
Better Auth Guardian validates: Auth integrated correctly across layers
```

---

### 2.6 All Agents → Integration Orchestrator

**Input Contract**:
- Implementation across all layers (Frontend, Backend, Domain, Database)
- Agent validation reports (from all specialist agents)

**Output Contract** (from Integration Orchestrator):
- ✅ Integration validation report (all contracts satisfied)
- ✅ Integration test results (Backend + DB tests pass)
- ✅ E2E test results (full workflow validated)

**Validation**:
- Integration Orchestrator validates:
  - Frontend ↔ Backend: API contracts satisfied
  - Backend ↔ Domain: Domain interfaces called correctly
  - Domain ↔ Persistence: Schema mappings correct
  - Auth: Session flows work end-to-end
  - Errors: Propagate correctly across layers

**Handoff Example**:
```
Integration Orchestrator receives:
- Domain Guardian: Task domain model approved
- Data & Schema Guardian: Schema migration ready
- Backend: API endpoint implemented
- Frontend: UI component implemented
- Test Architect: Unit tests pass

Integration Orchestrator validates:
- POST /api/tasks → TaskService → Domain → Database → Success
- Frontend form → POST /api/tasks → Task appears in UI
- All integration tests pass ✅
```

---

## 3. Execution Rules

### Rule 1: Sequential Execution (CrewAI Pattern)

**Agents execute in order**. Each agent receives output from previous agent.

**Blocking Rule**: If Agent N blocks, Agents N+1 through 9 **DO NOT EXECUTE**.

**Example**:
```
1. Spec Governance validates spec → ✅ PASS
2. Domain Guardian validates domain → ❌ BLOCK (domain pollution detected)
3. Agents 3-9: DO NOT EXECUTE (blocked upstream)

Remediation required before proceeding.
```

---

### Rule 2: Conditional Execution

**Not all agents run for every feature**. Execution depends on feature scope.

**Decision Logic**:
```
Backend Architect runs IF:
  - Backend code changes required
  - API endpoints modified
  - Application logic updated

Frontend Architect runs IF:
  - UI changes required
  - Frontend components modified
  - User-facing changes

Better Auth Guardian runs IF:
  - Auth requirements change
  - New protected resources added
  - Session handling modified

Error & Reliability Architect: ALWAYS runs (review)
Test Strategy Architect: ALWAYS runs (TDD validation)
Integration Orchestrator: ALWAYS runs (integration validation)
```

---

### Rule 3: Iterative Re-Validation

**If implementation violates contracts**, loop back to violating agent for re-validation.

**Example (Integration Orchestrator detects Backend violates Domain)**:
```
Step 8: Integration Orchestrator runs integration tests
Result: ❌ Backend reimplements domain validation logic

Action: Loop back to Step 2 (Domain Guardian)
- Domain Guardian reviews Backend implementation
- Blocks Backend for domain pollution
- Backend remediates (calls domain instead of duplicating logic)
- Re-execute Steps 4-9
```

---

### Rule 4: Blocking Takes Precedence

**If any agent with blocking authority blocks, ALL downstream work stops**.

**Blocking Agents** (can halt workflow):
1. Spec Governance Enforcer
2. Domain Guardian
3. Data & Schema Guardian
4. Better Auth Guardian
5. Test Strategy Architect
6. Integration Orchestrator

**Non-Blocking Agents** (advisory only):
- Error & Reliability Architect
- Backend Architect
- Frontend Architect

---

## 4. Invocation Decision Tree

Use this decision tree to determine which agents to invoke:

```
START: User requests feature
│
├─ Has approved spec? ──NO──> Invoke: Spec Governance Enforcer → BLOCK until spec exists
│
└─ YES
   │
   ├─ Domain model changes? ──YES──> Invoke: Domain Guardian
   │                          NO──> Skip Domain Guardian
   │
   ├─ Database schema changes? ──YES──> Invoke: Data & Schema Guardian
   │                             NO──> Skip Data & Schema Guardian
   │
   ├─ Backend changes? ──YES──> Invoke: Backend Architect
   │                     NO──> Skip Backend Architect
   │
   ├─ Frontend changes? ──YES──> Invoke: Frontend Architect
   │                      NO──> Skip Frontend Architect
   │
   ├─ Auth changes? ──YES──> Invoke: Better Auth Guardian
   │                  NO──> Skip Better Auth Guardian
   │
   ├─ ALWAYS Invoke: Error & Reliability Architect (review)
   │
   ├─ ALWAYS Invoke: Test Strategy Architect (TDD validation)
   │
   └─ ALWAYS Invoke: Integration Orchestrator (integration validation)

END: Feature complete if all validations pass
```

---

## 5. Phase-Based Protocol Constraints

### Phase 1 (Hackathon)

**Execution Model**:
- ✅ Sequential execution (CrewAI Process.sequential)
- ✅ Manual agent invocation
- ✅ User approval at each blocking point
- ✅ Manual integration validation

**Blocking Points**:
- Spec Governance blocks: Until spec approved
- Domain Guardian blocks: Until domain pollution removed
- Test Strategy Architect blocks: Until tests written first

**Workflow Example (Phase 1)**:
```
1. User: "Add priority to tasks"
2. Spec Governance: Check spec.md → BLOCK (no spec) → User creates spec
3. Domain Guardian: Validate priority in domain → APPROVE
4. Data & Schema Guardian: Design migration → User approves migration
5. Backend: Implement API → Test Architect blocks (no tests) → Write tests first
6. Frontend: Implement UI → Integration Orchestrator validates end-to-end
7. COMPLETE
```

---

### Phase 2+ (Production)

**Execution Model**:
- ✅ Automated agent invocation in CI/CD
- ✅ Parallel execution where safe (Backend + Frontend can run concurrently if API contract pre-defined)
- ✅ Automated integration tests in pipeline
- ✅ Pre-commit hooks enforce TDD

**Blocking Points** (Automated):
- CI/CD blocks merge: If tests missing, coverage insufficient
- CI/CD blocks deployment: If integration tests fail
- Pre-commit blocks commit: If TDD violated

**Workflow Example (Phase 2+)**:
```
1. Developer: Creates branch, writes spec
2. CI/CD: Runs Spec Governance validation automatically
3. Developer: Writes tests (TDD), implements feature
4. Pre-commit hook: Validates tests exist, blocks commit if not
5. CI/CD: Runs all agent validations automatically
6. CI/CD: Blocks merge if any validation fails
7. Deployment: Only if all validations pass
```

---

## 6. Quick Reference: Agent Execution Checklist

Before invoking agents, confirm:

**Pre-Execution**:
- [ ] Feature requirements clear
- [ ] Affected layers identified (Frontend, Backend, Domain, DB, Auth)
- [ ] Execution sequence determined (which agents needed)

**During Execution**:
- [ ] Spec Governance validates spec exists
- [ ] Domain Guardian validates domain purity
- [ ] Data & Schema Guardian validates schema alignment
- [ ] Backend/Frontend implement using contracts
- [ ] Better Auth Guardian validates auth security
- [ ] Error Architect reviews error handling
- [ ] Test Architect validates TDD compliance
- [ ] Integration Orchestrator validates integration

**Post-Execution**:
- [ ] All blocking validations passed
- [ ] Integration tests pass
- [ ] E2E tests pass
- [ ] PHR created for work completed
- [ ] ADR created if architecturally significant

---

## 7. Common Execution Patterns

### Pattern 1: Simple Feature (No Schema Changes)

**Example**: "Update task title validation (frontend + backend)"

**Execution**:
```
1. Spec Governance: Validate spec → ✅
2. Domain Guardian: Validate validation rule → ✅
3. Data & Schema Guardian: SKIP (no schema change)
4. Backend Architect: Update validation → ✅
5. Frontend Architect: Update error message → ✅
6. Better Auth Guardian: SKIP (no auth change)
7. Error Architect: Review error handling → ⚠️ Advisory
8. Test Architect: Validate tests → ✅
9. Integration Orchestrator: E2E validation → ✅
```

**Total Agents Invoked**: 6 of 9

---

### Pattern 2: New Feature (Full Stack)

**Example**: "Add task priority (domain + schema + backend + frontend)"

**Execution**:
```
1. Spec Governance: Validate spec → ✅
2. Domain Guardian: Add priority to domain → ✅
3. Data & Schema Guardian: Migration for priority column → ✅
4. Backend Architect: API endpoint for priority → ✅
5. Frontend Architect: Priority dropdown UI → ✅
6. Better Auth Guardian: SKIP (no auth change)
7. Error Architect: Review error taxonomy → ⚠️ Advisory
8. Test Architect: Validate TDD compliance → ✅
9. Integration Orchestrator: E2E priority workflow → ✅
```

**Total Agents Invoked**: 8 of 9

---

### Pattern 3: Auth Feature

**Example**: "Protect task editing (only owner can edit)"

**Execution**:
```
1. Spec Governance: Validate spec → ✅
2. Domain Guardian: Add ownership concept to Task → ✅
3. Data & Schema Guardian: Add user_id foreign key → ✅
4. Backend Architect: Ownership check before update → ✅
5. Frontend Architect: Hide edit button for non-owners → ✅
6. Better Auth Guardian: Define ownership validation → ✅
7. Error Architect: Review 403 Forbidden errors → ⚠️ Advisory
8. Test Architect: Validate ownership tests → ✅
9. Integration Orchestrator: E2E auth workflow → ✅
```

**Total Agents Invoked**: 9 of 9 (all agents)

---

## 8. Troubleshooting Agent Execution

### Problem: Agent blocks unexpectedly

**Solution**:
1. Review agent's blocking criteria (see AGENT_OWNERSHIP_MATRIX.md)
2. Validate agent received correct inputs from previous agent
3. Check for violation of agent's invariants
4. Remediate violation
5. Re-execute from blocking agent

---

### Problem: Agents disagree (conflict)

**Solution**:
1. Consult AGENT_OWNERSHIP_MATRIX.md Section 4 (Conflict Resolution)
2. Apply priority rules (Spec > Domain > Test > Auth > Schema > Integration)
3. If unresolved, escalate to Integration Orchestrator
4. If still unresolved, escalate to User with options

---

### Problem: Circular dependency detected

**Solution**:
1. Sequential execution prevents circular dependencies by design
2. If Agent A needs Agent B output, but B needs A output: ESCALATE to Integration Orchestrator
3. Integration Orchestrator resolves by defining which executes first
4. Document resolution as ADR

---

## Summary

This protocol ensures:
- ✅ **Predictable execution**: Same sequence every time
- ✅ **Clear contracts**: Each agent knows what it receives and must produce
- ✅ **No gaps**: All layers validated before deployment
- ✅ **No conflicts**: Priority rules and conflict resolution defined
- ✅ **Scalable**: Conditional execution prevents unnecessary work

**Golden Rule**: Follow the sequence. Respect blocking authority. Validate contracts.

---

---

## 9. LifeOps Event-Driven Protocol

LifeOps agents operate on a fundamentally different execution model than the development pipeline. Instead of sequential invocation, LifeOps agents are **event-driven** — triggered by external events detected by watchers.

### 9.1 LifeOps Execution Flow

```
┌─────────────────────────────────────────────────────────────────┐
│  LIFEOPS EVENT-DRIVEN EXECUTION FLOW                            │
└─────────────────────────────────────────────────────────────────┘

External Event
  │
  ├─ Email received ──────────> Email Watcher ──> event_bus
  ├─ Transaction detected ────> Finance Watcher ──> event_bus
  ├─ Calendar event upcoming ─> Calendar Watcher ──> event_bus
  ├─ File changed ────────────> File Watcher ──> event_bus
  │
  ↓
Event Bus (routes to appropriate agent)
  │
  ├─ email.received ──────────> Communication Agent
  │   ├─ finance content? ────> Route to Finance Agent
  │   ├─ social inquiry? ─────> Route to Social Media Agent
  │   └─ general message ─────> Draft response (HITL)
  │
  ├─ finance.transaction ─────> Finance Agent
  │   └─ Record/categorize ───> HITL gate if above threshold
  │
  ├─ calendar.upcoming ───────> Communication Agent
  │   └─ Prepare/remind ──────> Notify human
  │
  ├─ schedule.post_due ───────> Social Media Agent
  │   └─ Publish approved ────> HITL gate
  │
  └─ system.health_check ────> Monitoring Agent
      └─ Assess + report ─────> Alert if issues found

  ↓
Policy Enforcement Gate
  │
  ├─ ALLOW ────> Execute action
  ├─ DENY ─────> Log + notify human
  └─ REQUIRE_APPROVAL ──> HITL Queue
      │
      ├─ Approved ──> Execute action
      └─ Denied ───> Log + notify agent

  ↓
Audit Trail (every action logged)

  ↓
Monitoring Agent (tracks health continuously)
```

### 9.2 LifeOps Agent Handoff Contracts

#### Event → Communication Agent

**Input Contract:**
- Event type: `email.received` or `slack.message`
- Message content, sender, channel, timestamp
- Thread context (if reply)

**Output Contract:**
- Classification: urgency, category, required action
- Draft response (if reply needed)
- Routing decision (if cross-domain)
- HITL approval request (if sending)

#### Communication Agent → Finance Agent

**Input Contract:**
- Original message with financial content
- Extracted data: amounts, vendor, due dates, invoice numbers
- Routing reason and confidence score

**Output Contract:**
- Financial action taken (or queued for approval)
- Confirmation message for Communication Agent to relay

#### Communication Agent → Social Media Agent

**Input Contract:**
- Social media inquiry or content request
- Platform context
- Sender/requester information

**Output Contract:**
- Draft content or response
- Scheduling recommendation
- HITL approval request

#### Monitoring Agent → All Agents

**Input Contract:**
- Continuous health check (reads agent logs/metrics)

**Output Contract:**
- Health report (written to `vault/state/health.yaml`)
- Alerts (sent via notification skill)
- Safety blocks (if CRITICAL thresholds breached)

#### Audit Agent → All Agents

**Input Contract:**
- Audit trail files from all agents
- Approval records from HITL queue
- Policy rules to verify against

**Output Contract:**
- Compliance report
- Violation alerts
- Blocking decisions (if systematic violations found)

### 9.3 LifeOps vs Dev Pipeline Isolation

| Aspect | Dev Pipeline | LifeOps Layer |
|--------|-------------|---------------|
| Execution model | Sequential (CrewAI) | Event-driven (parallel) |
| Trigger | User request | External event |
| Agent count | 10 | 5 |
| Skill count | 15 | 13 + 3 system |
| Invocation order | Fixed sequence | Event-determined |
| Blocking | Pipeline halt | Individual action block |
| Cross-layer calls | No | No |
| Shared governance | Spec Governance, Test Strategy | Monitoring Agent, Audit Agent |

**Isolation Rule:** Dev pipeline agents NEVER directly invoke LifeOps agents. LifeOps agents NEVER directly invoke dev pipeline agents. Cross-layer coordination happens through the human or shared governance agents.

### 9.4 LifeOps Phase-Based Constraints

#### Phase 1 (Hackathon)
- ✅ Event-driven agent invocation
- ✅ Manual watcher triggering
- ✅ HITL approval for all HIGH/CRITICAL actions
- ✅ File-based audit trail
- ❌ No automated scheduling (manual only)
- ❌ No auto-learning from feedback

#### Phase 2+ (Production)
- ✅ Automated watchers with health monitoring
- ✅ Smart routing with confidence scoring
- ✅ Configurable auto-approval for LOW risk
- ✅ Dashboard for monitoring and approvals
- ✅ Analytics and trend analysis
- ✅ Feedback loop for continuous improvement

---

**References**:
- Agent definitions: `.claude/agents/`
- Ownership matrix: `.claude/AGENT_OWNERSHIP_MATRIX.md`
- Integration Orchestrator: `.claude/agents/integration-orchestrator.md`
- LifeOps agents: `.claude/agents/communication-agent.md`, `finance-agent.md`, `social-media-agent.md`, `monitoring-agent.md`, `audit-agent.md`
