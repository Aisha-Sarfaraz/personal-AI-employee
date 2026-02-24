---
id: "0007"
title: Silver Tier Spec Clarification Round 6
stage: spec
date: 2026-02-20
surface: agent
model: claude-sonnet-4-6
feature: 002-silver-tier
branch: 001-bronze-tier
user: USER-PC
command: "/sp.clarify (sixth session — dashboard health, architecture box, contradictions)"
labels: ["clarification", "silver-tier", "dashboard-health", "architecture", "update_dashboard", "queue", "mcp"]
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

/sp.clarify (sixth clarification session — fresh scan after session 5 changes)

## Response snapshot

Fresh ambiguity scan identified 1 implementation-blocking question plus 7 direct fixes applied
without consuming question quota:

**Direct fixes (no questions used):**
- Architecture "SCHEDULED SKILLS" box: replaced with "SELF-GUARDED SKILLS" box — corrected to
  show both skills called every cycle with internal guards (not "not every cycle" phrasing)
- SC-012: "two concurrent watcher threads" → "Four Concurrent Watcher Threads"
- Section 1: `update_dashboard.py` moved from "unchanged" to "minimally extended" list
- Files to Modify table: `update_dashboard.py` row updated with health dict details
- `mcp>=1.0.0` added to requirements.txt additions (MCP Python SDK was missing)
- `vault/Watch/linkedin_mock/` folder added to FR-J03 mock folder structure
- `vault/Watch/linkedin_mock/sample_post.json` added to New Files table (Section 5)

**Q1**: What data does each watcher health row in Dashboard.md show? → **B: Last-poll timestamp + item count**
- Section 6 contracts: `update_dashboard` now specifies shared dict format
  `{last_poll: ISO_timestamp, items_this_cycle: int, status: "OK"/"ERROR"}`
- Files to Modify table: `update_dashboard.py` row describes reading orchestrator shared dict
- Session bullet added

## Outcome

- ✅ Impact: 1 more implementation blocker resolved. Dashboard health data format is now explicit
  and matches the orchestrator shared-dict pattern. 7 direct fixes removed contradictions
  (architecture box, SC-012 count, update_dashboard.py scope, missing mcp package, missing
  linkedin_mock folder).
- 🧪 Tests: No new tests (clarification session). 416 tests remain green.
- 📁 Files: specs/002-silver-tier/spec.md (15 edits: Q1×3, direct fixes×7, session bullet×1, stale refs×4)
- 🔁 Next prompts: `/sp.clarify` again — 1 more session for final scan; then `/sp.plan`
- 🧠 Reflection: "SCHEDULED SKILLS" box was an internal architectural contradiction — the self-guard
  clarification from session 3 made the box label wrong but the box text was not updated. Future specs
  should keep architectural diagram text in sync with FR decisions as they are made, not at the end.

## Evaluation notes (flywheel)

- Failure modes observed: None; Q1 answered on first attempt
- Graders run and results (PASS/FAIL): Manual — architecture box shows "SELF-GUARDED SKILLS";
  SC-012 says "Four"; update_dashboard.py in Files to Modify; mcp>=1.0.0 in requirements
- Prompt variant (if applicable): Sixth /sp.clarify session — cumulative across 6 sessions
- Next experiment: Auto-diff architectural diagram text against FR decisions after each session
  to catch label drift proactively
