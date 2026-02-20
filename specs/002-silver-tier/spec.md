# Silver Tier Specification: AI Business Assistant Upgrade

**Version:** 1.0.0
**Date:** 2026-02-20
**Status:** Draft
**Tier:** SILVER (builds on Bronze Foundation)
**Branch:** 002-silver-tier
**Constitution Reference:** `.specify/memory/constitution.md`
**Predecessor:** `specs/001-bronze-tier/spec.md` (385 passing tests, SC-001–SC-009 verified)

---

## Context

Silver Tier upgrades the Bronze personal AI employee from a single-source file-drop system into a
multi-channel autonomous business assistant. Where Bronze proved the pipeline (file → triage →
plan → HITL → done), Silver activates real perception (Gmail + WhatsApp), real execution
(email-mcp for outbound sends), AI-generated reasoning traces (Claude-authored Plan.md files),
outbound LinkedIn sales posts via browser automation, and scheduled periodic operations.

All Bronze infrastructure is preserved unchanged. Silver adds new files; it does not replace or
refactor existing Bronze code except where explicitly required to wire new capabilities.

**Architecture layers (Silver additions highlighted):**

```
External Sources (Gmail, WhatsApp, filesystem)
  → Perception Layer    (GmailWatcher [NEW] + WhatsAppWatcher [NEW] + FilesystemWatcher)
  → Obsidian Vault      (+ Briefings/ + Quarantine/ + Templates/ [NEW])
  → Reasoning Layer     (generate_plan [NEW] + detect_lead [NEW] + existing skills)
  → Action Layer        (email-mcp real sends [NEW] + browser-mcp LinkedIn [NEW])
  → Orchestration Layer (Task Scheduler / cron scheduling [NEW])
```

---

## Clarifications

| Question | Decision | Rationale |
|----------|----------|-----------|
| Which WhatsApp API? | Twilio WhatsApp REST (polling) | No public webhook URL needed; mock fallback when creds absent |
| LinkedIn post how? | `browser-mcp` (Playwright) | Official LinkedIn API too restricted for personal/small-business |
| "Claude reasoning loop" means? | New `generate_plan.py` skill calls Claude API | Falls back to Bronze PLAN_TEMPLATES when `dev_mode: true` or no API key |
| Scheduling on Windows? | `schtasks.exe` on Windows, crontab on Linux/Mac | Idempotent; uninstall script included |
| Gmail watcher dedup key? | `message_id` from Gmail API | Matches `_make_item_id()` pattern in BaseWatcher |
| Test without real credentials? | Dry-run reads from `vault/Watch/gmail_mock/` and `whatsapp_mock/` | Full pipeline works without any live API calls |

### Session 2026-02-20

- Q: How does Python action_executor call email-mcp at runtime? → A: MCP Python SDK (`mcp` client library connects to the `npx @anthropic/email-mcp` server process and calls its `send_email` tool programmatically; not subprocess or HTTP).
- Q: Gmail credential storage — env var GMAIL_REFRESH_TOKEN or token file? → A: Token file (`vault/.gmail_token.json`) written by `gmail_auth.py` OAuth2 flow; `GmailWatcher` reads it via `google.oauth2.credentials.Credentials` with automatic token refresh. Remove `GMAIL_REFRESH_TOKEN` from `.env.example`.
- Q: What is the exact format of `vault/Opt_Out_List.md`? → A: Markdown list — one `- email@example.com` entry per line; headings and blank lines are skipped by the parser.
- Q: Does the orchestrator call weekly_briefing, or is it OS-scheduler-only? → A: Orchestrator time-guard — orchestrator calls `weekly_briefing.run()` every scan cycle; the skill self-guards by checking (a) current day is Monday and (b) `vault/Briefings/BRIEFING_<this-monday>.md` does not yet exist. Returns `{skipped: true}` immediately if either condition fails.
- Q: LinkedIn credential storage — plaintext password in .env or session cookie file? → A: Session cookie file — one-time manual browser-mcp login; session persisted to `vault/state/linkedin_session/` (gitignored). No `LINKEDIN_EMAIL` or `LINKEDIN_PASSWORD` in `.env`.

---

## 1. Feature Overview

Silver Tier adds eight capabilities on top of the unchanged Bronze foundation:

1. **Multi-channel perception** — Gmail (OAuth2) and WhatsApp (Twilio) watchers run concurrently
   alongside the existing filesystem watcher. A new LinkedIn watcher reads engagement metrics.

2. **Real email sends** — `email-mcp` (`npx @anthropic/email-mcp`) replaces simulated email sends
   when `dev_mode: false` and Gmail credentials are present.

3. **LinkedIn sales posts** — `generate_linkedin_post` skill drafts posts using Claude, requires
   HIGH HITL approval, then publishes via `browser-mcp`. All posts include `#AIAssisted`.

4. **Claude reasoning loop** — `generate_plan.py` skill calls Claude API to write Plan.md files
   with intent summary, step rationale, and a `## Reasoning` trace. Falls back to Bronze
   PLAN_TEMPLATES when `dev_mode: true` or `ANTHROPIC_API_KEY` is absent.

5. **Lead detection** — `detect_lead.py` skill scores incoming items for buying signals. Items
   scoring ≥ 2 are upgraded to `type: lead`, `priority: CRITICAL`, and routed to the lead
   plan template which includes a `send_email` response step.

6. **Weekly CEO briefing** — `weekly_briefing.py` skill aggregates vault audit logs into a
   `vault/Briefings/BRIEFING_<date>.md` covering items by channel, leads, emails sent, LinkedIn
   posts, approvals, quarantined items, and next-week recommendations.

7. **OS-level scheduling** — `install_schedule.py` registers the orchestrator at system startup
   and the weekly briefing at Monday 08:00 via Windows Task Scheduler or crontab. Idempotent.

8. **Safety infrastructure** — Idempotency keys prevent duplicate external sends. Rate limiting
   caps emails at 20/hour and social posts at 10/hour. Quarantine isolates items that fail 3+
   times. Opt-out list enforced before every outbound email. AI disclosure footer on all emails.

### What Bronze Stays Exactly the Same

- `src/core/` — vault.py, frontmatter.py, approval.py, audit_logger.py: **unchanged**
- `src/skills/triage_inbox.py`, `check_handbook.py`, `execute_plan.py`, `update_dashboard.py`: **unchanged**
- `src/watchers/filesystem_watcher.py`, `base_watcher.py`: extended minimally (dry_run property)
- `config/settings.yaml`: extended with new stanzas; existing keys unchanged
- All 385 Bronze tests must continue to pass

