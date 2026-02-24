---
id: "0005"
title: Silver Tier Spec Clarification Round 4
stage: spec
date: 2026-02-20
surface: agent
model: claude-sonnet-4-6
feature: 002-silver-tier
branch: 001-bronze-tier
user: USER-PC
command: "/sp.clarify (fourth session — queue drain, LinkedIn DOM, Gmail mock schema)"
labels: ["clarification", "silver-tier", "queue-drain", "linkedin-playwright", "gmail-mock-schema", "execute_plan"]
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

/sp.clarify (fourth clarification session — new ambiguity scan post all previous sessions)

## Response snapshot

Full ambiguity scan identified 3 remaining implementation-blocking gaps plus 6 stale
`browser-mcp` references (fixed directly without asking):

**Stale refs fixed (no questions used):**
- settings.yaml: `linkedin.enabled` comment corrected
- vault/state: linkedin_session description corrected
- Risk 2: "browser-mcp" → "Playwright" in 2 places
- project structure: action_executor description corrected
- SC-015: "With browser-mcp running" → "vault/state/linkedin_session/ present"
- .env.example LinkedIn comment corrected

**Q1**: Rate-limited action queue processing → **A: Drain on next scan cycle**
- FR-D01 updated: queue entry appended on rate-limit; returns `{queued: true}` not exception
- FR-D06 added: `execute_plan.py` drains queue at start of each cycle; retries if limit reset;
  purges entries older than 24h; queue entry schema `{action_type, details, plan_id, queued_at}`
- US-15 updated: queue drain behavior described

**Q2**: LinkedIn watcher Playwright target page → **A: Profile activity page**
- FR-C01 updated: target URL `https://www.linkedin.com/in/<username>/detail/recent-activity/`;
  `settings.yaml` `watchers.linkedin.username` field added
- Extracted fields: reactions (aria-label), comments, post_preview (200 chars), post_url
- Item ID: SHA256 of post_url[:12]; type: social_media_engagement

**Q3**: Gmail mock JSON required fields → **A: Flat mock schema**
- FR-A05 rewritten: flat schema `{id, subject, from, to, body, received_at, thread_id}`;
  `_parse_message()` normalisation helper specified (detects real vs mock via `payload` key)
- FR-J03 updated: explicit flat schema documented
- Section 5 mock file description updated

## Outcome

- ✅ Impact: 3 critical implementation blockers resolved. Queue drain behavior makes
  rate-limiting recoverable without human intervention. LinkedIn Playwright target page and
  field extraction gives implementors a concrete starting point. Gmail flat mock schema enables
  test fixture authoring without knowledge of the real Gmail API structure.
- 🧪 Tests: No new tests (clarification session). 416 tests remain green.
- 📁 Files: specs/002-silver-tier/spec.md (13 edits: Q1×3, Q2×3, Q3×4, stale refs×6, session bullets×3)
- 🔁 Next prompts: `/sp.plan` to generate specs/002-silver-tier/plan.md — spec now implementation-ready
- 🧠 Reflection: Stale terminology references accumulate silently across clarification sessions.
  The browser-mcp → Playwright rename was made 3 sessions ago but 6 references survived in
  non-FR sections (risks, project structure, success criteria, config comments). Future sessions
  should run a grep sweep for deprecated terms before presenting questions.

## Evaluation notes (flywheel)

- Failure modes observed: None; all 3 questions answered on first attempt
- Graders run and results (PASS/FAIL): Manual — grep "browser-mcp" in spec shows 0 remaining;
  FR-D06 added; FR-C01 has target URL; FR-A05 has explicit JSON schema
- Prompt variant (if applicable): Fourth /sp.clarify session in same feature sprint
- Next experiment: Run automated grep sweep for deprecated terms at start of each clarification
  session (before questions) to catch stale refs systematically
