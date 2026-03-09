---
id: "0004"
title: Gold Tier Implementation Plan
stage: plan
date: 2026-02-25
surface: agent
model: claude-sonnet-4-6
feature: 003-gold-tier
branch: 003-gold-tier
user: USER-PC
command: /sp.plan
labels: ["gold-tier","planning","odoo","meta-api","twitter","mcp","ralph-loop","error-recovery"]
links:
  spec: specs/003-gold-tier/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - specs/003-gold-tier/plan.md
  - specs/003-gold-tier/research.md
  - specs/003-gold-tier/data-model.md
  - specs/003-gold-tier/quickstart.md
  - specs/003-gold-tier/contracts/odoo_mcp_tools.md
  - specs/003-gold-tier/contracts/social_skills.md
  - specs/003-gold-tier/contracts/finance_watcher.md
  - specs/003-gold-tier/contracts/error_recovery.md
  - specs/003-gold-tier/contracts/ralph_loop.md
  - CLAUDE.md
tests:
  - none (plan stage — tests defined in tasks.md via /sp.tasks)
---

## Prompt

/sp.plan

(Continued from previous session; all 4 Phase 0 research agents had completed. Phase 1 artifacts written in this session.)

## Response snapshot

Wrote all Gold Tier plan artifacts for `specs/003-gold-tier/`:

**research.md** — Consolidated all 4 research agent findings:
1. Odoo JSON-RPC: `requests` library, per-call auth, `/web/dataset/call_kw`, stateless `execute_kw(db, uid, pwd, model, method, args, kwargs)` pattern
2. Meta Graph API v20.0: `POST /{page-id}/feed` (Facebook), two-step Instagram (create container → publish), long-lived Page token, `Authorization: Bearer`, 200 calls/hour
3. Twitter API v2: `tweepy>=4.14`, Bearer token for reads, OAuth 1.0a for writes, `TWITTER_USER_ID` static env var, 1 tweet/day guard
4. MCP Python SDK: `mcp.server.Server` class (NOT FastMCP), `@server.list_tools()` + `@server.call_tool()` decorators, anyio stdio, direct handler testing in pytest

**data-model.md** — Five Gold entities: `FinanceTransaction`, `AuditEntry` (Gold extension), `RalphLoopState`, `OdooInvoice`, `SocialPost`; vault folder structure; state file paths.

**5 contracts** — Complete API contracts for: Odoo MCP 6 tools + OdooMCPClient, social skills (post_facebook/post_twitter + watcher contracts), Finance Watcher (dedup, CSV format, month rollover), error recovery (@with_retry, ErrorCategory, degradation), Ralph loop (ralph_loop.py + stop_hook.py).

**quickstart.md** — Step-by-step setup: Docker Compose Odoo, Meta Graph API token exchange, Twitter Developer Portal, .env configuration, stop hook registration, smoke tests, troubleshooting.

**plan.md** — Full implementation plan: 8 phases covering 36 implementation tasks (~120 new tests); invariant checks; scope; Bronze/Silver invariant; 3 ADR suggestions.

Agent context updated via `update-agent-context.sh claude`.

## Outcome

- ✅ Impact: Complete Gold Tier architecture plan ready for `/sp.tasks`; all unknowns resolved; all contracts specified; 8 implementation phases defined with ~120 new tests targeting SC-021 through SC-032
- 🧪 Tests: None run (plan stage); ~120 Gold tests specified across 8 phases
- 📁 Files: 10 files created/updated (plan.md, research.md, data-model.md, quickstart.md, 5 contracts, CLAUDE.md)
- 🔁 Next prompts: `/sp.tasks` to generate atomic task list with Red-Green-Refactor TDD breakdown; then `/sp.implement`
- 🧠 Reflection: Phase 0 research completed across 4 parallel agents (Odoo, Meta, Twitter, MCP SDK) before this session resumed. All clarification answers from spec were encoded in contracts. Additive-only approach preserves all 916 existing tests.

## Evaluation notes (flywheel)

- Failure modes observed: Session compacted mid-plan (context limit); resumed cleanly from summary; no data lost
- Graders run and results (PASS/FAIL): N/A (plan stage)
- Prompt variant (if applicable): N/A
- Next experiment (smallest change to try): Run `/sp.tasks` to generate atomic TDD tasks; verify SC-021–SC-032 acceptance criteria are represented as test cases