---

## 2. User Stories

### US-01 — Gmail Inbox Monitoring
As a business owner, I want incoming Gmail messages to be automatically detected and triaged, so
I can respond to client enquiries without manually checking email.

**Acceptance**: A new email in Gmail matching the configured query appears as an item in
`vault/Inbox/` within 2 minutes of arrival.

---

### US-02 — WhatsApp Message Capture
As a business owner, I want WhatsApp messages sent to my business number to appear in the vault
inbox, so I have a unified view of all inbound communications.

**Acceptance**: A WhatsApp message to the Twilio number creates an Inbox item within 2 minutes
(real mode) or immediately in mock mode.

---

### US-03 — Real Email Sends via email-mcp
As a business owner, I want approved email responses to actually be sent via Gmail (not just
simulated), so I can trust the system is doing real work.

**Acceptance**: When `dev_mode: false` and Gmail credentials are set, approving an email send
step results in the email appearing in Gmail Sent folder. Audit log records `simulated: false`.

---

### US-04 — Lead Detection
As a sales-focused business owner, I want the system to automatically flag emails and WhatsApp
messages containing buying signals, so I never miss a lead.

**Acceptance**: An email containing "I'm interested in your pricing" is classified `type: lead`,
`priority: CRITICAL`, with `lead_score >= 2`.

---

### US-05 — LinkedIn Post Generation and Publishing
As a business owner, I want the system to draft LinkedIn posts designed to generate sales leads,
require my approval, then publish them automatically.

**Acceptance**: A LinkedIn post draft is created in `vault/Plans/LINKEDIN_POST_*.md`. After
approval, browser-mcp publishes the post. Audit entry records `simulated: false` (real mode).

---

### US-06 — Claude-Powered Plan Generation
As a user reviewing plans in Obsidian, I want plan files to contain AI-reasoned steps with
rationale, not hardcoded templates, so I can trust and understand the system's intentions.

**Acceptance**: When `dev_mode: false` and `ANTHROPIC_API_KEY` is set, Plan.md files contain a
`## Reasoning` section written by Claude. In DEV_MODE, plans are generated from templates without
error.

---

### US-07 — Weekly CEO Briefing
As a business owner, I want a weekly summary of everything the system did, pending items, leads
detected, and emails sent, so I can review the week in 5 minutes.

**Acceptance**: Every Monday at 08:00, `vault/Briefings/BRIEFING_<YYYY-MM-DD>.md` is created
with all required sections.

---

### US-08 — Scheduling Setup
As a system administrator, I want the orchestrator to start automatically and schedule recurring
jobs, so the system runs without manual intervention.

**Acceptance**: Running `python src/skills/install_schedule.py` registers the required tasks.
Running it again produces no duplicates (idempotent).

---

### US-09 — Quarantine Safety Net
As a business owner, I want items that repeatedly fail processing to be safely isolated, so they
do not block the pipeline or cause infinite retries.

**Acceptance**: An item that fails processing 3 times is in `vault/Quarantine/` with a MEDIUM
audit entry. Dashboard.md shows the quarantine count.

---

### US-10 — Enhanced Dashboard with New Channels
As a business owner, I want Dashboard.md to show the status of all three watchers and the lead
pipeline, so I have a real-time system view.

**Acceptance**: Dashboard.md shows watcher health rows for `gmail_watcher`, `whatsapp_watcher`,
`filesystem_watcher`, leads-detected count, and briefings-generated count.

---

### US-11 — Dry-Run Mode for New Watchers
As a developer, I want to run the full system without live credentials, so I can test end-to-end
before connecting real accounts.

**Acceptance**: With credentials absent or `DRY_RUN=true`, watchers read from mock folders.
All downstream processing is identical to live mode.

---

### US-12 — Idempotency Keys for External Actions
As a system administrator, I want every external API call to carry an idempotency key, so
retrying after a timeout never sends a duplicate email or publishes a duplicate post.

**Acceptance**: `vault/state/idempotency_keys.json` exists after first run. Retrying an already-
completed action returns the cached result without re-calling the MCP server.

---

### US-13 — Opt-Out List Enforcement
As an ethical operator, I want outbound emails to skip opted-out contacts, so the system
respects preferences and avoids spam.

**Acceptance**: An address in `vault/Opt_Out_List.md` is blocked from receiving any AI-sent
email. A `skipped: opted_out` audit entry is logged.

---

### US-14 — AI Disclosure Footer
As an ethical operator, I want all AI-drafted emails to include a disclosure footer, so
recipients know the message was AI-assisted.

**Acceptance**: Every email sent via the system includes the footer: "This message was drafted
with AI assistance."

---

### US-15 — Rate Limiting on External Actions
As a system operator, I want the system to respect rate limits, so I do not hit API quotas or
appear as spam.

**Acceptance**: Email sends are capped at 20/hour; social media posts at 10/hour. When the
limit is reached, the action is queued in `vault/state/queue.json` and a MEDIUM audit entry is
written.

---

## 3. Functional Requirements

### FR-A: Gmail Watcher

**FR-A01**: `src/watchers/gmail_watcher.py` MUST implement `check_for_updates()` using the Gmail
API (`google-api-python-client`) with OAuth2 credentials loaded from
`vault/.gmail_token.json` (written by `gmail_auth.py`). The token object is constructed via
`google.oauth2.credentials.Credentials.from_authorized_user_file()`. Only `GMAIL_CLIENT_ID`
and `GMAIL_CLIENT_SECRET` are read from `.env` (needed for refresh); `GMAIL_REFRESH_TOKEN`
env var is NOT used.

**FR-A02**: The watcher MUST poll the inbox at the configured `poll_interval` (default: 120s)
using `messages.list` with configurable query filter (default: `is:unread label:inbox`).

**FR-A03**: Each Gmail message MUST be converted to an item dict with keys:
`id` (= message_id), `source: gmail`, `subject`, `from_address`, `to_address`, `message_id`,
`received_at`, `thread_id`, `body` (plain text of email), `type` (set by triage), `priority`,
`filename` (= `GMAIL_<message_id>.md`), `tags: []`.

**FR-A04**: After creating the Inbox item, the watcher MUST mark the message as read in Gmail
(`messages.modify` — remove `UNREAD` label). This is a LOW-risk auto-approved operation.

**FR-A05**: When `GMAIL_CLIENT_ID` is absent or `DRY_RUN=true`, the watcher MUST read mock
messages from `vault/Watch/gmail_mock/*.json` (schema matching Gmail API `messages.get` response)
and behave identically to live mode for all downstream processing.

