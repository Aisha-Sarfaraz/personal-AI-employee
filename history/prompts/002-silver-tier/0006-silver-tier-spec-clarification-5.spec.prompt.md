---
id: "0006"
title: Silver Tier Spec Clarification Round 5
stage: spec
date: 2026-02-20
surface: agent
model: claude-sonnet-4-6
feature: 002-silver-tier
branch: 001-bronze-tier
user: USER-PC
command: "/sp.clarify (fifth session — execute_plan contradiction, watcher threading, linkedin cadence)"
labels: ["clarification", "silver-tier", "execute_plan", "threading", "linkedin-cadence", "frequency_days"]
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

/sp.clarify (fifth clarification session — fresh scan after session 4 changes)

## Response snapshot

Fresh ambiguity scan identified 3 implementation-blocking gaps plus 5 stale references
(fixed directly without asking):

**Stale refs fixed (no questions used):**
- Feature Overview item 3: "via browser-mcp" → "via Playwright direct"
- US-05 acceptance: "browser-mcp publishes" → "Playwright publishes"
- Session 2026-02-20 bullet: "browser-mcp login" → "Playwright setup_session() login"
- Architecture diagram: WhatsAppWatcher "(Twilio REST API)" → "(Playwright, WhatsApp Web)"
- Architecture diagram: Added LinkedInWatcher to Perception Layer (was missing entirely);
  updated "3 concurrent" → "4 concurrent" watcher threads

**Q1**: `execute_plan.py` "unchanged" claim contradicts FR-D06 and FR-J04 → **B: Mark as modified**
- Section 1 updated: `execute_plan.py` moved from "unchanged" to "minimally extended"
- Files to Modify table: `execute_plan.py` row added with scope description
- Session bullet added

**Q2**: Watcher concurrency model → **A: Daemon threads**
- Architecture diagram already corrected (4 watcher threads)
- `src/orchestrator.py` modification note updated: "all 4 watchers as threading.Thread(daemon=True)"
- Session bullet added

**Q3**: `generate_linkedin_post` cadence control → **A: frequency_days interval**
- FR-F03 rewritten: guard checks vault/Logs/ for posts in last N days; max_posts_per_day removed
- FR-C06 updated: 1 post per frequency_days (not "5 per day")
- settings.yaml: `max_posts_per_day` removed; `frequency_days` comment clarified
- Session bullet added

## Outcome

- ✅ Impact: 3 more implementation blockers resolved. execute_plan.py modification scope is now
  explicit and non-contradictory. Threading model confirmed (daemon threads, per-watcher intervals).
  LinkedIn posting cadence uses frequency_days interval guard (not daily cap), consistent with
  brand quality intent.
- 🧪 Tests: No new tests (clarification session). 416 tests remain green.
- 📁 Files: specs/002-silver-tier/spec.md (12 edits: Q1×3, Q2×2, Q3×4, stale refs×5, session bullets×3)
- 🔁 Next prompts: `/sp.plan` — spec has now had 5 clarification sessions across 16 questions
- 🧠 Reflection: The "unchanged" claim in Section 1 was a maintenance hazard — a statement written
  at spec creation time that became stale as FRs were added. Future specs should track modified-file
  claims in the Files to Modify table only (single source of truth), and Section 1 should not make
  "unchanged" claims about files with Silver-level extension FRs.

## Evaluation notes (flywheel)

- Failure modes observed: None; all 3 questions answered on first attempt
- Graders run and results (PASS/FAIL): Manual — Section 1 no longer claims execute_plan.py
  unchanged; FR-F03 uses frequency_days; architecture diagram shows 4 watcher threads
- Prompt variant (if applicable): Fifth /sp.clarify session — cumulative across 5 sessions
- Next experiment: At /sp.plan time, automatically diff the "Files to Modify" table against
  all FR "MUST" statements to catch contradictions like the execute_plan.py case automatically
