---
id: "0001"
title: Gold Tier Spec Writing
stage: spec
date: 2026-02-25
surface: agent
model: claude-sonnet-4-6
feature: 003-gold-tier
branch: 003-gold-tier
user: USER-PC
command: /sp.specify
labels: ["spec", "gold-tier", "odoo", "facebook", "instagram", "twitter", "ralph-wiggum", "audit-logging", "error-recovery", "mcp"]
links:
  spec: specs/003-gold-tier/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - specs/003-gold-tier/spec.md
  - specs/003-gold-tier/checklists/requirements.md
  - history/prompts/003-gold-tier/0001-gold-tier-spec-writing.spec.prompt.md
tests:
  - null
---

## Prompt

/sp.specify

# Gold Tier Specification Request: Autonomous AI Employee — Full Business Operations

## Context & Predecessor

**Feature:** `003-gold-tier`
**Branch:** `003-gold-tier`
**Tier:** GOLD (Autonomous Employee)
**Predecessor:** `specs/002-silver-tier/spec.md`
  - Silver: 531 passing tests, 73.36% coverage, SC-010–SC-020 verified
  - Bronze: 385 passing tests, SC-001–SC-009 verified (all still green)

All Bronze and Silver infrastructure is preserved unchanged. Gold adds new files and
capabilities; it does not replace or refactor existing Silver/Bronze code except where
explicitly required to wire new capabilities.

## Resolved Clarifications (pre-answered)

| ID | Question | Resolution |
|----|----------|-----------|
| C1 | Odoo 19 setup | Docker Compose — docker-compose.odoo.yml; URL http://localhost:8069, DB fte_db |
| C2 | Meta Graph API auth | Long-lived Page access token in .env as FACEBOOK_ACCESS_TOKEN |
| C3 | Twitter/X API tier | Free tier — 1,500 tweets/month; 24h poll interval |
| C4 | Ralph Wiggum hook | Auto via install_schedule.py extension |
| C5 | Finance Watcher source | Odoo primary + CSV fallback |
| C6 | CEO Briefing delivery | Vault-only |

## Gold Tier Capabilities (G1–G11)

G1: Full cross-domain integration (Personal + Business)
G2: Odoo Community accounting via MCP (Odoo 19+ JSON-RPC)
G3: Finance Watcher (implements Silver stub; Odoo + CSV fallback)
G4: Facebook & Instagram integration (engagement + posting)
G5: Twitter/X integration (Free tier; metrics + posting)
G6: Multiple MCP servers (config/mcp_servers.yaml registry)
G7: Enhanced CEO Briefing (Revenue, Expense, Bottleneck, Social Summary)
G8: Error recovery & graceful degradation (@with_retry + ErrorCategory)
G9: Comprehensive audit logging (Gold JSON-Lines schema, 9 fields)
G10: Ralph Wiggum autonomous loop (Stop hook + file-movement completion)
G11: All AI functionality as Agent Skills

Success Criteria: SC-021 through SC-030
Non-Goals: Platinum cloud deploy, A2A, open banking, circuit breakers

## Response snapshot

Created Gold Tier specification at `specs/003-gold-tier/spec.md` (~1,300 lines).

**Structure (13 sections, mirrors Silver spec exactly):**
- Context: builds on Silver 531 tests; 10 Gold capabilities described
- Clarifications: all 6 pre-resolved (C1–C6) + 6 additional session clarifications
- Feature Overview: 10 new capabilities (G1–G10); Silver/Bronze invariants listed
- User Stories: 9 stories (US-016 to US-030 conceptually; P1/P2/P3) with edge cases
- Functional Requirements: 9 FR groups (FR-K through FR-S); 42 individual requirements
- System Architecture: ASCII data flow diagram + Ralph Wiggum Stop hook flow
- New Components Map: 36 files to create + 8 files to modify (minimal patches)
- Skill Interface Contracts: post_facebook, post_twitter, generate_invoice,
  accounting_audit, error_recovery, OdooMCPClient
- Config Changes: settings.yaml stanzas + .env.example vars
- Vault Changes: new folders + Current_Month.md template
- Success Criteria: SC-021 to SC-030 (measurable, technology-agnostic)
- Out of Scope: 9 explicit exclusions (Platinum, A2A, open banking, etc.)
- Risks & Mitigations: 4 risks (Odoo setup, Meta token expiry, Twitter quota, Ralph loop)
- Project Structure: full directory tree showing Gold additions
- Constitution Traceability: 11 capability-to-constitution mappings

**Also created:** `specs/003-gold-tier/checklists/requirements.md` — all 16 checklist items pass.

**Branch:** `003-gold-tier` created and checked out.

## Outcome

- ✅ Impact: Gold Tier spec written; branch 003-gold-tier created; all 6 clarifications resolved; 10 capabilities (G1–G10) fully specified with FR groups, user stories, and acceptance scenarios
- 🧪 Tests: No tests run (spec-only deliverable); Silver 531 + Bronze 385 tests remain unchanged
- 📁 Files: specs/003-gold-tier/spec.md (created), specs/003-gold-tier/checklists/requirements.md (created), history/prompts/003-gold-tier/0001-gold-tier-spec-writing.spec.prompt.md (this file)
- 🔁 Next prompts: /sp.plan (proceed to architecture planning) | /sp.clarify (if further clarification needed before planning)
- 🧠 Reflection: All 6 clarifications pre-resolved via AskUserQuestion before spec was written — avoided the 8-round clarification loop that Silver required. Gold spec mirrors Silver structure exactly (13 sections), enabling consistent downstream tooling.

## Evaluation notes (flywheel)

- Failure modes observed: none — all clarifications pre-resolved; spec written in single pass
- Graders run and results (PASS/FAIL): checklist validation PASS (16/16 items)
- Prompt variant (if applicable): gold-tier-prompt-v1 (professional prompt with 6 pre-answered clarifications)
- Next experiment (smallest change to try): /sp.plan to generate architecture plan and identify ADRs
