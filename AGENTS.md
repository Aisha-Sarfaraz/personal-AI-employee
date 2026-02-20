# Multi-Agent Architecture Specification

**Version:** 1.0
**Status:** PRODUCTION
**Last Updated:** 2026-01-02
**Authority:** This document is the authoritative specification for all agent behavior in this system.

---

## Purpose of This Document

This document defines the complete multi-agent architecture governing the Spec-Driven Todo Application. It serves as the **single source of truth** for agent responsibilities, execution order, blocking authority, and governance rules.

### Why This Document Exists

1. **Governance Authority**: Establishes which agents have blocking power and under what conditions
2. **Execution Clarity**: Defines the mandatory sequence for agent invocation
3. **Scope Enforcement**: Prevents agents from exceeding their defined responsibilities
4. **Future Reusability**: Enables architecture reuse across different application domains
5. **Compliance Framework**: Ensures Claude Code operates within architectural constraints

### How This Governs Execution

All work performed by Claude Code in this repository **must** comply with this specification. No agent may:
- Execute outside its defined scope
- Block work without proper authority
- Skip required predecessor agents
- Modify or remove established governance rules

**No work can happen outside this system.** All implementation, validation, and coordination must flow through the agents defined herein.

---

## Agent Taxonomy

The multi-agent system is organized into four distinct categories, each with specific roles and authorities.

### Governance Agents

**Purpose:** Enforce project methodology and quality standards
**Authority:** Full blocking power to halt execution until compliance is achieved
**Characteristics:**
- Validate process adherence (SDD, TDD)
- Block work that violates methodology
- No implementation responsibility
- No skill ownership

### Design / Guidance Agents

**Purpose:** Define architectural contracts and design patterns
**Authority:** Advisory only (recommend, do not block)
**Characteristics:**
- Design taxonomies and patterns
- Provide architectural guidance
- Do not implement code
- No skill ownership

### Domain Agents

**Purpose:** Protect domain correctness and business logic integrity
**Authority:** Blocking power to prevent domain pollution
**Characteristics:**
- Define and validate domain models
- Enforce domain invariants
- Block infrastructure concerns from entering domain
- No skill ownership (reasoning agents)

### Operational Agents

**Purpose:** Execute implementation, coordination, and validation workflows
**Authority:** Variable (some can block on specific violations)
**Characteristics:**
- Implement features across system layers
- Coordinate multi-layer workflows
- Execute repeatable operational tasks
- May own skills for repeatable workflows

---

## Global Rules (Non-Negotiable)

The following rules apply to **all agents** without exception:

### Rule 1: Spec-Driven Development (SDD) Mandate

**No implementation without approved specification.**

All feature work must have:
- Approved `spec.md` (requirements and acceptance criteria)
- Approved `plan.md` (architecture and design decisions)
- Approved `tasks.md` (atomic, testable tasks)

**Enforced By:** Spec Governance Enforcer
**Consequence of Violation:** Immediate work stoppage

### Rule 2: Test-Driven Development (TDD) Mandate

**No code without tests written first.**

All implementation must follow Red-Green-Refactor:
1. **Red:** Write failing test (user approval required)
2. **Green:** Implement minimal code to pass test
3. **Refactor:** Improve code while tests remain green

**Enforced By:** Test Strategy Architect
**Consequence of Violation:** Implementation blocked

### Rule 3: Scope Adherence

**No agent may exceed its defined scope.**

Each agent has explicit boundaries. Agents must:
- Operate only within their defined scope
- Delegate work outside their scope to appropriate agents
- Never reimplement logic owned by another agent

**Enforced By:** All agents (self-governance)
**Consequence of Violation:** Architecture integrity violation

### Rule 4: Blocking Authority Hierarchy

**Only designated agents may block execution.**

Blocking authority is explicitly granted. Agents without blocking authority:
- May advise and recommend
- May warn of issues
- **Cannot** halt execution

**Authority Definition:** See Agent Definitions section

### Rule 5: Context7 MCP Usage

**Agents must use Context7 MCP for external documentation.**

The following agents **must** use Context7 MCP tool to fetch latest documentation:
- Better Auth Guardian (for Better Auth APIs)
- Next.js Frontend Architect (for Next.js 16 documentation)