**FR-A06**: OAuth token refresh MUST be handled automatically. Refresh failures MUST produce a
MEDIUM audit entry and pause the watcher (not crash the orchestrator).

**FR-A07**: Watcher state `vault/state/gmail_watcher_state.json` MUST persist processed message
IDs and last successful poll timestamp. Token expiry is managed by `vault/.gmail_token.json`
(written by `google-auth`); the state file does NOT duplicate token data.

**FR-A08**: The watcher MUST NOT make more than 100 Gmail API calls per hour.

---

### FR-B: WhatsApp Watcher

**FR-B01**: `src/watchers/whatsapp_watcher.py` MUST implement `check_for_updates()` using the
Twilio Messages REST API. Required env vars: `WHATSAPP_TWILIO_ACCOUNT_SID`,
`WHATSAPP_TWILIO_AUTH_TOKEN`, `WHATSAPP_FROM_NUMBER`.

**FR-B02**: The watcher MUST poll Twilio for inbound messages to the configured number at
`poll_interval` (default: 120s), filtering `direction: inbound`.

**FR-B03**: Each WhatsApp message MUST be converted to an item dict with keys:
`id` (= message_sid), `source: whatsapp`, `from_number`, `to_number`, `message_sid`,
`body` (message text), `received_at`, `num_media`, `filename` (= `WA_<message_sid>.md`),
`type`, `priority`, `tags: []`.

**FR-B04**: When `WHATSAPP_TWILIO_ACCOUNT_SID` is absent or `DRY_RUN=true`, the watcher MUST
read mock messages from `vault/Watch/whatsapp_mock/*.json` (Twilio Messages API schema).

**FR-B05**: Media attachments MUST be noted (`has_media: true`) but NOT downloaded in Silver
tier. Body notes: "[Media attachment — see WhatsApp app]".

**FR-B06**: Watcher state `vault/state/whatsapp_watcher_state.json` MUST persist processed
message SIDs and last poll timestamp.

---

### FR-C: LinkedIn Watcher + Post Generator

**FR-C01**: `src/watchers/linkedin_watcher.py` MUST exist as a read-only watcher that reads
engagement data (reaction count, comment count) from recent posts via `browser-mcp`. LinkedIn
authentication uses a **persisted browser session** stored in `vault/state/linkedin_session/`
(gitignored, never committed). On first run (session absent), browser-mcp opens a browser
window for manual one-time login; the session is then persisted automatically. No LinkedIn
credentials are stored in `.env`. If `browser-mcp` is unavailable or session expired, the
watcher returns an empty list and logs a LOW audit entry with instructions to re-login.

**FR-C02**: LinkedIn watcher items MUST have `type: social_media_engagement`, `source: linkedin`,
`platform: linkedin`. These trigger the `social_media_engagement` plan template (FR-I).

**FR-C03**: `src/skills/generate_linkedin_post.py` MUST be an Agent Skill that:
- Reads `vault/Business_Goals.md` and recent vault activity (last 7 days from Logs/) as context.
- Calls Claude API (`ANTHROPIC_API_KEY`) to draft a post (max 3,000 chars, professional tone,
  value-first, no hard-sell, includes a CTA). Falls back to configurable template when
  `dev_mode: true` or API key absent.
- Writes the draft to `vault/Plans/LINKEDIN_POST_<timestamp>.md` with `type: linkedin_post`,
  `risk_level: HIGH`, `requires_approval: true`.
- The plan includes a `post_social` step tagged `platform: linkedin` executed via `action_executor`.

**FR-C04**: Publishing a LinkedIn post via `browser-mcp` MUST be a HIGH-risk action requiring
explicit HITL approval. The approval file MUST include the full post text for human review.

**FR-C05**: All LinkedIn posts MUST include `#AIAssisted` per constitution S13.3.

**FR-C06**: LinkedIn post frequency MUST NOT exceed 5 posts per day (rate_limiter enforcement).

---

### FR-D: Email MCP Integration (Real Sends)

**FR-D01**: `src/actions/action_executor.py` MUST be extended with a real `_send_email` handler
that calls `email-mcp` via the **MCP Python SDK** (`mcp` client library) — connecting to the
`npx @anthropic/email-mcp` server process and invoking its `send_email` tool programmatically
(not via subprocess or HTTP) — when `dev_mode: false`. The handler MUST:
- Append the AI disclosure footer: "This message was drafted with AI assistance."
- Check `vault/Opt_Out_List.md`; skip + log `skipped: opted_out` if recipient is listed.
- Check rate limiter (max 20 emails/hour).
- Generate and check an idempotency key before calling email-mcp.
- Return `{success, action_type, details, simulated: false, message_id}`.

**FR-D02**: When `dev_mode: true` (default), `_send_email` MUST simulate exactly as Bronze,
returning `simulated: true` without calling email-mcp.

**FR-D03**: `DRY_RUN=true` in environment MUST force simulation across ALL external actions
regardless of `dev_mode` setting.

**FR-D04**: All Gmail credentials MUST be loaded from `.env` only — never from vault files.

**FR-D05**: Email send failures MUST retry with exponential backoff (1s, 2s, 4s — 3 attempts).
After 3 failures: log `failure`, increment item `fail_count`, move to Quarantine if `fail_count >= 3`.

---

### FR-E: Lead Detection Skill

**FR-E01**: `src/skills/detect_lead.py` MUST be an Agent Skill that scans `vault/Needs_Action/`
for items with `type` NOT already `lead`, checking for ≥ 2 keyword matches.

**FR-E02**: Default lead keywords (configurable in `settings.yaml` under `skills.detect_lead.keywords`):
`pricing`, `quote`, `proposal`, `interested`, `buy`, `purchase`, `contract`, `hire`, `rates`,
`availability`, `demo`, `trial`, `interested in`.

**FR-E03**: When a lead is detected, the skill MUST update frontmatter in-place:
`type: lead`, `priority: CRITICAL`, `lead_score: <int 0-10>`. Log a HIGH audit entry.

**FR-E04**: Lead score: 1 point per keyword match (capped at 10), +2 if `source: gmail`, +1 if
already `priority: CRITICAL`.

**FR-E05**: `run()` MUST return `{processed, leads_detected, errors, skipped}`.

---

### FR-F: LinkedIn Post Generation Skill

**FR-F01**: `src/skills/generate_linkedin_post.py` MUST implement `run(vault_root) -> dict`
returning `{processed, post_files_created, skipped_rate_limit, errors, skipped}`.

**FR-F02**: The Claude prompt MUST be loaded from `vault/Templates/linkedin_post_prompt.md` if
the file exists; otherwise a hardcoded default prompt is used. The template file is editable
without code changes.

