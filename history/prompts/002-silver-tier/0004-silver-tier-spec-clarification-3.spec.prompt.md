---
id: "0004"
title: Silver Tier Spec Clarification Round 3
stage: spec
date: 2026-02-20
surface: agent
model: claude-sonnet-4-6
feature: 002-silver-tier
branch: 001-bronze-tier
user: USER-PC
command: "/sp.clarify (third session, post base_watcher.py and generate_linkedin_post trigger)"
labels: ["clarification", "silver-tier", "base_watcher", "generate_linkedin_post", "dry_run", "self-guard"]
links:
  spec: specs/002-silver-tier/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - specs/002-silver-tier/spec.md
tests:
  - "No new tests (clarification-only session; 416 tests still passing)"
---

## Prompt

/sp.clarify (third clarification session — continued after context reset)

## Response snapshot

Ambiguity scan continued from session 3. Two remaining questions answered:

1. **base_watcher.py dry_run sharing** (MEDIUM) — Q: Does `base_watcher.py` get shared `dry_run`
   + `_load_mock_items()` or does each watcher handle independently?

   **Q1**: → **A: Extend base_watcher.py (shared base)**
   - FR-J02 updated: explicit statement that all three new watchers delegate to base methods
   - Note added: `WhatsAppWatcher` already follows this pattern; `GmailWatcher` and `LinkedInWatcher` MUST do the same
   - Prevents duplicated dry-run logic across three watchers

2. **generate_linkedin_post trigger mechanism** (HIGH) — Q: Self-guard inside skill or
   orchestrator-level scheduling?

   **Q2**: → **A: Self-guard inside skill (same pattern as weekly_briefing)**
   - FR-F03 rewritten: orchestrator calls on every scan cycle; skill self-guards on (a) enabled
     flag and (b) rate_limiter posts-today count
   - Returns `{skipped: 1}` immediately when either gate fails
   - Orchestrator has no scheduling logic for this skill
   - Context diagram stale ref `browser-mcp LinkedIn [NEW]` fixed → `Playwright LinkedIn [NEW]`
   - FR-I01 `linkedin_post` template step 2 description fixed → "via Playwright direct"

## Outcome

- ✅ Impact: 2 additional implementation blockers resolved. base_watcher.py extension pattern
  confirmed (single source of truth for dry_run). generate_linkedin_post self-guard pattern
  confirmed (orchestrator stays thin; same as weekly_briefing). 2 stale browser-mcp references
  eliminated from spec.
- 🧪 Tests: No new tests (clarification session). 416 tests remain green.
- 📁 Files: specs/002-silver-tier/spec.md (5 edits: clarification bullets ×2, FR-J02, FR-F03, context diagram + template description)
- 🔁 Next prompts: `/sp.plan` to generate specs/002-silver-tier/plan.md
- 🧠 Reflection: The self-guard pattern (skill decides for itself) is consistently cleaner than
  orchestrator-level scheduling for periodic skills. weekly_briefing established the precedent;
  applying it to generate_linkedin_post keeps the orchestrator as a thin dispatcher.

## Evaluation notes (flywheel)

- Failure modes observed: None; both questions answered in first attempt
- Graders run and results (PASS/FAIL): Manual check — grep "browser-mcp" in spec shows 0 remaining incorrect refs; FR-J02 confirms base class extension; FR-F03 matches weekly_briefing pattern
- Prompt variant (if applicable): Third /sp.clarify session — continuing from context-reset state
- Next experiment: After all clarification sessions complete, auto-validate spec for internal consistency before /sp.plan
