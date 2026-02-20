---
id: "0001"
title: Silver Tier Spec Writing
stage: spec
date: 2026-02-20
surface: agent
model: claude-sonnet-4-6
feature: 002-silver-tier
branch: 001-bronze-tier
user: USER-PC
command: "only write spec [Silver Tier requirements provided]"
labels: ["spec", "silver-tier", "watchers", "gmail", "whatsapp", "linkedin", "oauth2", "quickstart"]
links:
  spec: specs/002-silver-tier/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - specs/002-silver-tier/spec.md
  - specs/002-silver-tier/quickstart.md
  - history/prompts/002-silver-tier/0001-silver-tier-spec-writing.spec.prompt.md
tests:
  - "No new tests (spec-only deliverable; 385 Bronze tests remain green)"
---

## Prompt

[Silver Tier requirements provided by user — paraphrased from multi-message context]

User provided the following Silver Tier requirements and said "only write spec":

- Gmail watcher (OAuth2, reads unread emails, dry-run mock, token refresh, state file)
- WhatsApp watcher (Twilio REST, polling, dry-run mock, no media download)
- LinkedIn watcher (read engagement via browser-mcp) + LinkedIn post generator skill
- Real email sending via email-mcp (gated on dev_mode: false, opt-out list, idempotency)
- detect_lead skill (keyword scoring, CRITICAL priority, lead plan template)
- generate_plan skill (Claude API reasoning loop, fallback to Bronze templates)
- generate_linkedin_post skill (Claude draft, HIGH HITL gate, #AIAssisted tag, rate limit)
- weekly_briefing skill (vault/Logs aggregation → vault/Briefings/BRIEFING_<date>.md)
- install_schedule.py (Windows Task Scheduler + crontab, idempotent, uninstall)
- 3 new PLAN_TEMPLATES entries (lead, linkedin_post, social_media_engagement)
- Quarantine policy: fail×3 → vault/Quarantine/
- scan_interval: 30 → 120s (Constitution S4.2 Silver Layer 2)
- approval.expiry_hours: 24 → 48h (Constitution S7.2)
- Dry-run / mock mode for all new watchers
- New core modules: idempotency.py, rate_limiter.py, opt_out.py

User interrupted the first attempt and then said "resume" — continued with plan mode exploration, then wrote the spec.

## Response snapshot

Created two deliverables:

**`specs/002-silver-tier/spec.md`** (~500 lines):
- 15 User Stories (US-01 through US-15) covering all 8 Silver requirements
- 10 Functional Requirement groups (FR-A through FR-J, 25+ individual requirements):
  - FR-A: GmailWatcher (OAuth2, dry-run mock, token refresh, state file)
  - FR-B: WhatsAppWatcher (Twilio REST, dry-run mock, media noted not downloaded)
  - FR-C: LinkedIn watcher (browser-mcp) + post generator skill
  - FR-D: email-mcp real send wiring (gated on dev_mode, opt-out, AI footer, idempotency)
  - FR-E: detect_lead skill (keyword scoring, CRITICAL priority, lead plan template)
  - FR-F: generate_linkedin_post skill (Claude draft, HIGH HITL, #AIAssisted tag, rate limit)
  - FR-G: weekly_briefing skill (vault/Logs → vault/Briefings/BRIEFING_<date>.md)
  - FR-H: install_schedule.py (Windows + crontab, idempotent, uninstall)
  - FR-I: 3 new PLAN_TEMPLATES entries (lead, linkedin_post, social_media_engagement)
  - FR-J: dry-run/mock mode + quarantine policy (fail×3 → vault/Quarantine/)
- System architecture ASCII data flow diagram + HITL gate detail + idempotency key flow
- New components map: 27 new files, 8 files to modify (additive only)
- Skill interface contracts: run() signatures for all 5 new skills + 3 new core modules
- Config changes: settings.yaml, .env.example, requirements.txt additions
- Vault changes: 5 new folders, 5 new state/template files
- 11 Success Criteria: SC-010 through SC-020 (each independently verifiable)
- Out of Scope section (Odoo, Slack, encryption, Ralph loop, etc.)
- 3 Risks + Mitigations (OAuth complexity, LinkedIn fragility, Claude latency)
- Silver-additions-only project structure file tree
- Constitution traceability table

**`specs/002-silver-tier/quickstart.md`**:
- OAuth2 setup walkthrough (Gmail, Twilio, browser-mcp)
- Step-by-step first-run instructions
- Dev mode vs production mode table
- Troubleshooting table
- SC-010–SC-020 verification checklist

Key design decisions grounded in actual Bronze code:
- `generate_plan.py` wraps `plan_task.py` (Bronze templates preserved, 385 tests stay green)
- `scan_interval` 30 → 120s (Constitution S4.2 Silver Layer 2)
- `approval.expiry_hours` 24 → 48h (Constitution S7.2)
- Gmail: `message_id` as dedup key (matches `_make_item_id()` pattern in `base_watcher.py`)
- WhatsApp: Twilio REST (not Meta Cloud API) — simpler auth, no public webhook URL needed
- LinkedIn: `browser-mcp` (official API too restricted for personal use)
- `PLAN_TEMPLATES` extended in `plan_task.py` (additive dict entries, no existing template modified)
- Real email gated strictly on `dev_mode: false` (safety first; default stays `true`)
- New core modules: `idempotency.py`, `rate_limiter.py`, `opt_out.py` (single-responsibility, reusable)

## Outcome

- ✅ Impact: Full Silver Tier specification written. All 8 Silver requirements covered by ≥1 FR and ≥1 SC. No {{PLACEHOLDER}} or [TODO] remaining. FR labels unique (FR-A01 through FR-J05). SC labels continue from Bronze (SC-010 through SC-020). Spec follows same markdown structure as `specs/001-bronze-tier/spec.md`.
- 🧪 Tests: No new tests (spec-only deliverable). 385 Bronze tests remain green.
- 📁 Files: specs/002-silver-tier/spec.md (created), specs/002-silver-tier/quickstart.md (created)
- 🔁 Next prompts: `/sp.plan` to create `specs/002-silver-tier/plan.md`, then `/sp.tasks` for task list, then Red phase (failing tests), then Green phase (implementation)
- 🧠 Reflection: Explored Bronze codebase deeply before writing spec — this grounded decisions in actual code (base_watcher patterns, plan_task.py PLAN_TEMPLATES dict, email-mcp already configured in settings.local.json). Plan agent's codebase exploration was essential for avoiding invented APIs.

## Evaluation notes (flywheel)

- Failure modes observed: User interrupted the first spec attempt mid-stream; resumed successfully via plan mode
- Graders run and results (PASS/FAIL): Manual structural check — grep patterns show correct FR/SC counts
- Prompt variant (if applicable): Two-phase: plan mode exploration → write mode implementation
- Next experiment: Add automated spec linter that validates FR/SC label uniqueness and no placeholder text