**FR-F03**: Post generation is triggered by the orchestrator only when:
- `skills.generate_linkedin_post.enabled: true` in settings.yaml, AND
- The number of posts in the last `frequency_days` (default: 3) days is below the daily limit.
- The skill is NOT called on every scan cycle — it self-throttles via rate_limiter.

---

### FR-G: Weekly CEO Briefing Skill

**FR-G01**: `src/skills/weekly_briefing.py` MUST implement `run(vault_root) -> dict` returning
`{processed, briefing_file, week_start, errors, skipped}`.

The skill MUST self-guard: on entry, check (a) `datetime.now().weekday() == 0` (Monday) and
(b) `vault/Briefings/BRIEFING_<this-monday-date>.md` does not exist. If either condition
fails, return `{processed: 0, briefing_file: None, week_start: None, errors: [], skipped: 1}`
immediately without reading logs. The orchestrator scan cycle calls `weekly_briefing.run()`
on every cycle — the skill itself decides whether to act.

**FR-G02**: The briefing MUST include all of these sections:
- Date range covered (previous Monday–Sunday)
- Items processed by channel (gmail, whatsapp, filesystem) — sourced from audit logs
- Leads detected: count, top 3 by score, pending vs responded
- Emails sent (real and simulated, flagged separately)
- LinkedIn posts published (with engagement delta if available)
- Plans in progress / completed / rejected counts
- Approvals: resolved / expired / pending counts
- Quarantine: count and failure reasons
- Next week recommended actions (Claude-drafted if API key present, else template text)

**FR-G03**: Output: `vault/Briefings/BRIEFING_<YYYY-MM-DD>.md` (Monday date of reported week).

**FR-G04**: The skill MUST read audit logs from `vault/Logs/` only. It MUST NOT reprocess vault
items. It is LOW-risk (no HITL required).

**FR-G05**: `vault/Briefings/` MUST be created by `orchestrator._ensure_vault_structure()` on
startup (added to vault folder list in settings.yaml).

---

### FR-H: Scheduling

**FR-H01**: `src/skills/install_schedule.py` MUST detect platform and register:
- **Windows**: `schtasks.exe` task `FTE-Orchestrator` (run at startup) + `FTE-WeeklyBriefing`
  (every Monday 08:00).
- **Linux/Mac**: crontab entries tagged `# FTE` — `@reboot` for orchestrator, `0 8 * * 1` for
  briefing.

**FR-H02**: Running the script MUST be idempotent — existing entries are updated, not duplicated.

**FR-H03**: `src/skills/uninstall_schedule.py` MUST remove all registered FTE tasks/entries.

**FR-H04**: The script MUST print a confirmation and write a LOW audit entry on completion.

**FR-H05**: Default `scan_interval` MUST change from 30s (Bronze) to 120s (Silver) in the updated
`config/settings.yaml`.

---

### FR-I: Enhanced Plan Templates

**FR-I01**: `src/skills/plan_task.py` `PLAN_TEMPLATES` dict MUST be extended with three new
entries (additive — no existing template modified):

**`lead`**:
```python
[
  {"step_number": 1, "action_type": "file_operation",  "description": "Review lead context and score",                "risk_level": "LOW",  "requires_approval": False, "status": "pending"},
  {"step_number": 2, "action_type": "file_operation",  "description": "Draft personalised response using business goals", "risk_level": "LOW",  "requires_approval": False, "status": "pending"},
  {"step_number": 3, "action_type": "send_email",      "description": "Send lead response email",                     "risk_level": "HIGH", "requires_approval": True,  "status": "pending"},
  {"step_number": 4, "action_type": "file_operation",  "description": "Tag lead as contacted in vault",               "risk_level": "LOW",  "requires_approval": False, "status": "pending"},
]
```

**`linkedin_post`**:
```python
[
  {"step_number": 1, "action_type": "file_operation", "description": "Review post draft and business goals alignment", "risk_level": "LOW",  "requires_approval": False, "status": "pending"},
  {"step_number": 2, "action_type": "post_social",    "description": "Publish LinkedIn post via browser-mcp",         "risk_level": "HIGH", "requires_approval": True,  "status": "pending"},
  {"step_number": 3, "action_type": "file_operation", "description": "Record post in engagement tracker",             "risk_level": "LOW",  "requires_approval": False, "status": "pending"},
]
```

**`social_media_engagement`**:
```python
[
  {"step_number": 1, "action_type": "file_operation", "description": "Summarise engagement metrics",          "risk_level": "LOW", "requires_approval": False, "status": "pending"},
  {"step_number": 2, "action_type": "file_operation", "description": "Update engagement tracker in vault",    "risk_level": "LOW", "requires_approval": False, "status": "pending"},
]
```

**FR-I02**: `src/skills/generate_plan.py` MUST wrap `plan_task` with Claude enrichment:
- Call `plan_task._generate_steps(item_type, metadata)` to get base steps.
- If `ANTHROPIC_API_KEY` set and `dev_mode: false`: call Claude to prepend `## Reasoning` section.
- Otherwise: write plan exactly as `plan_task.run()` does.
- Write `PLAN_*.md` using identical naming convention to `plan_task.py`.
- MUST NOT duplicate plans for already-planned items.
- Recommended Claude model: `claude-haiku-4-5` (speed + cost; configurable via
  `ANTHROPIC_PLAN_MODEL` env var).

**FR-I03**: The orchestrator scan cycle MUST call `generate_plan.run()` instead of
`plan_task.run()`. `plan_task.py` itself is unchanged and remains independently testable.

---

### FR-J: Safety, Dry-Run, and Quarantine

**FR-J01**: All new watchers MUST support dry-run mode (credentials absent OR `DRY_RUN=true`).
In dry-run mode, watchers read from their mock folder and prefix audit entries with `[DRY_RUN]`.

**FR-J02**: `src/watchers/base_watcher.py` MUST be extended with:
- `dry_run: bool` property (default `False`)
- `_load_mock_items(mock_folder: str) -> list[dict]` helper that reads JSON files from
  `mock_folder`, parses each as an item dict, and returns the list.

**FR-J03**: Mock folder structure:
- `vault/Watch/gmail_mock/sample_email.json` — Gmail API `messages.get` response schema
- `vault/Watch/whatsapp_mock/sample_message.json` — Twilio Messages API response schema
- Both folders created by `orchestrator._ensure_vault_structure()`
- Sample files committed to the repo for out-of-box testing

