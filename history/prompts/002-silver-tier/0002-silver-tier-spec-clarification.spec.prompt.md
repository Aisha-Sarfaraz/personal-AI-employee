---
id: "0002"
title: Silver Tier Spec Clarification
stage: spec
date: 2026-02-20
surface: agent
model: claude-sonnet-4-6
feature: 002-silver-tier
branch: 001-bronze-tier
user: USER-PC
command: "/sp.clarify"
labels: ["clarification", "silver-tier", "email-mcp", "gmail-oauth", "opt-out", "weekly-briefing", "linkedin-auth"]
links:
  spec: specs/002-silver-tier/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - specs/002-silver-tier/spec.md
tests:
  - "No new tests (clarification-only session)"
---

## Prompt

/sp.clarify

User invoked clarification workflow on `specs/002-silver-tier/spec.md`.

## Response snapshot

Ran structured ambiguity scan across 11 taxonomy categories. Found 2 Missing and 3 Partial
categories warranting questions. Asked 5 questions sequentially; all answered.

**Questions asked and answers received:**

1. **email-mcp call pattern from Python** → B: MCP Python SDK (`mcp` client library connects
   to `npx @anthropic/email-mcp` server and calls `send_email` tool programmatically).
   Updated: FR-D01 now specifies MCP SDK pattern explicitly.

2. **Gmail credential storage** → B: Token file (`vault/.gmail_token.json`) written by
   `gmail_auth.py`; `GmailWatcher` uses `google.oauth2.credentials.Credentials.from_authorized_user_file()`.
   Updated: FR-A01, FR-A07; removed `GMAIL_REFRESH_TOKEN` from `.env.example`.

3. **Opt_Out_List.md format** → B: Markdown list (`- email@example.com` per line; headings/blanks skipped).
   Updated: `opt_out.py` interface contract docstring; vault file description in Section 8.

4. **weekly_briefing trigger mechanism** → A: Orchestrator time-guard — orchestrator calls
   `weekly_briefing.run()` every scan cycle; skill self-guards on Monday + file-existence check.
   Updated: FR-G01 (added self-guard spec); `weekly_briefing` interface contract docstring.

5. **LinkedIn credential storage** → B: Session cookie file — persisted browser-mcp session
   at `vault/state/linkedin_session/` (gitignored). No password in `.env`.
   Updated: FR-C01; removed `LINKEDIN_EMAIL`/`LINKEDIN_PASSWORD` from `.env.example`; added
   `linkedin_session/` to vault state file table.

**Spec `## Clarifications / ### Session 2026-02-20` section** created with 5 bullet Q→A entries.

## Outcome

- ✅ Impact: All 5 ambiguities resolved and written into spec. No contradictions remain.
  FR-D01, FR-A01, FR-A07, FR-C01, FR-G01 updated. `.env.example` corrected.
- 🧪 Tests: No new tests (clarification session). 385 Bronze tests unaffected.
- 📁 Files: specs/002-silver-tier/spec.md (updated in 9 edits)
- 🔁 Next prompts: `/sp.plan` to generate `specs/002-silver-tier/plan.md`
- 🧠 Reflection: The Gmail token file vs env-var contradiction was a genuine spec bug that
  would have caused an implementation defect. The LinkedIn password-in-env issue was a security
  risk caught before implementation. Both are high-value catches from this workflow.

## Evaluation notes (flywheel)

- Failure modes observed: None — all 5 questions answered cleanly in one shot each
- Graders run and results (PASS/FAIL): Manual review — all 5 spec edits are non-contradictory
- Prompt variant (if applicable): Standard /sp.clarify flow
- Next experiment: Add automated check that scans spec for `GMAIL_REFRESH_TOKEN` references after clarification