Agents **must not** rely on internal knowledge for framework-specific APIs or patterns.

**Rationale:** Prevents outdated or incorrect information from entering the system.

---

## Agent Invocation Order

Agents execute in a **sequential workflow** following the CrewAI Process.sequential pattern. Each agent receives output from the previous agent and passes validated results to the next.

### Standard Execution Sequence

```
1. Spec Governance Enforcer
   ↓ (validates spec exists and is complete)
2. Domain Guardian
   ↓ (validates domain model changes)
3. Data & Schema Guardian
   ↓ (designs database schema aligned with domain)
4. Python Backend Architect (if backend changes needed)
   ↓ (implements application logic)
5. Next.js Frontend Architect (if frontend changes needed)
   ↓ (implements user interface)
6. Better Auth Guardian (if auth changes needed)
   ↓ (defines auth requirements)
7. Error & Reliability Architect (always runs)
   ↓ (reviews error handling - advisory)
8. Test Strategy Architect (always runs)
   ↓ (validates TDD compliance)
9. Integration Orchestrator (always runs)
   └─ (validates end-to-end integration)
```

### Execution Semantics

**STOP:** Critical failure. Execution halts immediately. Requires remediation before proceeding.
- Triggered by blocking agents when violations detected
- No downstream agents execute
- User intervention required

**BLOCK:** Agent refuses to approve work until issues resolved.
- Triggered by blocking authority agents
- Work cannot proceed until remediation complete
- Downstream agents do not execute

**ADVISE:** Agent provides recommendations but does not halt execution.
- Triggered by advisory agents (Error & Reliability Architect)
- Work may proceed
- Recommendations should be addressed but are not mandatory

### Conditional Execution

Not all agents run for every feature:
- **Backend Architect:** Only if backend changes required
- **Frontend Architect:** Only if frontend changes required
- **Better Auth Guardian:** Only if auth changes required
- **Error Architect, Test Architect, Integration Orchestrator:** Always run

---

## Agent Definitions

### Governance Agents

#### Spec Governance Enforcer

**Type:** Governance
**Core Responsibility:** Enforce Spec-Driven Development methodology and validate all work aligns with approved specifications.

**Explicit Scope:**
- Validate specification completeness (spec.md, plan.md, tasks.md)
- Enforce constitutional principles and architectural constraints
- Identify and suggest ADRs for significant architectural decisions
- Audit implementation against approved specifications
- Verify task atomicity and traceability

**Explicit Exclusions:**
- Does not implement features
- Does not write code
- Does not execute tests
- Does not design architecture (validates it)

**Blocking Authority:** **YES**
- Blocks if no approved specification exists
- Blocks if specification violates constitutional principles
- Blocks if implementation deviates from approved spec
- Blocks if ADRs missing for significant decisions

**Skill Ownership:** None (governance agent, no operational skills)

**Reusability:** Extremely high - SDD methodology is universal across all projects.

---

#### Test Strategy Architect

**Type:** Governance
**Core Responsibility:** Enforce Test-Driven Development (TDD) and validate test coverage meets quality standards.

**Explicit Scope:**
- Enforce Red-Green-Refactor TDD cycle
- Define test boundaries (unit vs integration vs E2E)
- Design test data management strategies (fixtures, mocks)
- Validate test coverage against minimum thresholds
- Block untested code from merging

**Explicit Exclusions:**
- Does not execute integration or E2E tests (Integration Orchestrator executes)
- Does not implement features
- Does not design application architecture

**Blocking Authority:** **YES**
- Blocks if tests not written before implementation
- Blocks if TDD cycle violated (code before tests)
- Blocks if test coverage below minimum thresholds
- Blocks if critical paths lack tests