**FR-J04**: Quarantine policy: `fail_count` is tracked in each item's frontmatter. On processing
failure, `execute_plan.py` increments `fail_count` in the item file. When `fail_count >= 3`, the
item is moved from `vault/Needs_Action/` to `vault/Quarantine/` and a MEDIUM audit entry is
written. Quarantine moves are agent-irreversible — only human action can rescue items.

**FR-J05**: Dashboard.md MUST show the `Quarantine` folder count.

---

## 4. System Architecture

### Data Flow: Perception → Reasoning → Action

```
┌──────────────────────────────────────────────────────────────┐
│  PERCEPTION LAYER (3 concurrent watcher daemon threads)      │
│                                                              │
│  GmailWatcher ─────────────────────────────────────────────┐ │
│  (google-api-python-client, OAuth2)  poll: 120s             │ │
│                                                             │ │
│  WhatsAppWatcher ──────────────────────────────────────────┼─┤→ vault/Inbox/
│  (Twilio REST API)                   poll: 120s             │ │  ITEM_*.md
│                                                             │ │
│  FilesystemWatcher ─────────────────────────────────────────┘ │
│  (watchdog, Bronze)                  poll: 5s                  │
└──────────────────────────────────────────────────────────────┘
                    │
                    ▼ (orchestrator scan cycle — 120s interval)
┌──────────────────────────────────────────────────────────────┐
│  REASONING LAYER (Agent Skills, sequential)                  │
│                                                              │
│  1. triage_inbox.run()    classify type + priority           │
│     detect_lead.run()     score lead signals           ──── │→ vault/Needs_Action/
│                                                              │
│  2. generate_plan.run()   Claude reasoning trace       ──── │→ vault/Plans/PLAN_*.md
│     (falls back to plan_task templates in DEV_MODE)          │
│                                                              │
│  3. execute_plan.run()    step execution + HITL gates  ──── │→ vault/Pending_Approval/
│                           ↓ (approved)                       │→ vault/Done/
│                    action_executor                           │→ vault/Quarantine/ (fail×3)
│                           │                                  │
│               ┌───────────┼──────────────┐                  │
│               ▼           ▼              ▼                  │
│          email-mcp   browser-mcp    file_operation           │
│          (send_email) (post_social) (vault writes)           │
│          REAL if       REAL if                               │
│          dev_mode=F    dev_mode=F                            │
│                                                              │
│  4. update_dashboard.run()  refresh Dashboard.md       ──── │
└──────────────────────────────────────────────────────────────┘
                    │
          (scheduled, not every cycle)
┌──────────────────────────────────────────────────────────────┐
│  SCHEDULED SKILLS                                            │
│                                                              │
│  generate_linkedin_post.run()  — every 3 days (configurable) │
│  weekly_briefing.run()         — every Monday 08:00          │
│  install_schedule.py           — run once, idempotent        │
└──────────────────────────────────────────────────────────────┘
```

### HITL Gate (unchanged from Bronze, extended for new action types)

```
Plan Step (HIGH or CRITICAL risk)
         │
         ▼
create_approval_request() → vault/Pending_Approval/APPROVAL_REQUIRED_<uuid>.md
         │                   (contains full action details + post text for LinkedIn)
         ▼ (next scan cycle)
check_approval_status()
  ├── approved  → execute_action(action_type, details)
  │               ├── send_email:  email-mcp (real) or simulate
  │               ├── post_social: browser-mcp (real) or simulate
  │               └── file_operation: vault write
  ├── rejected  → plan.status = rejected → Done/
  ├── expired   → re-queue (new approval_request)
  └── pending   → skip (try next cycle)
```

### Idempotency Key Flow (new in Silver)

```
execute_action(action_type, details)
         │
         ▼
generate_key(agent, action, details) → "send_email:hash:epoch_day"
         │
         ▼
check vault/state/idempotency_keys.json
  ├── key exists AND not expired → return cached result (no MCP call)
  └── key absent or expired
            │
            ▼
       call MCP server
            │
            ▼
       store key + result (TTL: 24h)
```

---

## 5. New Components Map

### New Files to Create

| File | Type | Description |
|------|------|-------------|
| `src/watchers/gmail_watcher.py` | Watcher | Gmail API OAuth2 polling — replaces Bronze stub |
| `src/watchers/whatsapp_watcher.py` | Watcher | Twilio WhatsApp REST — replaces Bronze stub |
| `src/watchers/linkedin_watcher.py` | Watcher | browser-mcp engagement reader |
| `src/skills/detect_lead.py` | Skill | Lead keyword scoring and flagging |
| `src/skills/generate_plan.py` | Skill | Claude-reasoning plan generator (wraps plan_task) |
| `src/skills/generate_linkedin_post.py` | Skill | Claude-drafted LinkedIn post generator |
| `src/skills/weekly_briefing.py` | Skill | Weekly CEO briefing aggregator |
| `src/skills/install_schedule.py` | Skill + Script | OS-level scheduler registration |
| `src/skills/uninstall_schedule.py` | Script | Remove scheduled FTE tasks |
| `src/core/idempotency.py` | Core | Idempotency key store (check / store / expire) |
| `src/core/rate_limiter.py` | Core | Per-action-type hourly counter |
| `src/core/opt_out.py` | Core | Opt-out list reader / checker |
| `vault/Briefings/.gitkeep` | Vault | New briefings folder |
| `vault/Quarantine/.gitkeep` | Vault | New quarantine folder |
| `vault/Templates/linkedin_post_prompt.md` | Vault | Editable Claude prompt for LinkedIn posts |
| `vault/Opt_Out_List.md` | Vault | Email opt-out list (initially empty) |
| `vault/Watch/gmail_mock/sample_email.json` | Mock | Sample Gmail API response for dry-run |
| `vault/Watch/whatsapp_mock/sample_message.json` | Mock | Sample Twilio response for dry-run |
| `tests/test_gmail_watcher.py` | Test | GmailWatcher unit tests |
| `tests/test_whatsapp_watcher.py` | Test | WhatsAppWatcher unit tests |
| `tests/test_linkedin_watcher.py` | Test | LinkedInWatcher unit tests |
| `tests/test_detect_lead.py` | Test | detect_lead skill unit tests |
| `tests/test_generate_plan.py` | Test | generate_plan skill unit tests |
| `tests/test_linkedin_post.py` | Test | generate_linkedin_post skill unit tests |
| `tests/test_weekly_briefing.py` | Test | weekly_briefing skill unit tests |
| `tests/test_idempotency.py` | Test | idempotency core unit tests |
| `tests/test_rate_limiter.py` | Test | rate_limiter core unit tests |
| `tests/test_opt_out.py` | Test | opt_out core unit tests |
| `tests/test_e2e_silver.py` | Test | End-to-end: mock email → lead → approved send |

