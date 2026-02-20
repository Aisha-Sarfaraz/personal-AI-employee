# Agent Ownership & Overlap Resolution Matrix

**Version**: 1.0
**Last Updated**: 2026-01-02
**Status**: AUTHORITATIVE GOVERNANCE DOCUMENT

This document is the **single source of truth** for agent responsibilities, overlap resolution, and blocking authority in the TODO app agent architecture.

---

## Table of Contents

1. [Agent Ownership Matrix](#agent-ownership-matrix)
2. [Overlap Resolution Rules](#overlap-resolution-rules)
3. [Blocking Authority Matrix](#blocking-authority-matrix)
4. [Conflict Resolution Protocol](#conflict-resolution-protocol)
5. [Quick Reference Table](#quick-reference-table)

---

## 1. Agent Ownership Matrix

### 1.1 Validation Responsibilities

| Responsibility | Owner Agent | Scope | Other Agents (Role) |
|---------------|-------------|-------|---------------------|
| **Domain Validation** | Domain Guardian | Business rules, domain invariants, entity state validity | Backend Architect (calls domain validation), Test Strategy Architect (tests domain validation) |
| **Input Validation** | Backend Architect | API request format, data types, required fields | Domain Guardian (NOT involved - this is application boundary), Frontend Architect (client-side UX validation only) |
| **Schema Validation** | Data & Schema Guardian | Database constraints, referential integrity, data types | Domain Guardian (defines domain model that schema must match) |
| **Contract Validation** | Integration Orchestrator | Cross-layer contracts (Frontend ↔ Backend ↔ Domain ↔ Persistence) | All specialist agents (provide contracts to validate) |

**Resolution Rule**:
- Domain validation happens in **Domain Guardian ONLY**
- Backend input validation happens **BEFORE** calling domain
- Schema constraints are **defensive** (last line of defense)
- Integration Orchestrator validates contracts **END-TO-END**

**Example (Task Creation)**:
```
1. Frontend: UX validation (show field required) - Frontend Architect
2. Backend: Input guards (check title not null) - Backend Architect
3. Domain: Business rules (title max 200 chars) - Domain Guardian
4. Database: Constraints (title VARCHAR 200 NOT NULL) - Data & Schema Guardian
5. Integration: Verify all layers work together - Integration Orchestrator
```

---

### 1.2 Error Handling Responsibilities

| Responsibility | Owner Agent | Scope | Other Agents (Role) |
|---------------|-------------|-------|---------------------|
| **Error Taxonomy Design** | Error & Reliability Architect | System-wide error classification, observability strategy | All agents (implement using taxonomy) |
| **Domain Error Semantics** | Domain Guardian | Domain-specific errors (ValidationError, StateTransitionError) | Error Architect (includes in taxonomy) |
| **Backend Error Handling** | Backend Architect | Application error mapping, error responses (400, 401, 403, 500) | Error Architect (designs taxonomy used) |
| **Frontend Error UX** | Frontend Architect | User-facing error messages, error states, recovery actions | Error Architect (defines error contracts) |
| **Error Propagation** | Integration Orchestrator | Validates errors flow correctly across layers | Error Architect (designs propagation strategy) |

**Resolution Rule**:
- Error Architect **DESIGNS** error taxonomy and observability strategy
- Specialist agents **IMPLEMENT** error handling using that taxonomy
- Integration Orchestrator **VALIDATES** error propagation end-to-end

**Example (Validation Error Flow)**:
```
1. Domain raises: DomainValidationError("Title cannot be empty")
2. Backend maps to: 400 Bad Request with {"error": "validation_error", "field": "title"}
3. Frontend displays: "Title is required" (user-friendly message)
4. Error Architect reviews: Taxonomy correct, observability in place
5. Integration Orchestrator validates: Error flows correctly from domain → user
```

---

### 1.3 Authentication & Authorization Responsibilities

| Responsibility | Owner Agent | Scope | Other Agents (Role) |
|---------------|-------------|-------|---------------------|
| **Auth Requirements Definition** | Better Auth Guardian | Better Auth configuration, session contracts, permission model | Backend/Frontend (implement using Better Auth APIs) |
| **Backend Session Verification** | Backend Architect | Calling `auth.api.getSession()`, extracting user_id | Better Auth Guardian (defines how to call Better Auth) |
| **Frontend Auth State** | Frontend Architect | `useSession()` hook, auth loading/error states, redirects | Better Auth Guardian (defines auth contracts) |
| **Application Ownership Logic** | Backend Architect | Checking if `session.user.id == resource.owner_id` | Domain Guardian (defines ownership concept in domain) |
| **Auth Integration Validation** | Integration Orchestrator | Validates auth flows work end-to-end | Better Auth Guardian (provides auth contracts) |

**Resolution Rule**:
- Better Auth Guardian **DEFINES** auth requirements and Better Auth usage
- Backend Architect **IMPLEMENTS** session verification + ownership checks
- Frontend Architect **IMPLEMENTS** auth state management and UX
- Domain Guardian **DEFINES** ownership concept (but doesn't enforce auth)

**Example (Protected Resource Access)**:
```
1. Better Auth Guardian defines: Use auth.api.getSession() to verify user
2. Backend implements:
   - session = auth.api.getSession()
   - if not session: return 401 Unauthorized
   - task = get_task(task_id)
   - if task.user_id != session.user.id: return 403 Forbidden
3. Frontend implements:
   - const { data: session } = useSession()
   - if (!session) redirect to /login
4. Domain Guardian defines: Task has user_id attribute (ownership concept)
5. Integration Orchestrator validates: Login → create task → only owner can edit
```

---

### 1.4 Testing Responsibilities

| Responsibility | Owner Agent | Scope | Other Agents (Role) |
|---------------|-------------|-------|---------------------|
| **TDD Enforcement** | Test Strategy Architect | Red-Green-Refactor cycle, blocks untested code | All implementation agents (must have tests before implementing) |
| **Unit Test Strategy** | Test Strategy Architect | Test boundaries, fixtures, mocks | All agents (write unit tests for their code) |
| **Integration Test Strategy** | Integration Orchestrator | Integration test design, cross-layer validation | Test Strategy Architect (provides testing philosophy) |
| **E2E Test Execution** | Integration Orchestrator | End-to-end workflow validation | Test Strategy Architect (defines E2E test philosophy) |
| **Test Coverage Validation** | Test Strategy Architect | Coverage requirements, quality metrics | Integration Orchestrator (validates integration test coverage) |

**Resolution Rule**:
- Test Strategy Architect **OWNS** TDD enforcement and unit test architecture
- Integration Orchestrator **OWNS** integration/E2E test execution
- Test Strategy Architect **BLOCKS** if TDD violated
- Integration Orchestrator **BLOCKS** if integration tests fail

**Example (New Feature Testing)**:
```
1. Test Strategy Architect enforces: Write unit tests FIRST (Red phase)
2. User approves tests
3. Backend/Frontend implement (Green phase)
4. Test Strategy Architect validates: Tests pass, coverage meets minimum
5. Integration Orchestrator executes: Integration tests for API + DB
6. Integration Orchestrator executes: E2E test for full workflow
```

---

### 1.5 Schema & Persistence Responsibilities

| Responsibility | Owner Agent | Scope | Other Agents (Role) |
|---------------|-------------|-------|---------------------|
| **Database Schema Design** | Data & Schema Guardian | Table structure, columns, types, constraints | Domain Guardian (provides domain model to map) |
| **Migration Creation** | Data & Schema Guardian | Upgrade/downgrade scripts, versioning | Backend Architect (uses persistence contracts) |
| **Domain Model Definition** | Domain Guardian | Entity attributes, relationships, invariants | Data & Schema Guardian (creates schema to match) |
| **Persistence Coordination** | Backend Architect | Calling repository methods, transaction management | Data & Schema Guardian (provides repository contracts) |
| **Schema ↔ Domain Alignment** | Integration Orchestrator | Validates domain objects map correctly to DB | Data & Schema Guardian + Domain Guardian (validate independently) |

**Resolution Rule**:
- Domain Guardian **DEFINES** domain model FIRST
- Data & Schema Guardian **DESIGNS** schema to match domain
- Backend Architect **COORDINATES** persistence using schema contracts
- Integration Orchestrator **VALIDATES** end-to-end mapping

**Example (Add Priority Field)**:
```
1. Domain Guardian defines: Task.priority (enum: low, medium, high)
2. Data & Schema Guardian designs: tasks.priority (VARCHAR(20), CHECK constraint)
3. Data & Schema Guardian creates: Migration to add column
4. Backend Architect updates: Repository to persist priority field
5. Integration Orchestrator validates: Task with priority persists and retrieves correctly
```

---

## 2. Overlap Resolution Rules

### 2.1 Validation Overlap Resolution

**Overlap**: Domain validation vs. Backend input validation

**Resolution**:
- **Backend Input Validation** (Backend Architect):
  - Validates request format (required fields present, correct types)
  - Happens at API boundary BEFORE domain is called
  - Example: Check that `title` field exists in request

- **Domain Validation** (Domain Guardian):
  - Validates business rules and invariants
  - Happens INSIDE domain logic
  - Example: Check that `title` is not empty and max 200 chars

**Rule**: Backend validates the request structure; Domain validates business semantics.

**Who Owns**:
- Backend Architect owns input guards
- Domain Guardian owns domain validation
- Backend NEVER reimplements domain validation

---

### 2.2 Error Handling Overlap Resolution

**Overlap**: Error taxonomy design vs. error implementation

**Resolution**:
- **Error & Reliability Architect**:
  - DESIGNS error taxonomy (error types, codes, observability strategy)
  - ADVISES on error handling best practices
  - DOES NOT implement error handling code

- **Backend/Frontend Architects**:
  - IMPLEMENT error handling using Error Architect's taxonomy
  - Write error mapping code (domain errors → HTTP status codes)
  - Write user-facing error messages

**Rule**: Error Architect designs; specialist agents implement.

**Who Blocks**:
- Error Architect: ADVISES only (does not block)
- Integration Orchestrator: BLOCKS if error propagation is broken

---

### 2.3 Auth Overlap Resolution

**Overlap**: Auth requirements vs. auth implementation

**Resolution**:
- **Better Auth Guardian**:
  - DEFINES auth requirements (session model, permissions)
  - SPECIFIES how to use Better Auth APIs
  - DOES NOT write implementation code

- **Backend Architect**:
  - IMPLEMENTS session verification: `session = auth.api.getSession()`
  - IMPLEMENTS ownership checks: `task.user_id == session.user.id`

- **Frontend Architect**:
  - IMPLEMENTS auth state: `const { data: session } = useSession()`
  - IMPLEMENTS auth UX (login redirects, protected routes)

**Rule**: Better Auth Guardian defines contracts; Backend/Frontend implement them.

**Who Blocks**:
- Better Auth Guardian: BLOCKS if security requirements not met
- Backend/Frontend Architects: Cannot block others

---

### 2.4 Testing Overlap Resolution

**Overlap**: Unit test strategy vs. integration test execution

**Resolution**:
- **Test Strategy Architect**:
  - OWNS TDD enforcement (Red-Green-Refactor)
  - OWNS unit test architecture (fixtures, mocks, boundaries)
  - DEFINES test coverage requirements
  - BLOCKS if TDD violated or coverage insufficient

- **Integration Orchestrator**:
  - OWNS integration test execution (Backend + DB tests)
  - OWNS E2E test execution (full stack tests)
  - DEFINES integration test scenarios
  - BLOCKS if integration/E2E tests fail

**Rule**: Test Architect enforces TDD and unit tests; Integration Orchestrator executes integration/E2E tests.

**Who Blocks**:
- Test Strategy Architect: BLOCKS untested code
- Integration Orchestrator: BLOCKS failed integration

---

## 3. Blocking Authority Matrix

| Agent | Blocking Authority | Advisory Authority | Cannot Block |
|-------|-------------------|-------------------|--------------|
| **Spec Governance Enforcer** | ✅ No approved spec<br>✅ Spec violations<br>✅ Missing ADRs for significant decisions | ⚠️ Incomplete specs<br>⚠️ Suboptimal spec structure | Implementation details (delegates to specialists) |
| **Domain Guardian** | ✅ Domain pollution (infrastructure in domain)<br>✅ Domain invariant violations<br>✅ Invalid state transitions | ⚠️ Suboptimal domain design<br>⚠️ Missing domain events | Persistence strategy, API design, UI concerns |
| **Data & Schema Guardian** | ✅ Schema conflicts with domain model<br>✅ Migration has no rollback<br>✅ Data loss without approval | ⚠️ Missing indexes<br>⚠️ Denormalization choices | Domain model design, application logic |
| **Backend Architect** | ❌ Cannot block others | ⚠️ Inefficient persistence usage<br>⚠️ Poor error handling | Can be blocked by Domain, Schema, Integration, Test |
| **Frontend Architect** | ❌ Cannot block others | ⚠️ Accessibility issues<br>⚠️ Poor UX patterns | Can be blocked by Integration, Test |
| **Better Auth Guardian** | ✅ Security requirements not met<br>✅ Session handling violations | ⚠️ Suboptimal auth UX<br>⚠️ Missing auth edge cases | Implementation details (delegates to Backend/Frontend) |
| **Error & Reliability Architect** | ❌ Cannot block (advisory only) | ⚠️ Error taxonomy violations<br>⚠️ Missing observability<br>⚠️ Poor error messages | All implementation (designs, does not implement) |
| **Integration Orchestrator** | ✅ Cross-layer contract violations<br>✅ Integration test failures<br>✅ Required agent skipped | ⚠️ Incomplete integration test coverage | Individual agent implementations (coordinates, does not dictate) |
| **Test Strategy Architect** | ✅ TDD violations (no tests before code)<br>✅ Coverage below minimums<br>✅ Critical paths untested | ⚠️ Test quality issues<br>⚠️ Brittle tests | Implementation details (enforces testing discipline) |

**Legend**:
- ✅ **BLOCKING**: Work cannot proceed until remediated
- ⚠️ **ADVISORY**: Should be fixed but doesn't block
- ❌ **Cannot Block**: Agent provides guidance but cannot halt work

---

## 4. Conflict Resolution Protocol

### 4.1 Agent Disagreement Protocol

**Scenario**: Two agents disagree on an approach (e.g., Domain Guardian says "X violates domain purity" but Backend Architect says "X is necessary for performance")

**Resolution Steps**:

1. **Document Conflict**:
   - Agent 1 position: [State concern and rationale]
   - Agent 2 position: [State need and rationale]
   - Blocking status: [Which agent can block]

2. **Check Blocking Authority**:
   - If blocking agent disagrees: **WORK IS BLOCKED**
   - If non-blocking agent disagrees: **ADVISORY WARNING ISSUED**

3. **Escalate to Integration Orchestrator**:
   - Integration Orchestrator reviews both positions
   - Evaluates impact on system integration
   - Provides recommendation

4. **Escalate to User** (if unresolved):
   - Present both positions with tradeoffs
   - Provide Integration Orchestrator recommendation
   - User makes final decision
   - Document decision as ADR if architecturally significant

**Example**:
```
Conflict: Backend wants to cache domain objects for performance
- Domain Guardian: BLOCKS - "Caching violates domain purity; belongs in infrastructure"
- Backend Architect: Advises - "Performance requires caching"
- Resolution: Domain Guardian's block stands
- Alternative: Implement caching in Backend layer, not in domain entities
```

---

### 4.2 Priority Rules

When multiple agents have overlapping concerns, apply this priority order:

**Priority 1 (Highest)**: Spec Governance Enforcer
- Rationale: No work without specs (SDD fundamental principle)
- Overrides: All other agents

**Priority 2**: Domain Guardian
- Rationale: Domain correctness is foundation; everything else builds on it
- Overrides: Backend, Frontend, Schema (but not Spec Governance)

**Priority 3**: Test Strategy Architect
- Rationale: TDD is non-negotiable per CLAUDE.md
- Overrides: Backend, Frontend (but not Spec Governance or Domain Guardian)

**Priority 4**: Better Auth Guardian
- Rationale: Security cannot be compromised
- Overrides: Backend, Frontend, Error Architect

**Priority 5**: Data & Schema Guardian
- Rationale: Data integrity is critical
- Overrides: Backend, Error Architect

**Priority 6**: Integration Orchestrator
- Rationale: Integration failures block deployment
- Overrides: Error Architect (advises on integration issues)

**Priority 7**: Backend Architect, Frontend Architect
- Rationale: Implementation specialists; can be blocked by governance agents
- Cannot override: Any governance agent

**Priority 8 (Lowest)**: Error & Reliability Architect
- Rationale: Advisory role; designs but does not block
- Cannot block: Any agent

---

### 4.3 Deadlock Resolution

**Scenario**: Circular dependency (Agent A blocks Agent B, Agent B blocks Agent C, Agent C blocks Agent A)

**Resolution**:
1. **Identify circular dependency**
2. **Apply priority rules** (higher priority wins)
3. **If same priority**: Escalate to Integration Orchestrator
4. **If unresolved**: Escalate to User with full context

**Deadlock Prevention**:
- Agents must declare dependencies upfront
- Integration Orchestrator validates no circular dependencies in workflow
- Execution sequence prevents circular blocks (sequential workflow)

---

## 5. Quick Reference Table

### 5.1 Responsibility Assignment (RACI-style)

| Responsibility | Responsible (R) | Accountable (A) | Consulted (C) | Informed (I) |
|----------------|----------------|-----------------|---------------|--------------|
| **Domain Model Design** | Domain Guardian (R/A) | - | Data & Schema Guardian (C) | Backend, Frontend (I) |
| **Database Schema Design** | Data & Schema Guardian (R/A) | - | Domain Guardian (C) | Backend (I) |
| **API Contract Definition** | Backend Architect (R/A) | - | Domain Guardian, Frontend (C) | Integration Orchestrator (I) |
| **Auth Strategy** | Better Auth Guardian (R/A) | - | Backend, Frontend (C) | - |
| **Error Taxonomy** | Error & Reliability Architect (R/A) | - | All agents (C) | - |
| **TDD Enforcement** | Test Strategy Architect (R/A) | - | All agents (C) | Integration Orchestrator (I) |
| **Integration Validation** | Integration Orchestrator (R/A) | - | All specialist agents (C) | Spec Governance (I) |
| **Spec Validation** | Spec Governance Enforcer (R/A) | - | All agents (C) | - |

**Legend**:
- **R (Responsible)**: Does the work
- **A (Accountable)**: Ultimately answerable for completion
- **C (Consulted)**: Provides input
- **I (Informed)**: Kept up-to-date

---

### 5.2 Decision Authority Quick Lookup

| Decision Type | Decision Owner | Must Consult | Can Block |
|---------------|---------------|--------------|-----------|
| Domain model changes | Domain Guardian | Data & Schema Guardian | Domain Guardian |
| Database schema changes | Data & Schema Guardian | Domain Guardian | Data & Schema Guardian |
| API contract changes | Backend Architect | Frontend Architect, Domain Guardian | Domain Guardian (if violates domain) |
| Auth implementation | Backend/Frontend Architects | Better Auth Guardian | Better Auth Guardian (if security issue) |
| Error handling approach | Backend/Frontend Architects | Error & Reliability Architect | None (Error Architect advises only) |
| Test strategy | Test Strategy Architect | Integration Orchestrator | Test Strategy Architect (if TDD violated) |
| Integration approach | Integration Orchestrator | All specialist agents | Integration Orchestrator (if contracts broken) |
| Spec completeness | Spec Governance Enforcer | Domain Guardian, Backend/Frontend | Spec Governance Enforcer |

---

## 6. Conflict Resolution Examples

### Example 1: Domain Validation vs Backend Input Validation

**Conflict**: "Where should we validate that task title is not empty?"

**Resolution**:
- **Backend Input Validation** (Backend Architect): Check that `title` field exists in request (structural validation)
- **Domain Validation** (Domain Guardian): Check that `title` is not empty string and max 200 chars (business rule)
- **Outcome**: Both happen, but in sequence: Backend input guards → Domain business rules

**No Conflict**: These are complementary layers of defense.

---

### Example 2: Error Message Ownership

**Conflict**: "Who decides what error message users see when task creation fails?"

**Resolution**:
- **Domain Guardian**: Raises `DomainValidationError("Title cannot be empty")`
- **Backend Architect**: Maps to HTTP 400 with error code: `validation_error`
- **Frontend Architect**: Displays user-friendly message: "Please enter a task title"
- **Error & Reliability Architect**: Designed taxonomy that Backend/Frontend use

**Outcome**:
- Domain owns domain error semantics
- Backend owns HTTP error mapping
- Frontend owns user-facing messages
- Error Architect designed the taxonomy all three use

**No Conflict**: Each layer has clear ownership.

---

### Example 3: Session Verification vs Ownership Check

**Conflict**: "Who checks if user can edit a task?"

**Resolution**:
- **Better Auth Guardian**: Defines how to verify session exists: `auth.api.getSession()`
- **Backend Architect**: Implements two-step check:
  1. Session verification: `session = auth.api.getSession()` → 401 if none
  2. Ownership check: `task.user_id == session.user.id` → 403 if mismatch
- **Domain Guardian**: Defines `Task.user_id` attribute (ownership concept in domain)

**Outcome**:
- Better Auth Guardian: Defines auth contracts
- Backend Architect: Implements session check + ownership check
- Domain Guardian: Defines ownership concept (does NOT enforce auth)

**No Conflict**: Clear separation of concerns.

---

## 7. Governance Principles

### Principle 1: Separation of Design vs Implementation

**Agents that DESIGN** (cannot block implementation details):
- Error & Reliability Architect (designs error taxonomy)
- Better Auth Guardian (defines auth contracts)

**Agents that IMPLEMENT**:
- Backend Architect
- Frontend Architect

**Governance**: Designers define contracts; implementers build using those contracts.

---

### Principle 2: Blocking Authority Hierarchy

**Can Block Widely**:
- Spec Governance Enforcer (blocks all work without specs)
- Domain Guardian (blocks domain pollution)
- Test Strategy Architect (blocks untested code)

**Can Block Narrowly**:
- Data & Schema Guardian (blocks schema conflicts)
- Better Auth Guardian (blocks security violations)
- Integration Orchestrator (blocks integration failures)

**Cannot Block**:
- Error & Reliability Architect (advisory only)
- Backend Architect (implements, does not govern)
- Frontend Architect (implements, does not govern)

---

### Principle 3: Consultation Before Blocking

**Before blocking, an agent must**:
1. Identify specific violation (reference rule/invariant/principle)
2. Provide concrete remediation steps
3. Consult relevant agents if blocking impacts their domain
4. Document block reason for audit trail

**Example**:
```
Domain Guardian blocks Backend implementation:
- Violation: "Database connection code found in Task entity class"
- Rule: "Domain must remain infrastructure-agnostic"
- Remediation: "Move persistence logic to TaskRepository in infrastructure layer"
- Consulted: Data & Schema Guardian (to provide repository contract)
```

---

## 8. LifeOps Ownership Matrix

### 8.1 LifeOps Responsibility Assignment

| Responsibility | Owner Agent | Scope | Other Agents (Role) |
|---------------|-------------|-------|---------------------|
| **Email Management** | Communication Agent | Read, classify, draft, route emails | Finance Agent (receives financial emails), Social Media Agent (receives social inquiries) |
| **Slack Management** | Communication Agent | Read, draft messages | All agents (may receive routed messages) |
| **Invoice Management** | Finance Agent | Create, track, reconcile invoices in Odoo | Communication Agent (routes invoice emails), Audit Agent (verifies compliance) |
| **Expense Tracking** | Finance Agent | Categorize, record, report expenses | Audit Agent (verifies approval chain) |
| **Social Content** | Social Media Agent | Draft, schedule, analyze social posts | Communication Agent (routes social DMs) |
| **System Health** | Monitoring Agent | Track all component health | All agents (observed passively) |
| **Compliance** | Audit Agent | Verify policy adherence, generate reports | All agents (audited) |
| **Policy Gating** | Monitoring Agent (via policy-enforcement skill) | Validate actions against rules | All agents (gated before execution) |

### 8.2 LifeOps Blocking Authority Matrix

| Agent | Blocking Authority | Advisory Authority | Cannot Block |
|-------|-------------------|-------------------|--------------|
| **Communication Agent** | ❌ Cannot block | ⚠️ Ambiguous message intent<br>⚠️ Unknown sender | All (drafts only, human decides) |
| **Finance Agent** | ✅ Transaction exceeds threshold<br>✅ Missing required data<br>✅ Duplicate transaction | ⚠️ Unusual amounts<br>⚠️ New vendor | Investment/tax decisions |
| **Social Media Agent** | ❌ Cannot block | ⚠️ Content tone concerns<br>⚠️ Hashtag risks | All (drafts only, human publishes) |
| **Monitoring Agent** | ✅ Runaway agent (>100 actions/min)<br>✅ Infinite loop (>10 repeats)<br>✅ Security breach indicators | ⚠️ Degraded performance<br>⚠️ Queue buildup | Business logic decisions |
| **Audit Agent** | ✅ Systematic violations (3+ from same agent)<br>✅ Missing HITL approvals on CRITICAL actions | ⚠️ Minor compliance gaps<br>⚠️ Policy update suggestions | Individual action decisions |

### 8.3 LifeOps RACI Matrix

| Responsibility | Responsible (R) | Accountable (A) | Consulted (C) | Informed (I) |
|----------------|----------------|-----------------|---------------|--------------|
| **Email Response** | Communication (R/A) | - | Human (C) | Audit (I) |
| **Financial Transaction** | Finance (R/A) | - | Human (C) | Audit (I), Monitoring (I) |
| **Social Post** | Social Media (R/A) | - | Human (C) | Audit (I) |
| **System Monitoring** | Monitoring (R/A) | - | Human (C on CRITICAL) | All agents (I) |
| **Compliance Audit** | Audit (R/A) | - | Human (C on violations) | All agents (I) |
| **Policy Enforcement** | Monitoring (R/A) | - | Human (C on DENY) | Requesting agent (I) |
| **Error Recovery** | System skill (R) | Requesting agent (A) | Human (C if escalated) | Monitoring (I) |
| **Notifications** | System skill (R) | Triggering agent (A) | - | Human (I) |

### 8.4 Cross-Layer Conflict Resolution

**Rule: Dev Pipeline and LifeOps are isolated layers.**

| Conflict Scenario | Resolution |
|-------------------|-----------|
| Dev agent needs LifeOps data | Route through human or filesystem (shared vault) |
| LifeOps agent needs dev pipeline action | Human creates spec → dev pipeline executes |
| Both layers modify same file | Filesystem MCP handles locking; last writer wins with audit log |
| Monitoring detects dev pipeline issue | Monitoring alerts human; does NOT invoke dev agents |
| Audit finds dev pipeline violation | Audit reports to human; Spec Governance handles dev compliance |

### 8.5 LifeOps Priority Rules

When LifeOps agents have overlapping concerns:

**Priority 1 (Highest)**: Monitoring Agent (safety overrides)
- Rationale: System safety is non-negotiable
- Can block any agent for CRITICAL safety issues

**Priority 2**: Audit Agent (compliance)
- Rationale: Compliance violations must be addressed
- Can block agents with systematic violations

**Priority 3**: Finance Agent (financial safety)
- Rationale: Financial accuracy and approval are critical
- Blocks unapproved transactions

**Priority 4**: Communication Agent
- Rationale: Communication is high-impact but human-gated
- Cannot block (advisory only)

**Priority 5 (Lowest)**: Social Media Agent
- Rationale: Social media is important but not safety-critical
- Cannot block (advisory only)

---

## 9. Amendment Process

This matrix is a living document (updated 2026-02-16 with LifeOps layer). To amend:

1. **Identify Need**: Agent overlap or conflict not covered by current rules
2. **Propose Amendment**: Document proposed change with rationale
3. **Review**: Integration Orchestrator coordinates review with affected agents
4. **Approve**: User approves amendment
5. **Document as ADR**: Significant changes require ADR
6. **Update Matrix**: Increment version, update last modified date
7. **Communicate**: Notify all agents of change

**Version History**:
- v1.0 (2026-01-02): Initial matrix creation

---

## Summary

This matrix provides **clear, unambiguous** ownership for every responsibility across both Dev Pipeline and LifeOps layers, ensuring:
- ✅ No duplicate work (each responsibility has ONE owner)
- ✅ No gaps (all responsibilities assigned across 15 agents)
- ✅ Clear blocking authority (who can halt work)
- ✅ Conflict resolution protocol (how to resolve disagreements)
- ✅ Governance hierarchy (priority order when conflicts arise)
- ✅ Layer isolation (dev pipeline and LifeOps agents do not cross-invoke)
- ✅ HITL safety matrix (every action classified by risk level)

**Golden Rule**: When in doubt, consult this matrix. If the matrix doesn't cover it, escalate to Integration Orchestrator (dev) or Monitoring Agent (LifeOps) or User.

**Version History**:
- v1.0 (2026-01-02): Initial matrix creation (10 dev agents)
- v2.0 (2026-02-16): Added LifeOps layer (5 agents, 13 skills, 3 system skills)