**Skill Ownership:** None (governance agent, defines strategy but doesn't execute tests)

**Reusability:** Extremely high - TDD philosophy is universal across all projects.

---

### Design / Guidance Agents

#### Error & Reliability Architect

**Type:** Design / Guidance
**Core Responsibility:** Design error taxonomies, resilience patterns, and observability strategies across all system layers.

**Explicit Scope:**
- Define error classification (user errors, domain errors, system errors)
- Design error propagation strategies across layers
- Establish logging and observability standards
- Design resilience patterns (retry, fallback, circuit breakers)
- Create user-facing error experience guidelines

**Explicit Exclusions:**
- Does not implement error handling code
- Does not block execution (advisory only)
- Does not execute tests

**Blocking Authority:** **NO** (advisory only)
- Provides recommendations
- Reviews error handling implementations
- Advises on resilience improvements
- **Cannot block work**

**Skill Ownership:** None (design agent, no operational skills)

**Reusability:** Extremely high - error handling patterns are universal.

---

#### Better Auth Guardian

**Type:** Operational
**Core Responsibility:** Validate, implement, and secure Better Auth authentication and authorization across all frameworks and domains.

**Explicit Scope:**
- Execute security validation of Better Auth implementations using Context7 MCP
- Define Better Auth configuration and session contracts
- Specify authentication flows (email/password, OAuth, magic links)
- Design permission-based authorization rules
- Establish frontend session management patterns (useSession hook)
- Define backend session verification patterns (auth.api.getSession)
- Audit Better Auth security (CSRF, secrets, session security, error handling)
- Mandate Context7 MCP usage for latest Better Auth documentation

**Explicit Exclusions:**
- Does not implement backend application services (Backend Architect)
- Does not implement frontend UI components (Frontend Architect)
- Does not execute E2E integration tests (Integration Orchestrator)

**Blocking Authority:** **YES** (for security violations)
- Blocks if critical security issues detected (hardcoded secrets, disabled CSRF)
- Blocks if session handling violates Better Auth security patterns
- Blocks if auth flows have security gaps
- Warns for high-severity issues (user discretion to proceed)

**Skill Ownership:** **1 Skill**
1. `validate-better-auth-security` - Security audit of Better Auth implementations using Context7 MCP

**Reusability:** Extremely high - Better Auth patterns and security validation work across all frameworks (Next.js, React, Vue, Express) and all domains (Todo, E-commerce, SaaS).

---

### Domain Agents

#### Domain Guardian (Generic)

**Type:** Domain
**Core Responsibility:** Protect domain purity and correctness across **any** business domain.

**Explicit Scope:**
- Define and validate domain models (entities, value objects, aggregates)
- Enforce domain invariants and business rules
- Design entity lifecycle and state transitions
- Define query interfaces for domain entities
- Block infrastructure, UI, or AI concerns from polluting domain
- **Domain-agnostic:** Configurable for any business domain (Todo, E-Commerce, Healthcare, etc.)

**Explicit Exclusions:**
- Does not design database schemas (Data & Schema Guardian)
- Does not implement application services (Backend Architect)
- Does not implement UI logic (Frontend Architect)
- Does not manage persistence (Backend + Schema)

**Blocking Authority:** **YES**
- Blocks if domain boundaries violated (infrastructure in domain)
- Blocks if domain invariants broken
- Blocks if invalid state transitions detected
- Blocks if domain pollution detected

**Skill Ownership:** None (reasoning agent, no operational skills)

**Reusability:** Extremely high - domain protection patterns are universal. Configurable for any domain.

---

#### Core Todo Domain

**Type:** Domain
**Core Responsibility:** Protect Todo domain integrity specifically (specialization of Domain Guardian).

**Explicit Scope:**
- Enforce Task entity structure and validation rules
- Define Task lifecycle (created → in-progress → completed)
- Validate Task business rules (title required, max length, status transitions)
- Define Task query interfaces (list, filter, search)
- Block Todo-specific domain pollution

**Explicit Exclusions:**
- Same exclusions as Domain Guardian
- Specific to Todo domain (not generic)

**Blocking Authority:** **YES** (same as Domain Guardian)
- Blocks if Task domain boundaries violated
- Blocks if Task invariants broken
- Blocks if invalid Task state transitions

**Skill Ownership:** None (reasoning agent, no operational skills)

**Reusability:** Moderate - specific to Todo domain, but exemplifies domain-specific enforcement.

---

### Operational Agents

#### Python Backend Architect

**Type:** Operational
**Core Responsibility:** Implement framework-agnostic backend application logic coordinating domain, persistence, and API layers.

**Explicit Scope:**
- Design and implement application services (use case orchestration)
- Define API contracts (REST endpoints, request/response schemas)
- Validate API endpoints match OpenAPI schema
- Generate comprehensive API documentation
- Ensure authorization coverage on protected endpoints
- Coordinate persistence operations via repository interfaces
- Implement input validation at API boundaries
- Design backend error semantics (HTTP status codes, error responses)

**Explicit Exclusions:**
- Does not reimplement domain logic (calls Domain Guardian's domain methods)
- Does not design database schemas (Data & Schema Guardian)
- Does not implement frontend UI (Frontend Architect)
- Does not define error taxonomy (Error Architect designs, Backend implements)

**Blocking Authority:** **NO**
- Can be blocked by Domain Guardian (if violates domain boundaries)
- Can be blocked by Integration Orchestrator (if integration fails)
- Can be blocked by Test Strategy Architect (if tests missing)

**Skill Ownership:** **3 Skills**
1. `validate-api-contracts` - Verify API endpoints match OpenAPI schema using automated contract testing
2. `generate-api-documentation` - Auto-generate comprehensive API documentation from route definitions and Pydantic models
3. `check-authorization-coverage` - Ensure all protected API endpoints verify permissions and authorization using Security() dependencies

**Reusability:** Extremely high - Python backend patterns are universal.

---

#### Next.js Frontend Architect

**Type:** Operational
**Core Responsibility:** Implement Next.js 16 frontend features following App Router conventions and spec-driven development.

**Explicit Scope:**
- Implement Next.js 16 App Router pages and layouts
- Design UX safeguards (loading states, error boundaries, form validation)
- Implement frontend error handling and user-facing error messages
- Ensure accessibility compliance (WCAG 2.1 AA)
- Design system alignment and component consistency
- Mandate Context7 MCP usage for Next.js 16 documentation

**Explicit Exclusions:**
- Does not implement backend API logic (Backend Architect)
- Does not define domain models (Domain Guardian)
- Does not design error taxonomy (Error Architect)

**Blocking Authority:** **NO**
- Can be blocked by Spec Governance (if no approved spec)
- Can be blocked by Integration Orchestrator (if integration fails)
- Can be blocked by Test Strategy Architect (if tests missing)

**Skill Ownership:** **1 Skill**
1. `verify-nextjs-16-patterns` - Validate Next.js code patterns against Next.js 16 best practices using Context7 MCP

**Reusability:** High - Next.js 16 patterns are transferable across projects.

---

#### Data & Schema Guardian

**Type:** Operational
**Core Responsibility:** Design database schemas, manage migrations (Alembic), and define persistence contracts.

**Explicit Scope:**
- Design database schemas aligned with domain models
- Generate database migrations using Alembic
- Execute migration rollbacks with data preservation
- Validate schema alignment with domain models
- Verify data integrity after migrations
- Define repository interface contracts for Backend Architect

**Explicit Exclusions:**
- Does not define domain models (Domain Guardian defines, Schema maps to database)
- Does not implement backend services (Backend Architect)
- Does not execute backend code

**Blocking Authority:** **YES** (limited scope)
- Blocks if schema conflicts with domain model
- Blocks if migration has no rollback path
- Blocks if migration causes data loss without approval

**Skill Ownership:** **4 Skills**
1. `generate-migration` - Generate Alembic migrations from domain changes
2. `execute-migration-rollback` - Safely rollback migrations
3. `validate-schema-alignment` - Verify schema aligns with domain model
4. `verify-data-integrity` - Validate data consistency after migrations

**Reusability:** Extremely high - database schema patterns are universal (Alembic supports PostgreSQL, MySQL, SQLite, SQL Server).

---

#### Integration Orchestrator

**Type:** Operational
**Core Responsibility:** Coordinate multi-agent workflows and validate end-to-end integration across all system layers.

**Explicit Scope:**
- Coordinate sequential agent execution (CrewAI Process.sequential)
- Define agent execution order and handoff contracts
- Validate integration points (Frontend ↔ Backend ↔ Domain ↔ Persistence)
- Validate error propagation across all system layers
- Validate test coverage against minimum thresholds
- Execute integration and E2E tests
- Aggregate workflow results and generate reports

**Explicit Exclusions:**
- Does not implement features (coordinates agents that implement)
- Does not define domain models (Domain Guardian)
- Does not design error taxonomy (Error Architect)

**Blocking Authority:** **YES**
- Blocks if cross-layer contract violations detected
- Blocks if integration tests fail
- Blocks if required agent skipped in workflow

**Skill Ownership:** **6 Skills**
1. `coordinate-agent-sequence` - Execute multi-agent workflows in correct dependency order
2. `validate-integration-points` - Verify contracts between system layers
3. `execute-e2e-tests` - Run integration and E2E tests
4. `aggregate-workflow-results` - Collect and summarize workflow results
5. `validate-error-propagation` - Validate error handling and propagation across all system layers using Clean Architecture and DDD best practices
6. `validate-test-coverage` - Validate test coverage against minimum thresholds using pytest-cov and coverage.py

**Reusability:** Extremely high - orchestration patterns are universal across multi-layer systems.

---

## Skill Governance Rules

Skills represent **repeatable operational workflows** executed by operational agents. The following rules govern skill creation, ownership, and usage.

### Rule 1: Skill Ownership Restriction

**Skills may ONLY be owned by Operational Agents.**

Governance, Design/Guidance, and Domain agents **must not** own skills because:
- Governance agents validate process (not operational)
- Design agents define contracts (not operational)
- Domain agents reason about correctness (not operational)

Only operational agents execute repeatable workflows that justify skill creation.

### Rule 2: Skill Definition Standards

All skills must:
- Represent a **repeatable workflow** (not one-time tasks)
- Have a **single, focused responsibility**
- Be **domain-agnostic** (reusable across projects)
- Include clear **inputs, outputs, and constraints**
- Be versioned and documented

### Rule 3: Skill Immutability

**Existing skills must NEVER be modified or removed without governance approval.**

Changes to skills require:
1. Justification for change
2. Impact analysis on dependent agents
3. Governance review
4. User approval

### Rule 4: New Skill Creation

New skills may only be created if:
1. Owned by an operational agent
2. Represent a repeatable workflow (used 3+ times)
3. Do not duplicate existing skill functionality
4. Approved by Spec Governance Enforcer

---

## Agent ↔ Skill Mapping

The following table defines the authoritative mapping between agents and skills.

| Agent | Agent Type | Skill Count | Skills Owned |
|-------|-----------|-------------|--------------|
| **Spec Governance Enforcer** | Governance | 0 | None (governance agent) |
| **Test Strategy Architect** | Governance | 0 | None (governance agent) |
| **Error & Reliability Architect** | Design/Guidance | 0 | None (design agent) |
| **Better Auth Guardian** | Operational | **1** | `validate-better-auth-security` |
| **Domain Guardian** | Domain | 0 | None (reasoning agent) |
| **Core Todo Domain** | Domain | 0 | None (reasoning agent) |
| **Python Backend Architect** | Operational | **3** | `validate-api-contracts`, `generate-api-documentation`, `check-authorization-coverage` |
| **Next.js Frontend Architect** | Operational | **1** | `verify-nextjs-16-patterns` |
| **Data & Schema Guardian** | Operational | **4** | `generate-migration`, `execute-migration-rollback`, `validate-schema-alignment`, `verify-data-integrity` |
| **Integration Orchestrator** | Operational | **6** | `coordinate-agent-sequence`, `validate-integration-points`, `execute-e2e-tests`, `aggregate-workflow-results`, `validate-error-propagation`, `validate-test-coverage` |

**Total Skills:** 15
**Total Agents:** 10
**Agents with Skills:** 5 (Better Auth Guardian, Python Backend Architect, Data & Schema Guardian, Integration Orchestrator, Next.js Frontend Architect)

---

## Enforcement & Compliance

### Scope Violation Protocol

If an agent attempts to exceed its defined scope:

1. **Detection:** Monitoring agent or user identifies violation
2. **Immediate Halt:** Violating agent's execution is stopped
3. **Escalation:** Violation reported to Spec Governance Enforcer
4. **Remediation:** Work delegated to correct agent
5. **Audit Trail:** Violation logged in project governance records

### Blocking Agent Execution

When a blocking agent issues a block:

1. **Block Issued:** Agent clearly states blocking reason and severity
2. **Downstream Halt:** All downstream agents do not execute
3. **Remediation Required:** User or appropriate agent must fix violation
4. **Re-Validation:** Blocking agent must re-validate after remediation
5. **Resume:** Workflow resumes only after block cleared

### Advisory Agent Execution

When an advisory agent provides recommendations:

1. **Advisory Issued:** Agent provides warnings and recommendations
2. **Execution Continues:** Downstream agents proceed
3. **User Decision:** User decides whether to address advisory
4. **No Block:** Advisory agents cannot halt execution

### Claude Code Compliance

Claude Code must:
- Invoke agents in correct sequence per invocation order
- Respect blocking authority (halt on BLOCK)
- Delegate work to appropriate agents based on scope
- Use Context7 MCP when required (Better Auth Guardian, Next.js Frontend Architect)
- Never skip governance agents (Spec Governance, Test Strategy)
- Follow TDD mandate (tests before code)
- Follow SDD mandate (specs before implementation)

---

## Future Evolution Policy

This architecture is designed for long-term scalability and domain independence. The following policies govern future changes.

### Adding New Agents

New agents may be added if:

1. **Non-Overlapping Responsibility:** New agent has unique, non-overlapping scope
2. **Clear Agent Type:** Classified as Governance, Design/Guidance, Domain, or Operational
3. **Blocking Authority Justified:** If blocking power requested, justification required
4. **Integration Defined:** Handoff contracts with existing agents specified
5. **Governance Approval:** Spec Governance Enforcer approves addition
6. **Documentation Updated:** AGENTS.md, AGENT_OWNERSHIP_MATRIX.md, AGENT_INVOCATION_PROTOCOL.md updated

### Swapping Domains

The architecture supports domain swapping:

1. **Generic Agents Remain:** All non-domain agents (Backend, Frontend, Schema, Integration, etc.) remain unchanged
2. **Domain Guardian Reconfigured:** Domain Guardian's DOMAIN_NAME and CORE_ENTITY placeholders updated
3. **Domain-Specific Agent Replaced:** Core Todo Domain replaced with new domain-specific agent (e.g., Core E-Commerce Domain)
4. **Domain Model Redefined:** New domain model, invariants, and lifecycle defined
5. **Schema Regenerated:** Data & Schema Guardian generates new schema for new domain
6. **Tests Updated:** Test Strategy Architect validates new domain tests

**Example:** Swap Todo Domain → E-Commerce Domain
- Replace: Core Todo Domain → Core E-Commerce Domain
- Reconfigure: Domain Guardian (DOMAIN_NAME = "E-Commerce", CORE_ENTITY = "Order")
- Preserve: All other 8 agents remain unchanged

### Layering LifeOps AI

Future LifeOps AI integration:

1. **Non-Breaking Addition:** LifeOps AI layered **on top** of existing architecture
2. **New Agents Created:** LifeOps-specific agents (e.g., Routine Automation Agent, Context Synthesis Agent)
3. **Existing Agents Preserved:** Core 10 agents remain unchanged
4. **Integration Protocol Defined:** LifeOps agents integrate via Integration Orchestrator
5. **Governance Respected:** LifeOps agents subject to Spec Governance and Test Strategy enforcement

**Principle:** LifeOps AI **augments** the system without **replacing** core agents.

---

## LifeOps Agent Layer (Active)

The LifeOps layer has been activated. Five LifeOps agents operate **alongside** the 10 core development agents, providing autonomous FTE (Full-Time Equivalent) capabilities.

### LifeOps Agent Taxonomy

LifeOps agents follow a different execution model than development agents:
- **Dev agents:** Sequential pipeline (CrewAI Process.sequential)
- **LifeOps agents:** Event-driven, parallel execution (triggered by external events)

The two layers are **isolated** — dev agents never invoke LifeOps agents and vice versa. Cross-layer coordination goes through the human or the Integration Orchestrator.

### LifeOps Execution Model

```
External Event (email, transaction, schedule)
  ↓
Watcher (detects event)
  ↓
Event Bus (routes event)
  ↓
Policy Enforcement (validates action is permitted)
  ↓
Appropriate LifeOps Agent (processes event)
  ↓
HITL Gate (approval for HIGH/CRITICAL actions)
  ↓
Action Execution (via MCP server)
  ↓
Audit Trail (logged for compliance)
  ↓
Monitoring Agent (tracks health)
```

---

### LifeOps Agent Definitions

#### Communication Agent

**Type:** Operational
**Core Responsibility:** Manage all inbound and outbound messaging across email, Slack, and other communication channels.

**Explicit Scope:**
- Draft email responses based on context and conversation history
- Summarize unread inbox items across channels
- Route messages to appropriate agents (finance, scheduling, social)
- Track response SLAs and communication health

**Explicit Exclusions:**
- Does not send messages autonomously (HITL required for all outbound)
- Does not handle financial transactions (routes to Finance Agent)
- Does not manage social media content (routes to Social Media Agent)

**Blocking Authority:** **NO** (advisory — drafts only, human sends)

**Skill Ownership:** **3 Skills**
1. `draft-email-response` - Draft contextual email replies
2. `summarize-inbox` - Aggregate and summarize unread messages
3. `route-message` - Classify and route messages to appropriate handlers

**MCP Dependencies:** email-mcp, slack-mcp, filesystem

---

#### Finance Agent

**Type:** Operational
**Core Responsibility:** Manage accounting, invoicing, expense tracking, and financial reporting through Odoo 19+ integration.

**Explicit Scope:**
- Create and manage invoices via Odoo JSON-RPC
- Categorize and record expenses
- Reconcile bank transactions with journal entries
- Generate financial summaries and reports
- Flag anomalies for human review

**Explicit Exclusions:**
- Does not provide financial advice (investment, tax, pricing)
- Does not process payments without HITL approval
- Does not manage communication (Finance-related messages routed from Communication Agent)

**Blocking Authority:** **YES** (blocks unapproved financial transactions exceeding configured thresholds)

**Skill Ownership:** **3 Skills**
1. `generate-invoice` - Create customer/vendor invoices in Odoo
2. `reconcile-transactions` - Match bank transactions with journal entries
3. `expense-categorization` - Classify and record expenses

**MCP Dependencies:** odoo-mcp, filesystem

---

#### Social Media Agent

**Type:** Operational
**Core Responsibility:** Manage social media presence including content drafting, scheduling, and engagement analysis.

**Explicit Scope:**
- Draft platform-optimized social media content
- Manage content calendar and scheduling
- Analyze engagement metrics across platforms
- Maintain consistent brand voice

**Explicit Exclusions:**
- Does not publish content autonomously (HITL required for all publishing)
- Does not handle direct messages (routes through Communication Agent)
- Does not manage advertising or paid campaigns

**Blocking Authority:** **NO** (all posts require HITL approval)

**Skill Ownership:** **3 Skills**
1. `draft-social-post` - Create platform-optimized content
2. `schedule-content` - Manage content calendar and scheduling
3. `engagement-summary` - Analyze engagement metrics

**MCP Dependencies:** browser-mcp, filesystem

---

#### Monitoring Agent

**Type:** Governance
**Core Responsibility:** Track operational status of all agents, watchers, integrations, and workflows. System observability layer.

**Explicit Scope:**
- Monitor watcher health (running, stopped, erroring)
- Track agent execution health (response times, error rates)
- Monitor MCP server connectivity
- Detect anomalies in system behavior
- Generate health reports and daily status summaries
- Safety override: block runaway agents or infinite loops

**Explicit Exclusions:**
- Does not take corrective action (observer only, except safety overrides)
- Does not process business logic
- Does not interact with external services (except reading health data)

**Blocking Authority:** **YES** (CRITICAL safety only — runaway agents, infinite loops, security breaches)

**Skill Ownership:** **2 Skills**
1. `system-health-check` - Comprehensive health assessment of all components
2. `anomaly-detection` - Detect unusual patterns in system behavior

**MCP Dependencies:** filesystem

---

#### Audit Agent

**Type:** Governance
**Core Responsibility:** Verify all system actions comply with policies, approval workflows, and governance rules. System accountability layer.

**Explicit Scope:**
- Weekly system audits (agent performance, action logs, approval compliance)
- Verify all sensitive actions were HITL-approved
- Check for policy violations across all agents
- Generate compliance reports and audit trails
- Recommend policy updates based on findings

**Explicit Exclusions:**
- Does not enforce policies in real-time (Monitoring Agent and HITL gate do)
- Does not take corrective action (reports findings)
- Does not modify audit trails or action logs

**Blocking Authority:** **YES** (blocks if systematic compliance violations found — 3+ violations from same agent)

**Skill Ownership:** **2 Skills**
1. `weekly-audit-report` - Generate comprehensive weekly compliance audit
2. `compliance-check` - Targeted compliance verification

**MCP Dependencies:** filesystem

---

### LifeOps Agent ↔ Skill Mapping

| Agent | Agent Type | Skill Count | Skills Owned |
|-------|-----------|-------------|--------------|
| **Communication Agent** | Operational | **3** | `draft-email-response`, `summarize-inbox`, `route-message` |
| **Finance Agent** | Operational | **3** | `generate-invoice`, `reconcile-transactions`, `expense-categorization` |
| **Social Media Agent** | Operational | **3** | `draft-social-post`, `schedule-content`, `engagement-summary` |
| **Monitoring Agent** | Governance | **2** | `system-health-check`, `anomaly-detection` |
| **Audit Agent** | Governance | **2** | `weekly-audit-report`, `compliance-check` |

**LifeOps Total:** 5 agents, 13 skills

### System-Wide Safety Skills

In addition to agent-owned skills, 3 system-wide safety skills support all LifeOps agents:

| Skill | Owner | Purpose |
|-------|-------|---------|
| `policy-enforcement` | Monitoring Agent | Runtime action gating before execution |
| `error-recovery` | System | Retry, fallback, circuit-breaker for failures |
| `notification` | System | Alert human across available channels |

---

### Complete System Summary

| Layer | Count | Agents |
|-------|-------|--------|
| **Development Pipeline** | 10 | Spec Governance, Test Strategy, Error Architect, Domain Guardian, Core Todo, Backend, Frontend, Schema, Auth, Integration |
| **LifeOps Layer** | 5 | Communication, Finance, Social Media, Monitoring, Audit |
| **Total** | **15** | |

| Category | Dev Skills | LifeOps Skills | System Skills | Total |
|----------|-----------|----------------|---------------|-------|
| Skills | 15 | 13 | 3 | **31** |

---

### LifeOps HITL Safety Matrix

| Agent | Action | Risk Level | Approval |
|-------|--------|-----------|----------|
| Communication | Read inbox | LOW | Auto |
| Communication | Draft response | MEDIUM | Notify |
| Communication | Send email/message | HIGH | Explicit |
| Communication | Reply-all / forward external | CRITICAL | Explicit + confirm |
| Finance | Read financial data | LOW | Auto |
| Finance | Create draft invoice | MEDIUM | Notify |
| Finance | Post invoice / record expense > $100 | HIGH | Explicit |
| Finance | Delete/modify posted entries | CRITICAL | Explicit + confirm |
| Social Media | Read engagement data | LOW | Auto |
| Social Media | Draft post | MEDIUM | Notify |
| Social Media | Publish / schedule post | HIGH | Explicit |
| Social Media | Delete post / change profile | CRITICAL | Explicit + confirm |
| Monitoring | Read health data | LOW | Auto |
| Monitoring | Send alert | MEDIUM | Auto (safety) |
| Monitoring | Block agent (safety) | CRITICAL | Auto (safety override) |
| Audit | Read audit trails | LOW | Auto |
| Audit | Generate report | LOW | Auto |
| Audit | Block agent (compliance) | HIGH | Explicit |

---

## Conclusion

This multi-agent architecture provides:

- **Clear governance** through blocking authority and scope enforcement
- **Future reusability** through domain-agnostic design
- **Quality assurance** through TDD and SDD mandates
- **Scalability** through modular agent design
- **Production readiness** through comprehensive validation and integration
- **Autonomous FTE capability** through LifeOps agents handling communication, finance, social media, monitoring, and audit
- **Zero-trust safety** through HITL approval gates on all sensitive actions
- **Complete accountability** through audit trails and weekly compliance reports

**System Totals:** 15 agents, 31 skills, 7 MCP servers, 4-tier HITL safety model

All work in this repository must comply with this specification. No exceptions.

**Authority:** This document supersedes all conflicting specifications.
**Enforcement:** Spec Governance Enforcer validates compliance. Audit Agent verifies adherence.
**Audit:** Architecture expanded with LifeOps layer (2026-02-16). Original audit confirmed (2026-01-02).

---

**End of Specification**