### Files to Modify (additive only)

| File | Change Required |
|------|----------------|
| `src/orchestrator.py` | Register gmail/whatsapp/linkedin watchers in `_init_watchers()`; add `detect_lead`, `generate_plan` to `_scan_cycle()`; add new folders to vault structure init |
| `src/skills/plan_task.py` | Add `lead`, `linkedin_post`, `social_media_engagement` to `PLAN_TEMPLATES` dict |
| `src/skills/update_dashboard.py` | Add Quarantine + Briefings folder counts; per-watcher health rows for all 3 watchers |
| `src/actions/action_executor.py` | Wire real `send_email` via email-mcp; wire `post_social` via browser-mcp; add rate-limit, idempotency, opt-out, and AI disclosure footer |
| `src/watchers/base_watcher.py` | Add `dry_run` property and `_load_mock_items()` helper |
| `config/settings.yaml` | Add gmail/whatsapp/linkedin watcher configs; new skill configs; rate_limits; idempotency; new vault folders; scan_interval 30→120 |
| `requirements.txt` | Add: `google-auth`, `google-auth-oauthlib`, `google-api-python-client`, `requests`, `anthropic` |
| `.env.example` | Add Gmail, WhatsApp, Anthropic, LinkedIn, DRY_RUN env var keys |

---

## 6. Skill Interface Contracts

All Silver skills conform to the Bronze `run(vault_root: str) -> dict` contract from
`specs/001-bronze-tier/contracts/skill-interface.md`. Return dict extensions are additive.

### detect_lead
```python
def run(vault_root: str) -> dict[str, Any]:
    """Scan Needs_Action/ for lead signals. Upgrade matching items to type:lead."""
    # Returns: {processed, leads_detected, errors, skipped}
```
Reads: `vault/Needs_Action/`
Writes: `vault/Needs_Action/` (frontmatter update in-place), `vault/Logs/`

### generate_plan
```python
def run(vault_root: str) -> dict[str, Any]:
    """Generate Plan.md for unplanned items. Claude-enriched when API key present."""
    # Returns: {processed, claude_enriched, template_fallback, errors, skipped}
```
Reads: `vault/Needs_Action/`, `vault/Business_Goals.md`
Writes: `vault/Plans/`, `vault/Needs_Action/` (status update), `vault/Logs/`

### generate_linkedin_post
```python
def run(vault_root: str) -> dict[str, Any]:
    """Draft a LinkedIn post. Only if frequency threshold allows."""
    # Returns: {processed, post_files_created, skipped_rate_limit, errors, skipped}
```
Reads: `vault/Business_Goals.md`, `vault/Logs/` (7 days), `vault/Templates/linkedin_post_prompt.md`
Writes: `vault/Plans/LINKEDIN_POST_<timestamp>.md`, `vault/Logs/`

### weekly_briefing
```python
def run(vault_root: str) -> dict[str, Any]:
    """Aggregate audit logs into weekly CEO briefing.
    Self-guards: only executes on Monday when this week's briefing file does not yet exist.
    Called by orchestrator every scan cycle; skips silently when not due.
    Returns: {processed, briefing_file, week_start, errors, skipped}
    """
```
Reads: `vault/Logs/`, `vault/Needs_Action/`, `vault/Done/`, `vault/Quarantine/`
Writes: `vault/Briefings/BRIEFING_<date>.md`, `vault/Logs/`

### install_schedule
```python
def run(vault_root: str) -> dict[str, Any]:
    """Register OS-level scheduled tasks. Idempotent."""
    # Returns: {processed, platform, tasks_created, tasks_updated, errors, skipped}
```

### Core: idempotency.py
```python
def generate_key(agent: str, action: str, details: dict) -> str:
    """Format: "{agent}:{action}:{sha256_of_details[:8]}:{epoch_day}" """

def check_and_store(
    vault_root: str,
    key: str,
    result: dict | None = None,
    ttl_hours: int = 24,
) -> tuple[bool, dict | None]:
    """Returns (key_existed, cached_result). Stores result if key is new."""
```

### Core: rate_limiter.py
```python
def check_and_increment(vault_root: str, action_type: str, limit_per_hour: int) -> bool:
    """Returns True (allowed) or False (rate limited). Increments counter if allowed."""
```

### Core: opt_out.py
```python
def is_opted_out(vault_root: str, email_address: str) -> bool:
    """Case-insensitive check of vault/Opt_Out_List.md.
    Format: Markdown list — lines starting with '- ' contain one email address each.
    Headings (starting with '#') and blank lines are skipped.
    Example file content:
        # Opt-Out List
        - alice@example.com
        - bob@example.com
    """
```

---

## 7. Config Changes

### settings.yaml additions

```yaml
vault:
  folders:
    briefings: "Briefings"       # NEW
    quarantine: "Quarantine"     # NEW
    templates: "Templates"       # NEW
  mock_dirs:                     # NEW
    gmail: "Watch/gmail_mock"
    whatsapp: "Watch/whatsapp_mock"

watchers:
  gmail:
    enabled: false               # set true when credentials in .env
    poll_interval: 120
    query: "is:unread label:inbox"
    max_results: 10
  whatsapp:
    enabled: false               # set true when credentials in .env
    poll_interval: 120
    max_results: 10
  linkedin:
    enabled: false               # set true when browser-mcp available
    poll_interval: 3600

orchestrator:
  scan_interval: 120             # CHANGED: 30 → 120 (Silver Layer 2 requirement)

approval:
  expiry_hours: 48               # CHANGED: 24 → 48 (Silver constitution S7.2)

skills:
  detect_lead:
    enabled: true
    keywords:
      - "pricing"
      - "quote"
      - "proposal"
      - "interested"
      - "buy"
      - "purchase"
      - "contract"
      - "hire"
      - "rates"
      - "availability"
      - "demo"
      - "trial"
  generate_plan:
    enabled: true
    use_claude: true             # false = template fallback only
  generate_linkedin_post:
    enabled: true
    frequency_days: 3
    max_posts_per_day: 5
  weekly_briefing:
    enabled: true

rate_limits:
  send_email: 20                 # per hour
  post_social: 10                # per hour

idempotency:
  ttl_hours: 24
```

### .env.example additions

