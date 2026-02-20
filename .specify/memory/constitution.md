# Personal AI Employee FTE System — Constitution

**Project:** Personal AI Employee — Building Autonomous Full-Time Equivalent AI Workers
**Authority:** This constitution is the supreme governance document for the FTE system. All agents, skills, watchers, and workflows must comply. Conflicts between this document and any other specification are resolved in favor of this constitution.

---

## Table of Contents

1. [Purpose & Vision](#1-purpose--vision)
2. [Hackathon Rules & Operating Principles](#2-hackathon-rules--operating-principles)
3. [System Resolution Framework](#3-system-resolution-framework)
4. [Architecture Principles](#4-architecture-principles)
5. [Code Quality Standards](#5-code-quality-standards)
6. [Testing Principles](#6-testing-principles)
7. [Performance Principles](#7-performance-principles)
8. [Security & Privacy Architecture](#8-security--privacy-architecture)
9. [Permission Boundaries](#9-permission-boundaries)
10. [Auditability & Observability](#10-auditability--observability)
11. [Failure & Recovery Principles](#11-failure--recovery-principles)
12. [Human Sovereignty](#12-human-sovereignty)
13. [Ethical Constraints](#13-ethical-constraints)
14. [Continuous Evolution](#14-continuous-evolution)

---

## Tier Inheritance Rule

Tiers are **cumulative**. Each tier inherits and enforces ALL rules from lower tiers:

- **[BRONZE]** — Foundation tier. All rules apply to every tier above.
- **[SILVER]** — Includes all Bronze rules plus Silver-specific rules.
- **[GOLD]** — Includes all Bronze + Silver rules plus Gold-specific rules.
- **[PLATINUM]** — Includes all Bronze + Silver + Gold rules plus Platinum-specific rules.

A system at a given tier MUST satisfy every requirement of that tier and all tiers below it.

---

## 1. Purpose & Vision

### 1.1 Mission

Build autonomous AI Full-Time Equivalent (FTE) workers that handle repeatable business and personal operations — email triage, financial accounting, social media management, scheduling, and compliance auditing — with human-in-the-loop (HITL) safety gates on all sensitive actions.

### 1.2 Philosophy

- **Augment, never replace.** AI extends human capability. AI does not replace human judgment, accountability, or decision-making authority.
- **Safety before autonomy.** No system may act on sensitive data or external services without explicit human approval at the appropriate risk tier.
- **Memory-first reasoning.** The Obsidian vault is the single source of truth. Agents reason from vault contents, not from internal model knowledge.
- **Transparency by default.** Every agent action is logged, traceable, and auditable. No silent execution.

### 1.3 Tier Progression

| Tier | Scope | Autonomy Model | Estimated Effort |
|------|-------|----------------|------------------|
| **[BRONZE]** | Single domain, local only | Human-in-command: AI drafts, human executes | 8-12 hours |
| **[SILVER]** | Single domain, local + 1 MCP | Human-on-the-loop: AI executes LOW/MEDIUM, human approves HIGH+ | 20-30 hours |
| **[GOLD]** | Cross-domain (Personal + Business), multiple MCPs | Human-over-the-loop: AI operates autonomously on LOW/MEDIUM, weekly human audit | 40+ hours |
| **[PLATINUM]** | Cloud 24/7, work-zone specialization | Human-as-strategic-director: AI operates continuously, human sets policy and approves exceptions | 60+ hours |

---

## 2. Hackathon Rules & Operating Principles

### 2.1 [BRONZE] Foundation Rules

1. **Obsidian Vault**: The system MUST use an Obsidian-compatible local Markdown vault as the memory layer and GUI.
2. **Dashboard.md**: The vault MUST contain a `Dashboard.md` file serving as the human-facing operational overview.
3. **Company_Handbook.md**: The vault MUST contain a `Company_Handbook.md` defining business context, policies, and operational procedures.
4. **Folder Structure**: The vault MUST implement the following folder hierarchy:
   - `/Inbox` — Incoming items awaiting triage
   - `/Needs_Action` — Items triaged and requiring human or agent action
   - `/Done` — Completed items archived for audit
5. **One Watcher**: At least one working watcher script (Gmail OR filesystem) MUST detect external events and write to `/Inbox`.
6. **Claude Code Integration**: Claude Code MUST read from and write to the vault via the filesystem MCP server.
7. **Agent Skills Mandate**: ALL AI functionality MUST be implemented as Agent Skills with documented SKILL.md definitions. No ad-hoc AI behavior outside the skill framework.

### 2.2 [SILVER] Expansion Rules

1. **Multiple Watchers**: At least two (2) working watcher scripts MUST operate concurrently (e.g., Gmail + WhatsApp, Gmail + LinkedIn, Gmail + filesystem).
2. **HITL Approval Workflow**: The system MUST implement the 4-tier HITL approval model (LOW/MEDIUM/HIGH/CRITICAL) as defined in Section 9.
3. **MCP Server**: At least one (1) working MCP server MUST enable external action execution (e.g., email-mcp for sending emails).
4. **Reasoning Loop**: Claude Code MUST create `Plan.md` files as part of a reasoning loop for multi-step tasks, documenting intent before execution.
5. **Scheduling**: Basic scheduling via cron, Task Scheduler, or equivalent MUST enable periodic operations (inbox checks, report generation).
6. **LinkedIn Sales Posts**: The system MUST support automatically posting on LinkedIn for sales outreach, subject to HITL approval (HIGH risk).
7. **All AI as Agent Skills**: Maintained from Bronze. No exceptions.

### 2.3 [GOLD] Cross-Domain Rules

1. **Cross-Domain Integration**: The system MUST handle both Personal and Business domains with clear domain isolation boundaries.
2. **Odoo 19+ Accounting**: The system MUST integrate with Odoo Community Edition (self-hosted, version 19+) via JSON-RPC API for accounting operations (invoicing, expenses, reconciliation).
3. **Social Media — Facebook + Instagram**: The system MUST integrate Facebook and Instagram for posting content and generating engagement summaries.
4. **Social Media — Twitter/X**: The system MUST integrate Twitter/X for posting content and generating engagement summaries.
5. **Multiple MCP Servers**: The system MUST operate multiple MCP servers for different action types (email, calendar, browser, filesystem, Odoo).
6. **Weekly Audit + CEO Briefing**: The Audit Agent MUST generate weekly business and accounting audit reports. A CEO briefing document MUST be produced summarizing key metrics, anomalies, and recommendations.
7. **Error Recovery**: The system MUST implement error recovery with retry logic, circuit breakers, and graceful degradation as defined in Section 11.
8. **Comprehensive Audit Logging**: All agent actions MUST be logged in structured JSON format with the fields defined in Section 10.
9. **Ralph Wiggum Loop**: The system MUST implement the Ralph Wiggum persistence loop (Claude Code Stop hook) for multi-step tasks that survive session interruptions.
10. **Architecture Documentation**: The system MUST maintain architecture documentation and lessons-learned records (ADRs).
11. **All AI as Agent Skills**: Maintained from Bronze. No exceptions.

### 2.4 [PLATINUM] Cloud-Native Rules

1. **Cloud 24/7 Operation**: The system MUST run continuously on cloud infrastructure with always-on watchers, orchestrator, and health monitoring.
2. **Work-Zone Specialization**:
   - **Cloud Zone** owns: email triage, email draft generation, social media draft creation, social media scheduling, engagement analysis, report generation.
   - **Local Zone** owns: HITL approvals, WhatsApp messaging, payment execution, final email send, final social media post, sensitive data operations.
3. **Vault Synchronization**: Cloud and Local zones MUST synchronize via Git or Syncthing with conflict-free coordination:
   - Cloud writes to `/Updates/` directory only.
   - Local merges `/Updates/` into `Dashboard.md`.
   - **Single-writer rule**: Only the Local zone may write to `Dashboard.md`.
4. **Claim-by-Move Rule**: Agents claim work items by moving them to `/In_Progress/<agent_name>/`. No two agents may claim the same item.
5. **Secrets Firewall**: Secrets (`.env`, API tokens, WhatsApp credentials, banking credentials) MUST NEVER synchronize between zones. Each zone maintains its own secrets store.
6. **Odoo Cloud Deployment**: Odoo MUST be deployed on a Cloud VM with HTTPS, automated backups, and health monitoring.
7. **Cloud Odoo Restrictions**: Cloud zone Odoo integration is limited to draft-only accounting actions. Posting invoices and recording payments require Local zone approval.
8. **Process Management**: The system MUST use a process manager (PM2, supervisord, or systemd) for watcher and orchestrator lifecycle management.
9. **End-to-End Demo Flow**: The system MUST demonstrate: Email arrives → Cloud drafts response → Approval file created → Local approves → Email sent → Action logged → Item moved to `/Done`.
10. **Optional A2A Upgrade**: The system MAY replace file-based handoffs with Agent-to-Agent (A2A) direct messaging protocol for reduced latency.

---

## 3. System Resolution Framework

### 3.1 Decision Priority Hierarchy

When conflicts arise between directives, the following priority applies (highest to lowest):

1. **Human Override** — A direct human instruction supersedes all other directives.
2. **Constitution** — This document supersedes all system policies, agent reasoning, and skill definitions.
3. **System Policies** — AGENTS.md, AGENT_INVOCATION_PROTOCOL.md, AGENT_OWNERSHIP_MATRIX.md, and SKILL.md definitions.
4. **Agent Reasoning** — Agent-generated plans, recommendations, and decisions.

### 3.2 Conflict Resolution

- **Blocking Authority Hierarchy**: Monitoring Agent (CRITICAL safety) > Audit Agent (compliance) > Finance Agent (financial thresholds) > Spec Governance Enforcer (SDD) > Domain Guardian (domain purity).
- **Agent Priority (LifeOps)**: Monitoring > Audit > Finance > Communication > Social Media.
- **Zone Conflicts [PLATINUM]**: Local zone authority supersedes Cloud zone authority for all sensitive operations (approvals, payments, final sends).
- **Ownership Conflicts [PLATINUM]**: The claim-by-move rule determines ownership. First agent to move item to `/In_Progress/<agent>/` owns it. If two agents claim simultaneously, the higher-priority agent (per hierarchy above) takes ownership.

### 3.3 Agent Routing Depth Limit

**[SILVER+]** Agent-to-agent message routing (e.g., Communication → Finance → Communication) MUST NOT exceed a maximum chain depth of **3 hops**. If a routing chain reaches depth 3 without resolution:

1. The item is placed in `/Needs_Action` with a `?routing-loop` tag.
2. A MEDIUM notification is sent to the human operator.
3. No further automatic routing occurs for that item.

Circular routing (Agent A → Agent B → Agent A for the same item) MUST be detected and halted immediately.

### 3.4 Ambiguous Instruction Handling

When an agent encounters ambiguous instructions:

1. **Never guess.** Do not infer intent from incomplete information.
2. **Ask clarifying questions.** Surface 2-3 targeted questions to the human operator.
3. **Queue and wait.** Place the item in `/Needs_Action` with a `?clarification-needed` tag and await human response.
4. **Time-bound escalation.** If no response within the configured HITL timeout (default: 24 hours), escalate via the notification skill.

### 3.5 Ethical Override

The human operator may force-stop any agent at any time for any reason. This override:

- Requires no justification.
- Takes effect immediately.
- Cannot be countermanded by any agent or policy.
- Is logged for audit purposes but never blocked.

---

## 4. Architecture Principles

### 4.1 System Metaphor

| Component | Metaphor | Implementation |
|-----------|----------|---------------|
| **The Brain** | Reasoning engine | Claude Code (claude-opus-4-6 or configured model) |
| **The Memory / GUI** | Knowledge store + dashboard | Obsidian vault (local Markdown files) |
| **The Senses** | Event perception | Watcher scripts (Gmail, WhatsApp, LinkedIn, filesystem) |
| **The Hands** | External action execution | MCP servers (email, calendar, browser, Odoo, Slack) |
| **The Loop** | Persistence across sessions | Ralph Wiggum Stop hook + Plan.md reasoning loop |
| **The Glue** | Automation orchestration | Python orchestrator script |

### 4.2 Layered Architecture

The system is organized into five layers. Each layer has a single responsibility and communicates only with adjacent layers.

```
Layer 5: Execution Layer (MCP Servers)
   ↑
Layer 4: Agent Layer (15 agents, 31+ skills)
   ↑
Layer 3: Orchestrator Layer (Python orchestrator, event bus)
   ↑
Layer 2: Watcher Layer (Gmail, WhatsApp, LinkedIn, filesystem watchers)
   ↑
Layer 1: Memory Layer (Obsidian vault, Dashboard.md, folder structure)
```

**Layer 1 — Memory Layer**
- **[BRONZE]**: Obsidian vault with Dashboard.md, Company_Handbook.md, /Inbox, /Needs_Action, /Done.
- **[SILVER]**: Add Plan.md files for reasoning traces. Add /Templates for reusable response templates.
- **[GOLD]**: Add /Audit for weekly reports. Add /Reports for CEO briefings. Add cross-domain folders (Personal/, Business/).
- **[PLATINUM]**: Add /Updates (Cloud write target), /In_Progress/<agent>/ (claim folders). Vault sync via Git/Syncthing.

**Layer 1a — Vault Write Access Control [SILVER+]**

Agents MUST only write to their designated vault folders. Unauthorized writes are logged and blocked.

| Agent | Write Access | Read Access |
|-------|-------------|-------------|
| Watchers | `/Inbox` only | None |
| Communication Agent | `/Needs_Action`, `/Done`, `/Templates` | `/Inbox`, `/Needs_Action`, `/Done` |
| Finance Agent | `/Needs_Action`, `/Done`, `/Audit`, `/Reports` | `/Inbox`, `/Needs_Action`, `/Done`, `/Audit` |
| Social Media Agent | `/Needs_Action`, `/Done` | `/Inbox`, `/Needs_Action`, `/Done`, `/Templates` |
| Monitoring Agent | `/Audit`, vault state files | All folders (read-only observation) |
| Audit Agent | `/Audit`, `/Reports` | All folders (read-only audit) |
| Orchestrator | `/Needs_Action`, `/Done`, `Plan.md` | All folders |
| **[PLATINUM] Cloud Zone** | `/Updates` only | `/Inbox`, `/Needs_Action` |
| **[PLATINUM] Local Zone** | All folders | All folders |

Any agent writing outside its designated folders MUST be logged as a policy violation by the Monitoring Agent.

**Layer 2 — Watcher Layer (Perception)**
- **[BRONZE]**: One watcher (Gmail OR filesystem). Poll interval: 5 minutes.
- **[SILVER]**: Two or more watchers (Gmail + WhatsApp + LinkedIn). Poll interval: 2 minutes.
- **[GOLD]**: All configured watchers active. Poll interval: 1 minute. Health monitoring via Monitoring Agent.
- **[PLATINUM]**: Always-on watchers on cloud infrastructure. Poll interval: 30 seconds. Auto-restart via process manager. Watchdog process monitors watcher health.

**Layer 3 — Orchestrator Layer**
- **[BRONZE]**: Manual orchestration (human triggers Claude Code).
- **[SILVER]**: Python orchestrator with cron-based scheduling. Basic event routing.
- **[GOLD]**: Event-driven orchestrator with event bus. Ralph Wiggum persistence loop. Error recovery integration.
- **[PLATINUM]**: Cloud-native orchestrator (PM2/supervisord/systemd). Work-zone routing (Cloud vs Local). Fault tolerance with zone failover.

**Layer 4 — Agent Layer**
- **[BRONZE]**: Core reasoning via Claude Code. Basic agent skills for vault operations.
- **[SILVER]**: Development pipeline agents + Communication Agent. HITL approval gates.
- **[GOLD]**: Full 15-agent system (10 dev + 5 LifeOps). Cross-domain agent coordination. Weekly audit cycle.
- **[PLATINUM]**: Zone-aware agents. Cloud agents (draft-only). Local agents (approval + execution). A2A messaging (optional).

**Layer 5 — Execution Layer (MCP Servers)**
- **[BRONZE]**: filesystem MCP only.
- **[SILVER]**: filesystem + email-mcp.
- **[GOLD]**: filesystem + email-mcp + browser-mcp + calendar-mcp + slack-mcp + odoo-mcp + context7.
- **[PLATINUM]**: All Gold MCP servers deployed on Cloud VM. Odoo on dedicated Cloud VM with HTTPS. Zone-restricted MCP access (Cloud cannot access WhatsApp MCP, Local-only MCPs).

### 4.3 Core Architecture Principles

1. **Watcher → Reasoner → Executor Flow**: Every action originates from an external event (watcher), passes through reasoning (agent), and executes via a controlled channel (MCP server). No agent may act without an originating event or human trigger.

2. **Memory-First Reasoning**: Agents MUST read from the vault before reasoning. The vault is the single source of truth. Agents MUST NOT rely on internal model knowledge for operational decisions.

3. **Event-Driven Orchestration**: LifeOps agents operate on an event-driven model (external event → policy check → agent processing → HITL gate → execution → audit). Development agents operate on a sequential pipeline (CrewAI Process.sequential).

4. **Single Responsibility**: Each agent has one core responsibility. Agents MUST NOT exceed their defined scope. Work outside an agent's scope MUST be delegated to the appropriate agent.

5. **Failure-Aware Design**: Every agent MUST handle failures gracefully. Retry logic, circuit breakers, and fallback paths are mandatory at Gold+. No agent may fail silently.

6. **Idempotent Operations**: Agent actions MUST be idempotent where possible. Retrying an action MUST NOT produce duplicate side effects (duplicate emails, duplicate invoices, duplicate posts).

### 4.4 Vault Integrity

**[GOLD+]** The system MUST verify vault integrity:

1. **Write Verification**: After every vault write, verify the file was written correctly (read-back check).
2. **Corruption Detection**: A daily scheduled job MUST validate that all vault files in `/Audit` and `/Reports` are parseable Markdown/JSON. Corrupted files are quarantined to `/Quarantine` and the human is notified.
3. **Concurrent Write Protection**: The filesystem MCP MUST use atomic writes (write-to-temp + rename) to prevent partial writes from concurrent agents.
4. **Backup**: Vault state MUST be backed up daily. At Platinum tier, vault snapshots are taken every 6 hours.

### 4.5 Ralph Wiggum Persistence Loop

**[SILVER+]** The Ralph Wiggum loop ensures multi-step tasks survive Claude Code session interruptions:

1. Agent writes current task state to `Plan.md` in the vault.
2. Claude Code Stop hook triggers.
3. On next session start, orchestrator reads `Plan.md` and resumes from last checkpoint.
4. Agent continues execution from the recorded state.
5. On completion, `Plan.md` is archived and item moves to `/Done`.

**Invariant:** No multi-step task may lose progress due to session interruption. If state cannot be persisted, the task MUST be re-queued to `/Needs_Action`.

### 4.6 Odoo Integration Architecture

**[GOLD+]** Odoo Community Edition 19+ integration via JSON-RPC API:

- **Connection**: JSON-RPC over HTTPS (self-hosted Odoo instance).
- **Authentication**: API key stored in `.env` (ODOO_URL, ODOO_DB, ODOO_USER, ODOO_API_KEY). Never stored in vault.
- **Operations**: Invoice creation, expense categorization, transaction reconciliation, financial reporting.
- **[PLATINUM] Zone Restriction**: Cloud zone may only create draft accounting entries. Posting invoices and recording payments requires Local zone approval via HITL gate.
- **[PLATINUM] Deployment**: Odoo deployed on Cloud VM with HTTPS termination, automated daily backups, and health monitoring endpoint.

---

## 5. Code Quality Standards

### 5.1 General Standards (All Tiers)

- **Readable over clever.** Code MUST prioritize readability. No premature optimization, no clever one-liners that sacrifice clarity.
- **Clean Architecture.** Separation of concerns across layers. Domain logic MUST NOT depend on infrastructure.
- **Config-driven behavior.** All thresholds, intervals, and feature flags MUST be configurable via environment variables or configuration files. No hardcoded operational parameters.
- **Version-controlled prompts.** Agent skill definitions (SKILL.md) and prompt templates MUST be version-controlled alongside code. Each SKILL.md MUST include a `version` field (MAJOR.MINOR.PATCH). Prompt changes that alter agent behavior require a MINOR version bump. Breaking changes to inputs/outputs require a MAJOR bump. Rollback to a previous prompt version MUST be possible via git revert within 5 minutes.
- **Strong typing.** Python code MUST use type hints (PEP 484). TypeScript code MUST use strict mode.
- **Idempotent operations.** All external actions MUST be safe to retry without producing duplicate effects.

### 5.2 Tier-Specific Coverage Requirements

| Tier | Test Coverage | Documentation | Code Review |
|------|--------------|---------------|-------------|
| **[BRONZE]** | Manual testing acceptable | README + SKILL.md files | Self-review |
| **[SILVER]** | 70% line coverage minimum | + Architecture docs | Peer review recommended |
| **[GOLD]** | 85% line coverage minimum | + ADRs + Weekly reports | Peer review required |
| **[PLATINUM]** | 90% line coverage minimum | + Runbooks + Incident playbooks | Peer review + automated gates |

### 5.3 Skill Development Standards

All Agent Skills MUST:

1. Have a SKILL.md file with: name, description, version, type, inputs, outputs, reusability rating, constraints.
2. Represent a repeatable workflow (not a one-time task).
3. Have a single, focused responsibility.
4. Be domain-agnostic where possible (reusable across projects).
5. Include clear input validation and error handling.
6. Be versioned using semantic versioning (MAJOR.MINOR.PATCH).

---

## 6. Testing Principles

### 6.1 TDD Mandate (Non-Negotiable)

**All code MUST follow Test-Driven Development (Red-Green-Refactor):**

1. **Red**: Write a failing test that defines the desired behavior. Obtain human approval of the test before proceeding.
2. **Green**: Write the minimum code necessary to make the test pass.
3. **Refactor**: Improve code quality while all tests remain green.

**No code may be written before its corresponding test exists.** This rule is enforced by the Test Strategy Architect and cannot be overridden by any agent.

### 6.2 Test Categories

| Category | Scope | Tier Required |
|----------|-------|---------------|
| **Unit Tests** | Individual agent skills, utility functions | **[BRONZE+]** |
| **Integration Tests** | MCP server interactions, agent-to-vault operations | **[SILVER+]** |
| **Simulation Tests** | End-to-end workflow simulation (email → triage → response) | **[GOLD+]** |
| **Failure Injection Tests** | Circuit breaker behavior, retry logic, degradation paths | **[GOLD+]** |
| **Zone Tests** | Cloud/Local zone isolation, vault sync correctness | **[PLATINUM]** |
| **Load Tests** | Concurrent watcher throughput, MCP server capacity | **[PLATINUM]** |

### 6.3 Test Invariant

**"No system may execute autonomously without testable behavior."**

Every agent, skill, watcher, and orchestrator component MUST have at least one automated test that validates its core behavior. Components without tests are not eligible for production deployment.

---

## 7. Performance Principles

### 7.1 Core Performance Rules

- **Queue-based execution.** Actions MUST be queued and processed sequentially within each agent. No race conditions from parallel execution of the same action type.
- **Retry-safe logic.** All operations MUST be safe to retry. Idempotency keys MUST be used for external API calls.
- **Never trade safety for speed.** Performance optimizations MUST NOT compromise HITL approval gates, audit logging, or error handling.

### 7.1a Idempotency Keys

**[SILVER+]** All external API calls MUST include an idempotency key to prevent duplicate execution on retry:

- **Format**: `{agent_name}:{action}:{request_id}:{timestamp_epoch}` (e.g., `finance:post_invoice:abc123:1708000000`)
- **Storage**: Idempotency keys are stored in a local key-value file (`vault/state/idempotency_keys.json`) with TTL of 24 hours.
- **Enforcement**: Before executing an external action, the system checks whether the idempotency key already exists. If it does, the action is skipped and the previous result is returned.
- **Financial Actions**: Financial idempotency keys have a TTL of 7 days (longer to prevent duplicate transactions during extended approval cycles).

### 7.1b Queue Specification

**[SILVER+]** The action queue MUST implement:

- **Persistence**: Queue state is persisted to `vault/state/queue.json`. Queue contents survive orchestrator restarts.
- **Ordering**: Actions are processed in FIFO order within each priority level. CRITICAL > HIGH > MEDIUM > LOW.
- **Depth Limit**: Maximum queue depth is 500 items (configurable). If queue depth exceeds the limit, the oldest LOW-priority items are moved to `/Needs_Action` for manual processing and a WARNING is sent.
- **Dead-Letter Queue**: Items that fail 3 times are moved to the quarantine folder (Section 11.7) instead of being retried indefinitely.
- **Visibility Timeout**: Items being processed are invisible to other agents for 5 minutes. If processing does not complete within 5 minutes, the item becomes visible again for reprocessing.

### 7.2 Tier-Specific SLAs

| Metric | [BRONZE] | [SILVER] | [GOLD] | [PLATINUM] |
|--------|----------|----------|--------|------------|
| Watcher poll interval | 5 minutes | 2 minutes | 1 minute | 30 seconds |
| Event-to-triage latency | Best effort | < 5 minutes | < 2 minutes | < 1 minute |
| Agent response time (p95) | Best effort | < 30 seconds | < 10 seconds | < 1 second |
| System uptime | Manual start | Scheduled hours | Business hours | 24/7 (99.5%) |
| HITL approval timeout | No limit | 48 hours | 24 hours | 12 hours |

### 7.3 Rate Limiting

**[SILVER+]** The system MUST enforce rate limits to prevent abuse and runaway behavior:

| Action Type | Rate Limit |
|-------------|-----------|
| Email send | 20 per hour |
| Social media post | 10 per hour |
| Financial transaction | 5 per hour |
| MCP server calls (per server) | 100 per hour |
| Agent actions (aggregate) | 200 per hour |
| Notifications | 10 per minute per channel |

**[GOLD+]** Rate limits MUST be configurable via environment variables. Exceeding a rate limit MUST trigger a MEDIUM notification and queue remaining actions.

**[SILVER+] Daily Action Budget:** The system MUST enforce a configurable daily aggregate action limit (default: 1,000 external actions per day). When the budget reaches 80%, a WARNING notification is sent. When the budget is exhausted, the system enters PAUSE mode:

- All non-safety actions are queued.
- Monitoring Agent continues operating (safety exempt).
- Human is notified via CRITICAL alert.
- Human must explicitly resume or increase the budget.

### 7.4 Scheduled Operations

- **[SILVER]**: Cron-based scheduling for inbox checks and report generation.
- **[GOLD]**: Scheduled weekly audit reports. Scheduled CEO briefing generation. Scheduled engagement summaries.
- **[PLATINUM]**: Process management via PM2/supervisord/systemd. Automatic restart on failure. Health check endpoints for all long-running processes.

---

## 8. Security & Privacy Architecture

### 8.1 Zero Trust Execution Model

No agent, watcher, or MCP server is trusted by default. Every action MUST be:

1. **Authenticated**: The originating agent or watcher is identified.
2. **Authorized**: The action is permitted per the permission boundaries (Section 9).
3. **Audited**: The action is logged with full context (Section 10).
4. **Scoped**: The action accesses only the minimum data required (least privilege).

### 8.2 Secrets Management

**[BRONZE+]** Credential Isolation Rules:

| Rule | Requirement | Enforced At |
|------|-------------|-------------|
| SEC1 | Never store credentials in plain text or in the vault | All tiers |
| SEC2 | Use environment variables (.env) for ALL API keys | All tiers |
| SEC3 | Use a secrets manager for banking and financial credentials | **[GOLD+]** |
| SEC4 | .env MUST be in .gitignore — never committed to version control | All tiers |
| SEC5 | Rotate credentials on a monthly schedule | **[GOLD+]** |
| SEC6 | DEV_MODE environment flag prevents ALL real external actions | All tiers |
| SEC7 | --dry-run flag MUST be supported on all action scripts | **[SILVER+]** |
| SEC8 | Separate sandbox accounts for development and testing | **[GOLD+]** |

**[PLATINUM]** Secrets Firewall:
- Secrets MUST NEVER synchronize between Cloud and Local zones.
- Each zone maintains an independent `.env` file.
- Cloud zone MUST NOT have access to: WhatsApp credentials, banking credentials, payment processing tokens.
- Local zone MUST NOT expose secrets to network-accessible endpoints.

### 8.3 Data Classification

| Classification | Examples | Storage | Access |
|---------------|----------|---------|--------|
| **Public** | Published social media posts, public website content | Vault or cloud | Any agent |
| **Internal** | Draft emails, draft posts, internal reports | Vault | Authorized agents |
| **Sensitive** | Personal contacts, conversation history, calendar data | Vault (encrypted at Gold+) | HITL-approved agents |
| **Financial** | Bank transactions, invoices, tax data, accounting records | Odoo + encrypted vault | Finance Agent + HITL approval |

### 8.3a Cross-Domain Data Leakage Prevention

**[GOLD+]** Agents MUST NOT include data of a higher classification in outputs of a lower classification without HITL approval:

- **Financial** data MUST NOT appear in social media drafts, public reports, or external communications without explicit approval.
- **Sensitive** data (personal contacts, conversation history) MUST NOT appear in drafts routed to external systems.
- **Internal** data MUST NOT be included in PUBLIC outputs.

The policy-enforcement skill MUST scan outbound content for data classification violations before execution. If a violation is detected, the action is blocked and the human is notified with the specific data elements flagged.

### 8.4 MCP Server Security

- **Least Privilege**: Each MCP server MUST have the minimum OAuth scopes required for its function.
- **Token Isolation**: MCP server tokens MUST be stored in `.env`, never in code or vault.
- **Scope Audit [GOLD+]**: Monthly review of MCP server OAuth scopes. Remove any scope not actively used.
- **Connection Security**: All MCP server connections MUST use HTTPS/TLS. No plaintext API calls.

**[SILVER+] MCP Allow-List per Agent:** Each agent MUST only invoke its declared MCP dependencies. Unauthorized MCP calls MUST be blocked by the policy-enforcement skill and logged as a violation.

| Agent | Allowed MCP Servers |
|-------|-------------------|
| Communication Agent | email-mcp, slack-mcp, filesystem |
| Finance Agent | odoo-mcp, filesystem |
| Social Media Agent | browser-mcp, filesystem |
| Monitoring Agent | filesystem |
| Audit Agent | filesystem |
| Orchestrator | filesystem |
| Watchers | filesystem (write to /Inbox only) |

**[GOLD+]** browser-mcp MUST be restricted to a URL allow-list of declared social media domains and approved external services. Arbitrary URL access is prohibited. The allow-list is configurable via environment variable `BROWSER_MCP_ALLOWED_DOMAINS`.

### 8.5 Sandboxing

- **[BRONZE+]**: `DEV_MODE=true` environment variable MUST prevent all real external actions. When DEV_MODE is active, agents log intended actions without executing them.
- **[SILVER+]**: `--dry-run` flag on all action scripts. Dry-run mode MUST produce identical logs to real execution but skip the actual MCP call.
- **[GOLD+]**: Dedicated sandbox accounts (separate Gmail, separate Odoo instance, separate social media test accounts) for development and testing.

### 8.6 Vault Encryption

- **[GOLD+]**: Sensitive vault files (contacts, financial summaries, personal data) MUST be encrypted at rest.
- **[PLATINUM]**: Full vault encryption with key management. Decryption requires Local zone authorization.

---

## 9. Permission Boundaries

### 9.1 Four-Tier HITL Risk Model

Every agent action is classified into one of four risk tiers. The risk tier determines the required approval level.

| Risk Tier | Approval | Human Involvement | Examples |
|-----------|----------|-------------------|----------|
| **LOW** | Auto-approve | None (logged for audit) | Read inbox, read vault, generate reports, read financial data, read engagement data |
| **MEDIUM** | Notify | Human notified, may intervene | Draft email, draft social post, create draft invoice, create calendar event, summarize data |
| **HIGH** | Explicit approval | Human MUST approve before execution | Send email, publish social post, post invoice > $100, record expense > $100, schedule content, LinkedIn sales post |
| **CRITICAL** | Explicit + confirmation | Human MUST approve AND confirm | Reply-all/forward external, delete/modify posted financial entries, delete social post, change profile, bulk operations, payments > $1,000 |

### 9.2 Financial Thresholds

| Amount Range | Risk Tier | Approval Required |
|-------------|-----------|-------------------|
| $0 — $100 | MEDIUM | Notify (human informed, auto-proceed after timeout) |
| $100 — $1,000 | HIGH | Explicit approval required |
| $1,000 — $10,000 | CRITICAL | Explicit approval + confirmation required |
| > $10,000 | DENIED | System MUST NOT process. Human must execute manually. |

**Invariant:** Financial transactions MUST NEVER be retried automatically. Failed financial transactions are logged and queued for human review.

### 9.3 Complete Permission Boundary Table

| Agent | Action | Risk | Approval |
|-------|--------|------|----------|
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
| Monitoring | Send alert | MEDIUM | Auto (safety exception) |
| Monitoring | Block agent (safety override) | CRITICAL | Auto (safety override — logged for audit) |
| Audit | Read audit trails | LOW | Auto |
| Audit | Generate report | LOW | Auto |
| Audit | Block agent (compliance violation) | HIGH | Explicit |

### 9.4 Approval Lifecycle

**[SILVER+]** HITL approvals follow a defined lifecycle:

1. **Request**: Agent creates approval request with action details, risk tier, and context.
2. **Pending**: Approval enters the HITL queue. A notification is sent per the notification skill.
3. **Expiry**: Approvals expire after the configured HITL timeout (see Section 7.2). Expired approvals are logged as `expired` and the action is re-queued to `/Needs_Action`. Expired approvals MUST NOT be auto-approved.
4. **Decision**: Human approves or denies. Decision is logged with timestamp and reason.
5. **Execution Window**: An approved action MUST be executed within 1 hour of approval. After 1 hour, the approval is stale and MUST be re-requested. This prevents acting on outdated context.
6. **Revocation**: Human may revoke a previously granted approval at any time. If execution has begun, the system performs best-effort rollback (see Section 11.8).
7. **Audit**: All approval lifecycle events (request, expire, approve, deny, revoke) are logged.

**Invariant:** No HITL approval is permanent. Every approval is scoped to a single action instance and expires.

### 9.5 Permission Immutability

No agent may modify its own or another agent's:

- Risk tier classification
- HITL approval requirements
- MCP allow-list
- Vault write ACL
- Rate limits or daily action budget
- SKILL.md definition or agent definition

Changes to permission boundaries require:

1. Human proposal (or agent recommendation accepted by human).
2. Constitution amendment per Section 14.2.
3. ADR documentation.

**Self-modification of governance documents by any agent is prohibited unconditionally.**

### 9.6 Outbound Communication Safety

**[SILVER+]** Outbound communications MUST comply with the following limits:

| Constraint | Limit | Override |
|-----------|-------|---------|
| Maximum recipients per email | 10 | CRITICAL approval for > 10 |
| Maximum attachment size | 10 MB | CRITICAL approval for > 10 MB |
| BCC recipients | Internal addresses only | CRITICAL approval for external BCC |
| Reply-all | CRITICAL risk tier always | No override |
| Social media posts per platform per day | 5 | HIGH approval for > 5 |

**Recipient Validation:** Before any outbound communication, the system MUST:

1. Check the opt-out list (Section 13.4).
2. Verify the recipient address is well-formed.
3. Flag new/unknown recipients for human review (first-contact notification).

### 9.7 [PLATINUM] Zone-Based Permissions

**Cloud Zone Permissions:**
- ALLOWED: Read inbox, draft responses, draft social posts, schedule content, generate reports, read financial data, create draft accounting entries.
- DENIED: Send email, publish posts, approve payments, post invoices, access WhatsApp, access banking APIs, write to Dashboard.md.

**Local Zone Permissions:**
- ALLOWED: All Cloud permissions PLUS: approve/deny HITL requests, send emails, publish posts, post invoices, record payments, write to Dashboard.md, access WhatsApp, access banking APIs.
- EXCLUSIVE: Only Local zone may execute CRITICAL actions. No exceptions.

---

## 10. Auditability & Observability

### 10.1 Mandatory Logging

**All tiers MUST log every agent action.** No action may execute without producing an audit record.

**[BRONZE]** Log format: Markdown files in vault (`/Audit/` or inline).

**[SILVER]** Log format: Structured Markdown with consistent fields.

**[GOLD+]** Log format: JSON with the following required fields:

```json
{
  "request_id": "uuid-v4",
  "timestamp": "ISO-8601",
  "agent": "agent_name",
  "skill": "skill_name",
  "action": "action_description",
  "risk_tier": "LOW|MEDIUM|HIGH|CRITICAL",
  "approval_status": "auto|notified|approved|denied",
  "approved_by": "human|system|null",
  "input_summary": "brief input description",
  "output_summary": "brief output description",
  "status": "success|failure|pending",
  "error": "error message if applicable",
  "duration_ms": 1234,
  "metadata": {}
}
```

### 10.1a Agent Identity Verification

**[GOLD+]** Log entries MUST include a system-verified agent identifier, not a self-reported string. The orchestrator assigns each agent invocation a unique `session_id` at startup. The `session_id` and `agent` name in log entries MUST match the orchestrator's assignment table. Log entries with mismatched or missing session_ids are flagged as integrity violations by the Audit Agent.

### 10.2 Decision Traceability

**[SILVER+]** Every multi-step workflow MUST be traceable via a `request_id` that correlates all actions from event detection through final execution. The request_id MUST appear in:

- Watcher event log
- Agent reasoning trace (Plan.md)
- HITL approval record
- MCP server execution log
- Audit trail entry

### 10.3 Log Retention

- **[BRONZE]**: No formal retention requirement. Best-effort vault archival.
- **[SILVER]**: 30-day retention minimum.
- **[GOLD]**: 90-day retention minimum. Logs MUST be backed up.
- **[PLATINUM]**: 90-day active retention + 1-year cold storage. Automated log rotation.

### 10.4 Weekly Audit Reports

**[GOLD+]** The Audit Agent MUST generate a weekly compliance report containing:

1. Total actions executed (by agent, by risk tier).
2. HITL approval compliance (all HIGH/CRITICAL actions approved).
3. Policy violations detected (with severity and remediation status).
4. Financial transaction summary (totals, anomalies, threshold compliance).
5. Error rate and recovery statistics.
6. Agent performance metrics (response times, success rates).

### 10.5 Human Oversight Schedule

| Frequency | Duration | Activity | Tier Required |
|-----------|----------|----------|---------------|
| Daily | 2 minutes | Review Dashboard.md, check /Needs_Action | **[BRONZE+]** |
| Weekly | 15 minutes | Review audit report, approve pending items, check agent health | **[SILVER+]** |
| Monthly | 1 hour | Review financial reconciliation, rotate credentials, review OAuth scopes | **[GOLD+]** |
| Quarterly | Full review | Constitution review, agent performance assessment, architecture audit | **[GOLD+]** |

### 10.6 [PLATINUM] Real-Time Dashboards

The system MUST provide real-time observability dashboards showing:

- Agent status (running, idle, erroring)
- Watcher status (active, polling, failed)
- MCP server connectivity (connected, disconnected, degraded)
- HITL queue depth (pending approvals by risk tier)
- Error rates (per agent, per MCP server)
- Financial transaction totals (daily, weekly, monthly)

---

## 11. Failure & Recovery Principles

### 11.1 Error Categories

| Category | Examples | Retry? | Notification |
|----------|----------|--------|-------------|
| **Transient** | Network timeout, API rate limit, temporary unavailability | Yes (with backoff) | After 3 failures |
| **Permanent** | Invalid credentials, malformed request, resource not found | No | Immediate |
| **Financial** | Payment failure, invoice posting error, reconciliation mismatch | Never auto-retry | Immediate (CRITICAL) |
| **Safety** | Runaway agent, infinite loop, security breach | Immediate halt | CRITICAL alert |

### 11.2 Retry Strategy

**[SILVER+]** Transient errors MUST use exponential backoff:

| Attempt | Delay | Max Attempts |
|---------|-------|-------------|
| 1 | 1 second | — |
| 2 | 2 seconds | — |
| 3 | 4 seconds | — |
| Exhausted | Queue for human review | 3 total |

**HTTP Status Code Retry Matrix:**

| Status Code | Category | Retry? |
|-------------|----------|--------|
| 408, 429 | Transient (timeout, rate limit) | Yes |
| 500, 502, 503, 504 | Transient (server error) | Yes |
| 400, 401, 403, 404, 422 | Permanent (client error) | No |
| 409 | Conflict | No (log and queue for human) |

### 11.3 Circuit Breaker Pattern

**[GOLD+]** Each MCP server connection MUST implement a circuit breaker:

| State | Behavior | Transition |
|-------|----------|-----------|
| **CLOSED** | Normal operation, requests pass through | → OPEN after 3 failures in 1 minute |
| **OPEN** | All requests fail immediately (no MCP call) | → HALF_OPEN after 30 seconds |
| **HALF_OPEN** | Allow 1 test request | → CLOSED if success, → OPEN if failure |

### 11.4 Fallback Hierarchy

When a primary action fails and retries are exhausted:

1. **Alternative MCP**: Try an alternative MCP server if available (e.g., browser-mcp if email-mcp fails for reading).
2. **Cached Data**: Use cached/stale data if available (read operations only).
3. **Queue**: Place action in `/Needs_Action` for manual processing.
4. **Human Escalation**: Notify human via notification skill with full context.

### 11.5 Financial Action Safety

**Financial actions MUST NEVER be retried automatically.** This is a non-negotiable safety rule.

If a financial action fails:
1. Log the failure with full context.
2. Send CRITICAL notification to human.
3. Queue the action for manual review in `/Needs_Action`.
4. Do NOT retry, even if the error appears transient.

### 11.6 Watchdog Process

**[GOLD+]** A watchdog process MUST monitor all long-running components:

- Detect crashed watchers and restart them (max 3 restarts per hour).
- Detect hung agents (no output for > 5 minutes) and terminate them.
- Detect infinite loops (> 10 repeated identical actions) and halt the agent.
- Log all watchdog interventions for audit.

### 11.7 Quarantine Policy

**[SILVER+]** Items that repeatedly fail processing MUST be quarantined to prevent queue clogging:

1. **Threshold**: If an item fails processing **3 times** (across retries and re-queues), it is moved to `/Quarantine`.
2. **Quarantine Folder**: `/Quarantine` is a vault folder that no agent may process automatically. Only human review can move items out of quarantine.
3. **Notification**: Each quarantine event triggers a MEDIUM notification to the human with the item details and failure history.
4. **Review**: Quarantined items appear on the weekly audit report. Items quarantined for > 30 days are flagged for deletion review.
5. **Poison Item Detection**: If 3 or more items from the same source are quarantined within 1 hour, the source watcher is paused and a HIGH alert is sent.

### 11.8 System Rollback Strategy

**[GOLD+]** The system MUST support rollback for recoverable actions:

**Vault Rollback:**
- Vault state is version-controlled via Git. Any vault change can be reverted via `git revert` within the retention window.
- Before executing a batch of related vault changes, a Git commit checkpoint is created. If the batch fails partway, all vault changes in the batch are reverted to the checkpoint.

**External Action Rollback (Best-Effort):**
- **Email**: Sent emails cannot be recalled. The system logs the sent email and, if revocation is requested, sends a follow-up correction email (requires HITL approval).
- **Financial**: Draft invoices can be deleted. Posted invoices require a credit note (CRITICAL approval). Payments cannot be reversed by the system — human must act manually.
- **Social Media**: Published posts can be deleted (CRITICAL approval). Scheduled-but-not-yet-published posts can be cancelled (HIGH approval).

**Rollback Audit:**
- Every rollback action is logged with: original action request_id, rollback reason, rollback method, success/failure status.

### 11.9 Orchestrator Self-Healing

**[GOLD+]** The orchestrator MUST implement self-healing:

1. **Heartbeat**: Orchestrator writes a heartbeat timestamp to `vault/state/orchestrator_heartbeat` every 30 seconds.
2. **Watchdog Detection**: The watchdog process monitors the heartbeat. If no heartbeat for > 2 minutes, the watchdog restarts the orchestrator.
3. **State Recovery**: On restart, the orchestrator reads `Plan.md` and `/In_Progress/` to resume in-flight tasks.
4. **Max Restarts**: If the orchestrator crashes 3 times in 1 hour, the watchdog halts and sends a CRITICAL alert. Human intervention required.
5. **[PLATINUM]**: Cloud and Local zones each run an independent orchestrator. If one zone's orchestrator fails, the other zone continues within its permission boundaries.

### 11.10 [PLATINUM] Zone Fault Tolerance

- If Cloud zone fails: Local zone continues all operations independently. Cloud-owned drafts are queued until Cloud recovers.
- If Local zone fails: Cloud zone continues LOW/MEDIUM operations. All HIGH/CRITICAL actions are queued in `/Updates/` until Local recovers.
- If Vault sync fails: Both zones operate on their local vault copy. Conflict resolution occurs on next successful sync (Local zone wins conflicts per single-writer rule).

---

## 12. Human Sovereignty

### 12.1 Non-Negotiable Human Authority

The human operator has absolute authority over the system at all tiers. This authority cannot be delegated to any agent, skill, or automation.

**Human authority includes:**

1. **Override any agent decision** — at any time, for any reason, without justification.
2. **Stop any agent** — immediately halt execution of any agent or workflow.
3. **Modify any policy** — change permission boundaries, financial thresholds, rate limits, or any configuration.
4. **Revoke any approval** — withdraw previously granted approval, even if execution has begun (best-effort rollback).
5. **Amend this constitution** — modify any section with proper versioning and ADR documentation.

### 12.2 Progressive Autonomy Model

| Tier | Autonomy Level | Human Role |
|------|---------------|------------|
| **[BRONZE]** | Human-in-command | Human triggers all actions. AI drafts and suggests. Human executes. |
| **[SILVER]** | Human-on-the-loop | AI executes LOW/MEDIUM actions autonomously. Human approves HIGH/CRITICAL. Human monitors via Dashboard.md. |
| **[GOLD]** | Human-over-the-loop | AI operates autonomously on most operations. Human reviews weekly audit. Human approves exceptions and CRITICAL actions. |
| **[PLATINUM]** | Human-as-strategic-director | AI operates 24/7 continuously. Human sets policies and reviews summaries. Human approves only CRITICAL actions and policy changes. |

### 12.3 AI Deference Rule

When an agent is uncertain about the correct course of action, it MUST:

1. **Not act.** Uncertainty is never a justification for autonomous action.
2. **Explain the uncertainty.** Clearly state what is ambiguous and why.
3. **Present options.** If multiple valid paths exist, present them with tradeoffs.
4. **Wait for human direction.** Queue the item and await human input.

### 12.4 Human Accountability

**[ETH8]** The human operator remains legally and ethically accountable for all actions taken by the AI system. The AI is a tool operating under human direction. This accountability cannot be transferred to the AI system.

---

## 13. Ethical Constraints

### 13.1 Absolute Prohibitions

The following actions are prohibited at ALL tiers, regardless of human instruction:

1. **No deception.** AI MUST NOT generate content designed to deceive recipients about its nature or the accuracy of information.
2. **No impersonation.** AI MUST NOT impersonate the human operator or any other person without explicit disclosure.
3. **No silent execution.** AI MUST NOT take actions without logging. Every action produces an audit trail.
4. **No irreversible action without approval.** Actions that cannot be undone (delete, permanent send, financial posting) MUST require HITL approval at HIGH or CRITICAL tier.

### 13.2 Restricted Domains

**[ETH1]** AI MUST NOT act autonomously in the following domains, regardless of risk tier classification:

- **Emotional/personal matters**: Relationship advice, grief responses, mental health support.
- **Legal matters**: Contract interpretation, legal advice, dispute resolution.
- **Medical matters**: Health advice, medical decisions, treatment recommendations.
- **Financial edge cases**: Tax advice, investment decisions, insurance claims.

In these domains, the AI MUST immediately defer to the human operator with a clear explanation of why it cannot proceed autonomously.

### 13.3 AI Disclosure

**[ETH2]** All AI-generated external communications MUST disclose AI involvement:

- **Email**: Footer text: "This message was drafted with AI assistance."
- **Social Media**: Tag or note: "#AIAssisted" or platform-equivalent disclosure.
- **Documents**: Header or footer indicating AI-generated content.
- **Chat/Messaging**: Initial disclosure that the conversation involves AI assistance.

### 13.4 Contact Opt-Out

**[ETH4]** Any recipient of AI-generated communication MUST have the ability to opt out of future AI-generated messages. The system MUST:

1. Maintain an opt-out list in the vault.
2. Check the opt-out list before generating any outbound communication.
3. Respect opt-out requests immediately (within 1 business day).
4. Never send AI-generated content to opted-out contacts.

### 13.5 Data Minimization

**[ETH6]** The system MUST:

1. Collect only data necessary for the current operation.
2. Not retain data beyond the configured retention period (Section 10.3).
3. Not aggregate personal data across domains without explicit human authorization.
4. Prefer local storage over cloud storage for sensitive data.
5. Never transmit telemetry, usage data, or personal data to third parties.

### 13.6 Local-First Principle

**[ETH7]** Sensitive data (personal contacts, financial records, health information, private communications) MUST be stored locally first. Cloud storage of sensitive data is permitted only at Platinum tier with:

- Encryption at rest and in transit.
- Access restricted to authorized agents via the secrets firewall.
- Human approval for any cloud storage of sensitive data categories.

---

## 14. Continuous Evolution

### 14.1 Constitution Versioning

This constitution follows semantic versioning:

- **MAJOR**: Breaking changes to governance rules, permission boundaries, or architecture principles.
- **MINOR**: Addition of new sections, new tier requirements, or new agent rules.
- **PATCH**: Corrections, clarifications, and formatting changes.

### 14.2 Amendment Process

Amendments to this constitution require:

1. **Proposal**: Written description of the proposed change with justification.
2. **Impact Analysis**: Assessment of which agents, skills, and workflows are affected.
3. **Human Approval**: Explicit approval from the human operator.
4. **ADR Documentation**: Architectural Decision Record documenting the change, alternatives considered, and rationale.
5. **Version Update**: Constitution version number incremented per semantic versioning rules.
6. **Notification**: All agents notified of the change (via notification skill or vault update).

### 14.3 System Learning Boundaries

The AI system MAY:

- **Recommend** policy changes based on observed patterns (e.g., "Email response drafts are approved 95% of the time — consider reducing to MEDIUM risk tier").
- **Suggest** new skills based on repeated manual workflows.
- **Propose** threshold adjustments based on historical data.

The AI system MUST NOT:

- **Auto-change** any policy, threshold, or permission boundary. All changes require human approval.
- **Self-modify** this constitution or any governance document.
- **Learn** from interactions in ways that alter behavior without human review.

### 14.4 Architecture Decision Records

**[GOLD+]** Significant architectural decisions MUST be documented in ADRs stored in `history/adr/`. An ADR is required when:

- A decision has long-term consequences (framework choice, data model, API design).
- Multiple viable alternatives were considered with significant tradeoffs.
- The decision is cross-cutting and influences system-wide design.

### 14.5 [PLATINUM] A2A Upgrade Path

The system MAY evolve from file-based agent coordination to Agent-to-Agent (A2A) direct messaging:

1. **Phase 1 (Current)**: File-based handoffs via vault (/Inbox, /Needs_Action, /Done, /Updates, /In_Progress).
2. **Phase 2 (Optional)**: A2A messaging layer replaces file handoffs for real-time coordination. Vault remains as persistent memory and audit store.
3. **Constraint**: A2A upgrade MUST NOT reduce audit trail completeness. All A2A messages MUST be logged with the same fields as file-based actions.

---

## Appendix A: Hackathon Requirement Traceability

Every hackathon requirement is covered by one or more sections of this constitution. The traceability matrix below confirms complete coverage.

### Bronze Requirements

| # | Requirement | Constitution Coverage |
|---|---|---|
| B1 | Obsidian vault with Dashboard.md and Company_Handbook.md | S2.1(1-3), S4.2(Layer 1) |
| B2 | One working Watcher script (Gmail OR filesystem) | S2.1(5), S4.2(Layer 2) |
| B3 | Claude Code reading from and writing to vault | S2.1(6), S4.2(Layer 5) |
| B4 | Basic folder structure: /Inbox, /Needs_Action, /Done | S2.1(4), S4.2(Layer 1) |
| B5 | All AI functionality as Agent Skills | S2.1(7), S5.3 |

### Silver Requirements

| # | Requirement | Constitution Coverage |
|---|---|---|
| S1 | All Bronze requirements | Tier Inheritance Rule |
| S2 | 2+ Watcher scripts | S2.2(1), S4.2(Layer 2) |
| S3 | LinkedIn sales posts | S2.2(6), S9.1(HIGH) |
| S4 | Claude reasoning loop with Plan.md | S2.2(4), S4.4 |
| S5 | One working MCP server | S2.2(3), S4.2(Layer 5), S8.4 |
| S6 | HITL approval workflow | S2.2(2), S9.1, S12 |
| S7 | Basic scheduling via cron | S2.2(5), S7.4 |
| S8 | All AI as Agent Skills | S2.2(7), S5.3 |

### Gold Requirements

| # | Requirement | Constitution Coverage |
|---|---|---|
| G1 | All Silver requirements | Tier Inheritance Rule |
| G2 | Cross-domain (Personal + Business) | S2.3(1), S3.2, S4.2(Layer 1 Gold) |
| G3 | Odoo 19+ accounting | S2.3(2), S4.5, S8.2 |
| G4 | Facebook + Instagram integration | S2.3(3), S9.3, S13.3 |
| G5 | Twitter/X integration | S2.3(4), S9.3 |
| G6 | Multiple MCP servers | S2.3(5), S4.2(Layer 5 Gold), S8.4 |
| G7 | Weekly audit + CEO briefing | S2.3(6), S10.4, S10.5 |
| G8 | Error recovery + graceful degradation | S2.3(7), S11 |
| G9 | Comprehensive audit logging | S2.3(8), S10.1(Gold) |
| G10 | Ralph Wiggum persistence loop | S2.3(9), S4.4 |
| G11 | Architecture documentation + lessons | S2.3(10), S14.4 |
| G12 | All AI as Agent Skills | S2.3(11), S5.3 |

### Platinum Requirements

| # | Requirement | Constitution Coverage |
|---|---|---|
| P1 | All Gold requirements | Tier Inheritance Rule |
| P2 | Cloud 24/7 operation | S2.4(1), S4.2(Layer 3/4 Platinum), S7.2 |
| P3 | Work-Zone Specialization | S2.4(2), S3.2, S9.4 |
| P4 | Cloud owns: email triage + drafts + social scheduling | S2.4(2 Cloud Zone), S9.4(Cloud) |
| P5 | Local owns: approvals + WhatsApp + payments + send | S2.4(2 Local Zone), S9.4(Local), S12 |
| P6 | Vault sync via Git/Syncthing | S2.4(3), S4.2(Layer 1 Platinum) |
| P7 | Claim-by-move rule | S2.4(4), S3.2 |
| P8 | Single-writer rule for Dashboard.md | S2.4(3), S3.2, S8.2 |
| P9 | Cloud writes /Updates/, Local merges to Dashboard | S2.4(3), S4.2(Layer 1 Platinum) |
| P10 | Secrets never sync | S2.4(5), S8.2(Platinum) |
| P11 | Odoo on Cloud VM (HTTPS, backups, health) | S2.4(6), S4.5, S8.4 |
| P12 | Cloud Odoo = draft-only | S2.4(7), S9.4(Cloud) |
| P13 | Local approval for posting invoices/payments | S2.4(7), S9.4(Local), S12 |
| P14 | Optional A2A upgrade | S2.4(10), S14.5 |
| P15 | End-to-end demo flow | S2.4(9), S10.2 |

### Architecture Requirements

| # | Requirement | Constitution Coverage |
|---|---|---|
| A1 | Claude Code as reasoning engine | S1.1, S4.1 |
| A2 | Obsidian vault as memory/GUI | S4.1, S4.2(Layer 1) |
| A3 | Watcher scripts for perception | S4.1, S4.2(Layer 2) |
| A4 | MCP servers for external actions | S4.1, S4.2(Layer 5) |
| A5 | Ralph Wiggum Stop hook | S4.4, S11 |
| A6 | Python Orchestrator | S4.1, S4.2(Layer 3) |
| A7 | Credential management (.env) | S8.2 |
| A8 | Sandboxing (DEV_MODE, --dry-run) | S8.5, S7.3 |
| A9 | Audit logging (JSON format) | S10.1(Gold) |
| A10 | Permission boundaries table | S9.3 |
| A11 | Error categories + retry + degradation | S11.1, S11.2, S11.4 |
| A12 | Watchdog process | S11.6, S4.2(Layer 3 Platinum) |
| A13 | Process management (PM2/supervisord) | S7.4, S4.2(Layer 3 Platinum) |

### Security Requirements

| # | Requirement | Constitution Coverage |
|---|---|---|
| SEC1 | No plaintext credentials | S8.2(SEC1) |
| SEC2 | Environment variables for API keys | S8.2(SEC2) |
| SEC3 | Secrets manager for banking | S8.2(SEC3) |
| SEC4 | .env in .gitignore | S8.2(SEC4) |
| SEC5 | Monthly credential rotation | S8.2(SEC5) |
| SEC6 | DEV_MODE flag | S8.5, S8.2(SEC6) |
| SEC7 | --dry-run on all action scripts | S8.5, S8.2(SEC7) |
| SEC8 | Sandbox accounts for dev | S8.5, S8.2(SEC8) |
| SEC9 | Rate limiting | S7.3 |
| SEC10 | Audit log format | S10.1(Gold) |
| SEC11 | 90-day log retention | S10.3 |
| SEC12 | Permission boundary table | S9.3 |

### Ethics Requirements

| # | Requirement | Constitution Coverage |
|---|---|---|
| ETH1 | No autonomous action in emotional/legal/medical/financial edge cases | S13.2 |
| ETH2 | Disclose AI involvement | S13.3 |
| ETH3 | Maintain audit trails | S10 |
| ETH4 | Contact opt-out from AI communication | S13.4 |
| ETH5 | Regular reviews of AI decisions | S10.5 |
| ETH6 | Minimize data collection | S13.5 |
| ETH7 | Local-first sensitive data | S8.6, S13.6 |
| ETH8 | Human accountable for AI actions | S12.4 |
| ETH9 | Oversight schedule (daily/weekly/monthly/quarterly) | S10.5 |

---

## Appendix B: System Summary

| Dimension | Count |
|-----------|-------|
| Agents (Development Pipeline) | 10 |
| Agents (LifeOps Layer) | 5 |
| **Total Agents** | **15** |
| Skills (Development) | 15 |
| Skills (LifeOps) | 13 |
| Skills (System Safety) | 3 |
| **Total Skills** | **31** |
| MCP Servers | 7 |
| HITL Risk Tiers | 4 |
| Constitution Sections | 14 |
| Hackathon Requirements Covered | 74 |
| Safety Subsections Added (v1.1.0) | 13 |

---

## Appendix C: Amendment Log

| Version | Date | Type | Changes |
|---------|------|------|---------|
| 1.0.0 | 2026-02-16 | Initial | Full 14-section constitution with 4 tiers and hackathon traceability |
| 1.1.0 | 2026-02-17 | MINOR | Production hardening from governance audit. Added: S3.3 Routing Depth Limit, S4.4 Vault Integrity, L1a Vault Write ACL, S7.1a Idempotency Keys, S7.1b Queue Specification, S7.3 Daily Action Budget, S8.3a Data Leakage Prevention, S8.4 MCP Allow-List per Agent, S9.4 Approval Lifecycle, S9.5 Permission Immutability, S9.6 Outbound Communication Safety, S10.1a Agent Identity Verification, S11.7 Quarantine Policy, S11.8 System Rollback Strategy, S11.9 Orchestrator Self-Healing. Strengthened prompt versioning (S5.1). |

---

**Version**: 1.1.0 | **Ratified**: 2026-02-16 | **Last Amended**: 2026-02-17