```bash
# Silver: Gmail (GmailWatcher + email-mcp)
# Token file at vault/.gmail_token.json is written by gmail_auth.py (one-time OAuth2 flow)
GMAIL_CLIENT_ID=your_client_id_here
GMAIL_CLIENT_SECRET=your_client_secret_here
# GMAIL_REFRESH_TOKEN — NOT used; refresh handled automatically by google-auth via token file

# Silver: WhatsApp (Twilio)
WHATSAPP_TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
WHATSAPP_TWILIO_AUTH_TOKEN=your_auth_token_here
WHATSAPP_FROM_NUMBER=whatsapp:+14155238886

# Silver: Claude API (generate_plan, generate_linkedin_post)
ANTHROPIC_API_KEY=sk-ant-xxxxxxxx
ANTHROPIC_PLAN_MODEL=claude-haiku-4-5

# Silver: LinkedIn (browser-mcp)
# No credentials in .env — LinkedIn uses a persisted browser session.
# On first run, browser-mcp opens a login window. Session saved to vault/state/linkedin_session/

# Silver: Force dry-run even when dev_mode=false
DRY_RUN=false
```

### requirements.txt additions

```
# Silver additions
google-auth>=2.0.0
google-auth-oauthlib>=1.0.0
google-api-python-client>=2.0.0
requests>=2.28.0
anthropic>=0.20.0
```

---

## 8. Vault Changes

### New Folders

| Folder | Purpose | Created By |
|--------|---------|-----------|
| `vault/Briefings/` | Weekly CEO briefing files | `orchestrator._ensure_vault_structure()` |
| `vault/Quarantine/` | Poison items (failed 3+ times) | `orchestrator._ensure_vault_structure()` |
| `vault/Templates/` | Editable prompt templates | `orchestrator._ensure_vault_structure()` |
| `vault/Watch/gmail_mock/` | Mock Gmail messages for dry-run | `orchestrator._ensure_vault_structure()` |
| `vault/Watch/whatsapp_mock/` | Mock WhatsApp messages for dry-run | `orchestrator._ensure_vault_structure()` |

### New Vault Files

| File | Purpose |
|------|---------|
| `vault/Opt_Out_List.md` | Markdown list (`- email@example.com` per line); checked before every outbound send |
| `vault/Templates/linkedin_post_prompt.md` | Editable Claude prompt for LinkedIn post drafting |
| `vault/state/idempotency_keys.json` | Key → result map with TTL (auto-created) |
| `vault/state/rate_limits.json` | Hourly action counters (auto-created) |
| `vault/state/queue.json` | Rate-limited action overflow queue (auto-created) |
| `vault/state/linkedin_session/` | Persisted browser-mcp session (gitignored; written on first LinkedIn login) |

### Updated Item State Machine

```
External event (email / WhatsApp / file drop)
  → vault/Inbox/               (watcher output)
  → vault/Needs_Action/        (after triage; lead flagging in-place)
  → vault/Plans/               (after generate_plan; Claude reasoning embedded)
  → vault/Pending_Approval/    (HIGH/CRITICAL step awaiting human)
  → vault/Approved/ or Rejected/ (human decision via checkbox)
  → vault/Done/                (completed or rejected — terminal)
  → vault/Quarantine/          (failed 3+ times — human rescue required)
  → vault/Briefings/           (weekly briefing output — read-only archive)
  → vault/Logs/                (all audit entries — append-only)
  → vault/state/               (watcher state, idempotency keys, rate limits, queue)
```

---

## 9. Success Criteria

Each criterion is independently verifiable.

### SC-010 — Gmail Watcher (mock mode)
`python -m pytest tests/test_gmail_watcher.py -v` passes with 0 failures. In mock mode (no
credentials), `GmailWatcher.check_for_updates()` returns items from `gmail_mock/sample_email.json`
through the full pipeline to `vault/Needs_Action/`.
**Real integration required for Silver certification** (mock acceptable for CI).

### SC-011 — WhatsApp Watcher (mock mode)
`python -m pytest tests/test_whatsapp_watcher.py -v` passes. In mock mode,
`WhatsAppWatcher.check_for_updates()` returns items from `whatsapp_mock/sample_message.json`.
**Real integration required for Silver certification** (mock acceptable for CI).

### SC-012 — Two Concurrent Watchers Running
Start orchestrator with mock mode enabled. Orchestrator logs show at least two watcher threads:
`[watcher-gmail_watcher]` and `[watcher-filesystem_watcher]` (or whatsapp). Neither raises
`NotImplementedError`. Both write items to `vault/Inbox/` within one scan cycle.

### SC-013 — Lead Detection End-to-End
Drop a file containing "I'm interested in your pricing" into `vault/Watch/`. After one scan
cycle: Inbox item exists → triaged → `detect_lead` upgrades to `type: lead`, `priority: CRITICAL`,
`lead_score >= 2` → `LEAD_*.md` file in `vault/Needs_Action/` → lead plan template used →
approval request for `send_email` step in `vault/Pending_Approval/`.

### SC-014 — Real Email Send via email-mcp
**Real mode**: Set `DEV_MODE=false`, set Gmail credentials. Approve an email send plan. After
executor runs, audit log contains `simulated: false` and email appears in Gmail Sent folder.
**CI mode**: `simulated: true` acceptable in automated tests.
**Real integration required for Silver certification**.

### SC-015 — LinkedIn Post Approved and Published
**Real mode**: With `browser-mcp` running, approve a `LINKEDIN_POST_*.md` plan. Executor audit
log records `action: published_linkedin_post`, `simulated: false`. Post visible on LinkedIn.
**CI mode**: `simulated: true` with `post_social` action acceptable.
**Real integration required for Silver certification**.

### SC-016 — Claude Plan Reasoning
With `ANTHROPIC_API_KEY` set and `dev_mode: false`, drop any file and wait for planning cycle.
The resulting `PLAN_*.md` in `vault/Plans/` contains a `## Reasoning` section with non-template
text. Without API key or in DEV_MODE, plan is generated from template without error.

### SC-017 — Weekly Briefing Generation
Run `python -c "from src.skills.weekly_briefing import run; import json; print(json.dumps(run('vault')))"`.
`vault/Briefings/BRIEFING_<date>.md` is created with all required sections present (verified by
`grep` for section headers). No error returned.

### SC-018 — Scheduling Installation (Idempotent)
**Windows**: Run `python src/skills/install_schedule.py`. Run
`schtasks /query /tn FTE-Orchestrator` — task exists with `Status: Ready`. Run installer again —
`schtasks /query` still shows exactly 1 task (not 2). Run `uninstall_schedule.py` — task removed.
**Linux/Mac**: `crontab -l | grep FTE` shows exactly 2 entries. Re-run: still 2 entries.

### SC-019 — Quarantine Safety Net
Run integration test that forces 3 consecutive execution failures for one item. Item is in
`vault/Quarantine/`. A MEDIUM audit entry exists. `Dashboard.md` shows `Quarantine | 1`.
Item is NOT in `vault/Plans/` or `vault/Needs_Action/`.

### SC-020 — All Tests Pass; Coverage ≥ 70%
```bash
python -m pytest tests/ -v --tb=short
# All 385 Bronze tests pass. All new Silver tests pass.

python -m pytest tests/ --cov=src --cov-report=term-missing --cov-fail-under=70
# >= 70% line coverage on src/ (Silver constitution requirement)
```

---

## 10. Out of Scope (Silver)

The following are explicitly NOT part of Silver Tier:

- **Finance watcher / Odoo integration** — Gold tier
- **Bank transaction monitoring** — Gold tier
- **Facebook / Instagram / Twitter/X social** — Gold tier
- **WhatsApp voice/media download** — media noted but not downloaded in Silver
- **Bulk email campaigns** — single-recipient sends only
- **Vault encryption** — Gold+
- **Ralph Wiggum loop (Claude Code Stop hook)** — Gold tier
- **Circuit breakers** — Gold tier (Silver has retry + quarantine)
- **Vault backup / Git checkpoints** — Gold tier
- **Slack MCP** — not required for Silver
- **calendar-mcp** — not required for Silver
- **A2A inter-agent messaging** — Platinum tier
- **Cloud deployment** — Platinum tier
- **Structured JSON audit logging** — Gold tier (Silver uses enhanced Markdown)

---

## 11. Risks and Mitigations

**Risk 1**: Gmail OAuth2 setup is complex (requires Google Cloud project, consent screen, scopes).
**Mitigation**: Detailed quickstart guide in `specs/002-silver-tier/quickstart.md`. Dry-run mock
mode lets the rest of Silver work without completing OAuth setup. Tests always run in mock mode.

**Risk 2**: LinkedIn login via browser-mcp is fragile (UI changes break selectors; automation
may trigger platform security flags).
**Mitigation**: Wrap all browser-mcp calls in try/except; fallback to `simulated: true` with a
MEDIUM audit warning. Rate-limit posts strictly (max 5/day). Include `#AIAssisted` disclosure.

**Risk 3**: Claude API latency (2–5s per call) in `generate_plan` adds time to the scan cycle.
**Mitigation**: Claude call is non-blocking within the sequential scan loop. Configurable
`use_claude: false` in settings.yaml to disable without code changes. Default model:
`claude-haiku-4-5` (fastest, cheapest; configurable via `ANTHROPIC_PLAN_MODEL` env var).

---

## 12. Project Structure (Silver additions only)

```
specs/002-silver-tier/
├── spec.md              # This file
└── quickstart.md        # OAuth2 setup + first-run instructions

src/
├── watchers/
│   ├── gmail_watcher.py           [IMPLEMENT]  Gmail OAuth2 polling
│   ├── whatsapp_watcher.py        [IMPLEMENT]  Twilio REST polling
│   └── linkedin_watcher.py        [NEW]        browser-mcp engagement reader
│
├── skills/
│   ├── detect_lead.py             [NEW]        Lead scoring skill
│   ├── generate_plan.py           [NEW]        Claude-reasoning planner
│   ├── generate_linkedin_post.py  [NEW]        LinkedIn post drafter
│   ├── weekly_briefing.py         [NEW]        CEO briefing aggregator
│   ├── install_schedule.py        [NEW]        OS scheduler registration
│   └── uninstall_schedule.py      [NEW]        Remove FTE scheduled tasks
│
├── core/
│   ├── idempotency.py             [NEW]        Idempotency key store
│   ├── rate_limiter.py            [NEW]        Per-action hourly counter
│   └── opt_out.py                 [NEW]        Opt-out list checker
│
└── actions/
    └── action_executor.py         [MODIFY]     Real email-mcp + browser-mcp wiring

vault/
├── Briefings/                     [NEW]
├── Quarantine/                    [NEW]
├── Templates/
│   └── linkedin_post_prompt.md    [NEW]
├── Opt_Out_List.md                [NEW]
└── Watch/
    ├── gmail_mock/
    │   └── sample_email.json      [NEW]
    └── whatsapp_mock/
        └── sample_message.json    [NEW]

tests/
├── test_gmail_watcher.py          [NEW]
├── test_whatsapp_watcher.py       [NEW]
├── test_linkedin_watcher.py       [NEW]
├── test_detect_lead.py            [NEW]
├── test_generate_plan.py          [NEW]
├── test_linkedin_post.py          [NEW]
├── test_weekly_briefing.py        [NEW]
├── test_idempotency.py            [NEW]
├── test_rate_limiter.py           [NEW]
├── test_opt_out.py                [NEW]
└── test_e2e_silver.py             [NEW]
```

---

## 13. Constitution Traceability

| Silver Requirement | Constitution Section | SC | Status |
|--------------------|---------------------|----|--------|
| All Bronze requirements | Tier Inheritance | SC-020 | Specified |
| 2+ working watchers | S2.2(1), S4.2 (Layer 2) | SC-012 | Specified |
| LinkedIn sales posts | S2.2(6), S9.1 (HIGH) | SC-015 | Specified |
| Claude reasoning loop + Plan.md | S2.2(4), S4.5 | SC-016 | Specified |
| One working MCP server (email-mcp) | S2.2(3), S4.2(Layer 5), S8.4 | SC-014 | Specified |
| HITL approval workflow | S2.2(2), S9.1, S12 | SC-019 | Specified (extended from Bronze) |
| Basic scheduling | S2.2(5), S7.4 | SC-018 | Specified |
| All AI as Agent Skills | S2.2(7), S5.3 | SC-020 | Specified |
| Idempotency keys | S7.1a | SC-012 | Specified |
| Quarantine (fail×3) | S11.7 | SC-019 | Specified |
| Rate limits | S7.3 | SC-015 | Specified |
| AI disclosure footer | S13.3 | FR-D01 | Specified |
| Opt-out list | S13.4 | FR-D01 | Specified |
| DRY_RUN flag | S8.2(SEC7) | SC-012 | Specified |
| ≥70% test coverage | S5.2 (Silver) | SC-020 | Specified |
| Approval timeout 48h | S7.2 (Silver) | settings.yaml | Specified |
| 2-minute poll interval | S4.2 (Silver Layer 2) | FR-H05 | Specified |
| Event-to-triage < 5 minutes | S7.2 | SC-010 | Specified |
