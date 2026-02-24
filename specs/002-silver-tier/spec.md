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
  → Action Layer        (email-mcp real sends [NEW] + Playwright LinkedIn [NEW])
  → Orchestration Layer (Task Scheduler / cron scheduling [NEW])
```

---

## Clarifications

| Question | Decision | Rationale |
|----------|----------|-----------|
| Which WhatsApp API? | Twilio WhatsApp REST (polling) | No public webhook URL needed; mock fallback when creds absent |
| LinkedIn post how? | Playwright directly in Python (same pattern as WhatsApp watcher) | browser-mcp is a Claude Code MCP server; runtime Python orchestrator cannot call it. Persistent session at `vault/state/linkedin_session/`. |
| "Claude reasoning loop" means? | New `generate_plan.py` skill calls Claude API | Falls back to Bronze PLAN_TEMPLATES when `dev_mode: true` or no API key |
| Scheduling on Windows? | `schtasks.exe` on Windows, crontab on Linux/Mac | Idempotent; uninstall script included |
| Gmail watcher dedup key? | `message_id` from Gmail API | Matches `_make_item_id()` pattern in BaseWatcher |
| Test without real credentials? | Dry-run reads from `vault/Watch/gmail_mock/` and `whatsapp_mock/` | Full pipeline works without any live API calls |

### Session 2026-02-20

- Q: How does Python action_executor call email-mcp at runtime? → A: MCP Python SDK (`mcp` client library connects to the `npx @anthropic/email-mcp` server process and calls its `send_email` tool programmatically; not subprocess or HTTP).
- **Architecture change**: WhatsApp watcher changed from Twilio REST API to **Playwright-based WhatsApp Web automation** (same session pattern as LinkedIn watcher). No Twilio account required. Session stored at `vault/state/whatsapp_session/`. First run uses `setup_session()` to scan QR code; subsequent runs headless. NOTE: WhatsApp ToS prohibits automated use — personal productivity only.
- Q: Gmail credential storage — env var GMAIL_REFRESH_TOKEN or token file? → A: Token file (`vault/.gmail_token.json`) written by `gmail_auth.py` OAuth2 flow; `GmailWatcher` reads it via `google.oauth2.credentials.Credentials` with automatic token refresh. Remove `GMAIL_REFRESH_TOKEN` from `.env.example`.
- Q: What is the exact format of `vault/Opt_Out_List.md`? → A: Markdown list — one `- email@example.com` entry per line; headings and blank lines are skipped by the parser.
- Q: Does the orchestrator call weekly_briefing, or is it OS-scheduler-only? → A: Orchestrator time-guard — orchestrator calls `weekly_briefing.run()` every scan cycle; the skill self-guards by checking (a) current day is Monday and (b) `vault/Briefings/BRIEFING_<this-monday>.md` does not yet exist. Returns `{skipped: true}` immediately if either condition fails.
- Q: LinkedIn credential storage — plaintext password in .env or session cookie file? → A: Session cookie file — one-time manual Playwright `setup_session()` login; session persisted to `vault/state/linkedin_session/` (gitignored). No `LINKEDIN_EMAIL` or `LINKEDIN_PASSWORD` in `.env`.
- Q: How does runtime Python orchestrator call LinkedIn/browser features? → A: Playwright directly in Python (same pattern as WhatsApp watcher) — `linkedin_watcher.py` and `post_social` action use `playwright.sync_api` with persistent session at `vault/state/linkedin_session/`. browser-mcp is a Claude Code tool only; runtime Python cannot call it.
- Q: How does generate_plan.py integrate with plan_task.py without modifying it? → A: Post-process approach — `generate_plan.run()` calls `plan_task.run()` to create the Plan.md file, then reads the written file and prepends a `## Reasoning` section authored by Claude. `plan_task.py` remains completely unchanged.
- Q: Where does gmail_auth.py live? → A: `src/watchers/gmail_auth.py` — standalone script in the watchers package. Run once: `python src/watchers/gmail_auth.py`. Writes `vault/.gmail_token.json`. Mirrors `setup_session()` pattern from WhatsApp/LinkedIn watchers.
- Q: Does `base_watcher.py` get shared `dry_run` + `_load_mock_items()` or does each watcher handle independently? → A: Extend `base_watcher.py` — single implementation in base class; all three new watchers delegate to it. `WhatsAppWatcher` already follows this pattern; `GmailWatcher` and `LinkedInWatcher` MUST do the same.
- Q: How does the orchestrator trigger `generate_linkedin_post`? → A: Self-guard inside skill — orchestrator calls `generate_linkedin_post.run()` every scan cycle; skill self-guards by checking (a) `enabled` flag and (b) `rate_limiter` posts-today count. Returns `{skipped: 1}` immediately when either gate fails. Same pattern as `weekly_briefing`. No orchestrator-level scheduling logic needed.
- Q: When an action is rate-limited and placed in `queue.json`, how is it eventually processed? → A: Drain on next scan cycle — `execute_plan.py` checks `vault/state/queue.json` at the start of each cycle (before processing new plans). Any queued entry whose rate limit is no longer exceeded is re-attempted via the normal executor path and removed from the queue. Queue entries carry `{action_type, details, plan_id, queued_at}`. No new component required.
- Q: What page does `linkedin_watcher.py` navigate to and what data does it extract? → A: Profile activity page — navigates to `https://www.linkedin.com/in/<username>/detail/recent-activity/`; `LINKEDIN_USERNAME` set in settings.yaml. Extracts the 5 most recent posts: reaction count (from `aria-label` on reaction button), comment count, post text preview. Returns items with `type: social_media_engagement`, `source: linkedin`.
- Q: What minimal JSON schema must `vault/Watch/gmail_mock/*.json` files provide? → A: Flat mock schema — `{"id", "subject", "from", "to", "body", "received_at", "thread_id"}`. `GmailWatcher` normalises both real nested Gmail API responses and flat mock files via a `_parse_message()` helper. One parsing path for each; mock files need NOT mirror the real `payload.headers[]` structure.
- Q: Section 1 claims `execute_plan.py` is unchanged, but FR-D06 (queue drain) and FR-J04 (quarantine) require modifications. Which is correct? → A: Mark as modified — `execute_plan.py` is minimally extended (not unchanged); queue drain prepended at entry, quarantine check appended after fail_count increment. Core plan-execution logic untouched. Added to Files to Modify table.
- Q: Do watchers run as concurrent daemon threads or polled sequentially in the scan cycle? → A: Daemon threads — each watcher runs in its own `threading.Thread(daemon=True)` with its own `poll_interval` sleep loop; allows per-watcher intervals (Gmail/WhatsApp 120s, LinkedIn 3600s, Filesystem 5s) without blocking each other. Same pattern as Bronze FilesystemWatcher.
- Q: What controls `generate_linkedin_post` posting cadence — `frequency_days` interval or `max_posts_per_day` daily cap? → A: `frequency_days` — skill scans `vault/Logs/` for any LinkedIn post in the last `frequency_days` days (default: 3); if found, returns `{skipped: 1}`. The global `rate_limits.post_social: 10/hour` in `action_executor` remains as a hard safety ceiling. `max_posts_per_day` removed from skill config to eliminate ambiguity.
- Q: What data does each watcher health row in Dashboard.md show? → A: Last-poll timestamp + item count — each watcher thread writes its result into a shared dict in the orchestrator (`{last_poll: ISO_timestamp, items_this_cycle: int, status: "OK"/"ERROR"}`); `update_dashboard.py` reads this dict and renders a row per watcher.
- Q: What is the format and creator of `vault/Business_Goals.md`? → A: Human-maintained Markdown — committed template with placeholder sections (company name, services, target customer, tone, goals); user fills it in once during setup. Skills read it as raw text passed to Claude as context. No machine parsing required. Ships as a template file in the repo.

---

## 1. Feature Overview

Silver Tier adds eight capabilities on top of the unchanged Bronze foundation:

1. **Multi-channel perception** — Gmail (OAuth2) and WhatsApp (Playwright/WhatsApp Web) watchers
   run concurrently alongside the existing filesystem watcher. A new LinkedIn watcher reads
   engagement metrics.

2. **Real email sends** — `email-mcp` (`npx @anthropic/email-mcp`) replaces simulated email sends
   when `dev_mode: false` and Gmail credentials are present.

3. **LinkedIn sales posts** — `generate_linkedin_post` skill drafts posts using Claude, requires
   HIGH HITL approval, then publishes via Playwright direct. All posts include `#AIAssisted`.

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
- `src/skills/triage_inbox.py`, `check_handbook.py`: **unchanged**
- `src/skills/update_dashboard.py`: **minimally extended** — new watcher health rows + Quarantine/Briefings counts added
- `src/skills/execute_plan.py`: **minimally extended** — queue drain prepended at entry; quarantine check appended after fail_count increment; core plan-execution logic untouched
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

**Acceptance**: A WhatsApp message received via WhatsApp Web creates an Inbox item within 2 minutes
(real headless mode) or immediately in dry-run mock mode.

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
approval, Playwright publishes the post. Audit entry records `simulated: false` (real mode).

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
written. On the next scan cycle (when the hourly counter has reset), `execute_plan.py` drains
the queue and re-attempts the action automatically — no human intervention required.

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
messages from `vault/Watch/gmail_mock/*.json` using a **flat mock schema** and behave identically
to live mode for all downstream processing. Mock schema:
```json
{
  "id": "gmail_message_id_string",
  "subject": "Email subject line",
  "from": "sender@example.com",
  "to": "recipient@example.com",
  "body": "Plain text email body",
  "received_at": "2026-02-20T09:00:00Z",
  "thread_id": "thread_id_string"
}
```
`GmailWatcher` MUST implement a `_parse_message(raw: dict) -> dict` normalisation helper that
accepts EITHER the flat mock schema OR the real Gmail API nested response (detected via presence
of `"payload"` key) and returns the same normalised item dict in both cases.

**FR-A06**: OAuth token refresh MUST be handled automatically. Refresh failures MUST produce a
MEDIUM audit entry and pause the watcher (not crash the orchestrator).

**FR-A07**: Watcher state `vault/state/gmail_watcher_state.json` MUST persist processed message
IDs and last successful poll timestamp. Token expiry is managed by `vault/.gmail_token.json`
(written by `google-auth`); the state file does NOT duplicate token data.

**FR-A08**: The watcher MUST NOT make more than 100 Gmail API calls per hour.

---

### FR-B: WhatsApp Watcher

> **Architecture**: Playwright-based WhatsApp Web automation (not Twilio REST API).
> No API credentials required. Session stored at `vault/state/whatsapp_session/`.
> NOTE: WhatsApp ToS prohibits automated use — personal productivity only.

**FR-B01**: `src/watchers/whatsapp_watcher.py` MUST implement `check_for_updates()` using
**Playwright persistent browser context** (`playwright.sync_api.sync_playwright`) pointing to
`vault/state/whatsapp_session/`. No API credentials required.

**FR-B02**: The watcher MUST poll WhatsApp Web at `poll_interval` (default: 120s) in headless
mode once a session exists. It navigates to `https://web.whatsapp.com`, waits for
`[data-testid="chat-list"]`, then queries `[data-testid="icon-unread-count"]` to find unread chats.

**FR-B03**: Each unread chat cell is parsed via `inner_text()` (line 0 = sender, line 1 = body
preview). Items are keyword-filtered (configurable via `settings.yaml`). Each message MUST be
converted to an item dict with keys: `id` (= `WA_{sender_norm}_{body_hash}`), `source: whatsapp`,
`from_number`, `body`, `type`, `priority`, `filename` (= `WA_<id>.md`), `tags: []`.

**FR-B04**: Priority: `HIGH` if body/sender contains `urgent`, `asap`, `emergency`, `critical`;
`MEDIUM` otherwise. Deduplication: content-hash-based ID — same sender+body = same ID = skipped.

**FR-B05**: When `DRY_RUN=true` or `vault/state/whatsapp_session/` does not exist, the watcher
MUST read mock messages from `vault/Watch/whatsapp_mock/*.json`.
Mock schema: `{"MessageSid": "...", "From": "...", "Body": "..."}`.

**FR-B06**: `setup_session()` MUST open a non-headless browser for the user to scan the QR code
and persist the session. Only needed once. Subsequent runs use headless mode automatically.

**FR-B07**: If QR code is detected during a headless run (session expired), the watcher MUST
log a warning and return `[]` without crashing the orchestrator. Session re-setup is triggered
manually by calling `setup_session()` again.

**FR-B08**: Watcher state `vault/state/whatsapp_watcher_state.json` MUST persist processed
message IDs (content-hash-based) to survive orchestrator restarts.

---

### FR-C: LinkedIn Watcher + Post Generator

**FR-C01**: `src/watchers/linkedin_watcher.py` MUST exist as a read-only watcher that reads
engagement data (reaction count, comment count) from recent posts using **Playwright directly**
(`playwright.sync_api`) — identical pattern to `whatsapp_watcher.py`. Authentication uses a
**persisted browser session** stored in `vault/state/linkedin_session/` (gitignored). On first
run (session absent), `setup_session()` opens a headful browser for manual login; subsequent
runs are headless. `browser-mcp` is NOT used at runtime (it is a Claude Code tool only). No
LinkedIn credentials are stored in `.env`. If session is expired or Playwright fails, the
watcher returns an empty list and logs a LOW audit entry with re-login instructions.

**Target page**: `https://www.linkedin.com/in/<username>/detail/recent-activity/`
where `<username>` is read from `settings.yaml` under `watchers.linkedin.username`.
**Extracted fields** (5 most recent posts):
- `reactions`: integer parsed from `aria-label` on the reaction button (e.g. "42 reactions")
- `comments`: integer parsed from comment count element text
- `post_preview`: first 200 chars of post text
- `post_url`: canonical URL of the post
Each post becomes one item dict with `type: social_media_engagement`, `source: linkedin`,
`platform: linkedin`, `reactions`, `comments`, `post_preview`, `post_url`, `id` (= SHA256 of post_url[:12]).

**FR-C02**: LinkedIn watcher items MUST have `type: social_media_engagement`, `source: linkedin`,
`platform: linkedin`. These trigger the `social_media_engagement` plan template (FR-I).

**FR-C03**: `src/skills/generate_linkedin_post.py` MUST be an Agent Skill that:
- Reads `vault/Business_Goals.md` (human-maintained Markdown template; raw text passed as Claude context)
  and recent vault activity (last 7 days from Logs/) as context.
- Calls Claude API (`ANTHROPIC_API_KEY`) to draft a post (max 3,000 chars, professional tone,
  value-first, no hard-sell, includes a CTA). Falls back to configurable template when
  `dev_mode: true` or API key absent.
- Writes the draft to `vault/Plans/LINKEDIN_POST_<timestamp>.md` with `type: linkedin_post`,
  `risk_level: HIGH`, `requires_approval: true`.
- The plan includes a `post_social` step tagged `platform: linkedin` executed via `action_executor`.

**FR-C04**: Publishing a LinkedIn post via **Playwright directly** (reusing the LinkedIn
persistent session at `vault/state/linkedin_session/`) MUST be a HIGH-risk action requiring
explicit HITL approval. The approval file MUST include the full post text for human review.
`browser-mcp` is NOT used; `action_executor` calls `playwright.sync_api` for the `post_social`
action type.

**FR-C05**: All LinkedIn posts MUST include `#AIAssisted` per constitution S13.3.

**FR-C06**: LinkedIn post frequency MUST NOT exceed 1 post per `frequency_days` (default: 3 days),
enforced by the `generate_linkedin_post` skill cadence guard (FR-F03). The global
`rate_limits.post_social: 10/hour` in `action_executor` acts as a hard ceiling across all
social post actions.

---

### FR-D: Email MCP Integration (Real Sends)

**FR-D01**: `src/actions/action_executor.py` MUST be extended with a real `_send_email` handler
that calls `email-mcp` via the **MCP Python SDK** (`mcp` client library) — connecting to the
`npx @anthropic/email-mcp` server process and invoking its `send_email` tool programmatically
(not via subprocess or HTTP) — when `dev_mode: false`. The handler MUST:
- Append the AI disclosure footer: "This message was drafted with AI assistance."
- Check `vault/Opt_Out_List.md`; skip + log `skipped: opted_out` if recipient is listed.
- Check rate limiter (max 20 emails/hour). If rate-limited: append
  `{action_type, details, plan_id, queued_at: <iso_timestamp>}` to `vault/state/queue.json`
  and return `{success: false, queued: true, reason: "rate_limited"}`. Do NOT raise an exception.
- Generate and check an idempotency key before calling email-mcp.
- Return `{success, action_type, details, simulated: false, message_id}`.

**FR-D02**: When `dev_mode: true` (default), `_send_email` MUST simulate exactly as Bronze,
returning `simulated: true` without calling email-mcp.

**FR-D03**: `DRY_RUN=true` in environment MUST force simulation across ALL external actions
regardless of `dev_mode` setting.

**FR-D04**: All Gmail credentials MUST be loaded from `.env` only — never from vault files.

**FR-D05**: Email send failures MUST retry with exponential backoff (1s, 2s, 4s — 3 attempts).
After 3 failures: log `failure`, increment item `fail_count`, move to Quarantine if `fail_count >= 3`.

**FR-D06**: `src/skills/execute_plan.py` MUST drain `vault/state/queue.json` at the START of
each invocation (before processing new plans). For each queued entry, re-check the rate limiter:
- If the limit has reset: re-attempt the action via `action_executor`, remove entry from queue.
- If still limited: leave entry in queue, write a MEDIUM audit entry (avoids log flood).
Queue entries schema: `{action_type: str, details: dict, plan_id: str, queued_at: str (ISO)}`.
Entries older than 24h are purged without retry (stale action guard).

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

**FR-F03**: The orchestrator scan cycle MUST call `generate_linkedin_post.run()` on every cycle
(same pattern as `weekly_briefing`). The skill MUST self-guard on entry:
1. Check `skills.generate_linkedin_post.enabled: true` in settings.yaml; if `false`, return
   `{skipped: 1}` immediately.
2. Scan `vault/Logs/` for any audit entry with `action: linkedin_post` in the last
   `frequency_days` days (default: 3); if found, return `{skipped: 1}` immediately.
3. Only if both guards pass: generate and write the post draft for HITL approval.
The orchestrator has no scheduling logic for this skill — the skill decides for itself.
The global `rate_limits.post_social: 10/hour` in `action_executor` remains as a hard safety
ceiling independent of this skill-level guard. `max_posts_per_day` is NOT used by this skill.

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
  {"step_number": 2, "action_type": "post_social",    "description": "Publish LinkedIn post via Playwright direct",   "risk_level": "HIGH", "requires_approval": True,  "status": "pending"},
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

**FR-I02**: `src/skills/generate_plan.py` MUST use a **post-process approach**:
1. Call `plan_task.run(vault_root)` — this creates `PLAN_*.md` in `vault/Plans/` using the
   existing Bronze templates. `plan_task.py` is NOT modified.
2. If `ANTHROPIC_API_KEY` is set and `dev_mode: false`: read the newly written `PLAN_*.md`,
   call Claude API to generate a `## Reasoning` section explaining the plan's intent and step
   rationale, then prepend this section to the file (insert after the YAML frontmatter block,
   before the first `##` heading).
3. If API key absent or `dev_mode: true`: return the plan as-is from step 1 without error.
4. MUST NOT re-plan items that already have a Plan in `vault/Plans/`.
5. Returns the result dict from `plan_task.run()` extended with `{claude_enriched: bool}`.
- Recommended Claude model: `claude-haiku-4-5` (speed + cost; configurable via
  `ANTHROPIC_PLAN_MODEL` env var).

**FR-I03**: The orchestrator scan cycle MUST call `generate_plan.run()` instead of
`plan_task.run()`. `plan_task.py` itself is unchanged and remains independently testable.

---

### FR-J: Safety, Dry-Run, and Quarantine

**FR-J01**: All new watchers MUST support dry-run mode (credentials absent OR `DRY_RUN=true`).
In dry-run mode, watchers read from their mock folder and prefix audit entries with `[DRY_RUN]`.

**FR-J02**: `src/watchers/base_watcher.py` MUST be extended with shared dry-run infrastructure
(per clarification 2026-02-20 — single implementation in base class, no per-watcher duplication):
- `dry_run: bool` property (checks `DRY_RUN` env var or constructor flag; default `False`)
- `_load_mock_items(mock_folder: str) -> list[dict]` helper that reads `*.json` files from
  `mock_folder`, parses each as an item dict, and returns the list (skips malformed files).
Both `GmailWatcher` and `LinkedInWatcher` MUST delegate to these base methods; they MUST NOT
re-implement dry-run logic independently. (`WhatsAppWatcher` already implements this pattern.)

**FR-J03**: Mock folder structure:
- `vault/Watch/gmail_mock/sample_email.json` — flat schema: `{id, subject, from, to, body, received_at, thread_id}`
- `vault/Watch/whatsapp_mock/sample_message.json` — `{MessageSid, From, Body, To}` schema
- `vault/Watch/linkedin_mock/sample_post.json` — `{post_url, reactions, comments, post_preview}` schema
- All three folders created by `orchestrator._ensure_vault_structure()`
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
│  PERCEPTION LAYER (4 concurrent watcher daemon threads)      │
│                                                              │
│  GmailWatcher ─────────────────────────────────────────────┐ │
│  (google-api-python-client, OAuth2)  poll: 120s             │ │
│                                                             │ │
│  WhatsAppWatcher ──────────────────────────────────────────┼─┤→ vault/Inbox/
│  (Playwright, WhatsApp Web)          poll: 120s             │ │  ITEM_*.md
│                                                             │ │
│  LinkedInWatcher ──────────────────────────────────────────┼─┤  (engagement items)
│  (Playwright, profile activity page) poll: 3600s            │ │
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
│          email-mcp   Playwright     file_operation           │
│          (send_email) (post_social) (vault writes)           │
│          MCP SDK if    direct sync   —                       │
│          dev_mode=F    dev_mode=F                            │
│                                                              │
│  4. update_dashboard.run()  refresh Dashboard.md       ──── │
└──────────────────────────────────────────────────────────────┘
                    │
          (also in scan cycle — self-guard controls execution)
┌──────────────────────────────────────────────────────────────┐
│  SELF-GUARDED SKILLS (called every cycle; skip internally)   │
│                                                              │
│  5. generate_linkedin_post.run()  — self-guards: frequency_  │
│                                     days check via Logs/     │
│  6. weekly_briefing.run()         — self-guards: Monday +    │
│                                     briefing-exists check    │
│  (install_schedule.py — run once manually, idempotent)       │
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
  │               ├── post_social: Playwright direct (real) or simulate
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
| `src/watchers/gmail_auth.py` | Auth Script | One-time OAuth2 flow; writes `vault/.gmail_token.json`. Run: `python src/watchers/gmail_auth.py` |
| `src/watchers/gmail_watcher.py` | Watcher | Gmail API OAuth2 polling — replaces Bronze stub |
| `src/watchers/whatsapp_watcher.py` | Watcher | Playwright WhatsApp Web automation — implemented |
| `src/watchers/linkedin_watcher.py` | Watcher | Playwright LinkedIn engagement reader + `setup_session()` |
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
| `vault/Business_Goals.md` | Vault | Human-maintained template following the **Documents.md schema exactly**: YAML frontmatter with `last_updated` + `review_frequency: weekly`; body sections: `## Q1 2026 Objectives` → `### Revenue Target` (Monthly goal placeholder / Current MTD placeholder) → `### Key Metrics to Track` table (Client response time / Invoice payment rate / Software costs) → `### Active Projects` list → `### Subscription Audit Rules` (flag on no-login-30d / cost-increase-20% / duplicate-functionality). User fills placeholder values once during setup. Skills read as raw Markdown text. **Note**: file already exists from Bronze as a simpler placeholder; Silver replaces it with this full template. |
| `vault/Opt_Out_List.md` | Vault | Email opt-out list (initially empty) |
| `vault/Watch/gmail_mock/sample_email.json` | Mock | Flat mock schema `{id, subject, from, to, body, received_at, thread_id}` for dry-run |
| `vault/Watch/whatsapp_mock/sample_message.json` | Mock | Sample WhatsApp mock message `{MessageSid, From, Body, To}` for dry-run |
| `vault/Watch/linkedin_mock/sample_post.json` | Mock | `{post_url, reactions, comments, post_preview}` for dry-run |
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
| `vault/Dashboard.md` | Add `## 💰 Bank Balance` placeholder section immediately after the page header (Documents.md §1: "Real-time summary of **bank balance**, pending messages, and active business projects"). Rename `## 📝 Recent Actions` → `## 📝 Recent Activity` to match Documents.md §5 End-to-End example. **Bronze gap fix** — must ship in Silver Phase 1 Setup. |
| `vault/Company_Handbook.md` | Add `review_frequency: weekly` key to YAML frontmatter. Documents.md §4 describes the handbook as a "Rules of Engagement" document managed on a weekly review cycle. **Bronze gap fix** — must ship in Silver Phase 1 Setup. |
| `src/orchestrator.py` | Register all 4 watchers as `threading.Thread(daemon=True)` in `_init_watchers()` (each with its own `poll_interval` sleep loop); add `detect_lead`, `generate_plan` to `_scan_cycle()`; add new folders to vault structure init |
| `src/skills/plan_task.py` | Add `lead`, `linkedin_post`, `social_media_engagement` to `PLAN_TEMPLATES` dict |
| `src/skills/execute_plan.py` | Prepend queue drain (FR-D06); append quarantine move on fail_count ≥ 3 (FR-J04); core logic unchanged |
| `src/skills/update_dashboard.py` | Add Quarantine + Briefings folder counts; per-watcher health rows showing `last_poll` timestamp, `items_this_cycle` count, and `status` (OK/ERROR) read from orchestrator shared dict |
| `src/actions/action_executor.py` | Wire real `send_email` via MCP Python SDK (email-mcp); wire `post_social` via Playwright directly (LinkedIn session); add rate-limit, idempotency, opt-out, and AI disclosure footer |
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
    """Generate Plan.md for unplanned items via post-process enrichment.

    Flow: call plan_task.run() → plan written → if API key present, prepend ## Reasoning.
    plan_task.py is NOT modified. Returns plan_task result + {claude_enriched: bool}.
    Returns: {processed, claude_enriched, template_fallback, errors, skipped}
    """
```
Reads: `vault/Needs_Action/`, `vault/Business_Goals.md`, written `PLAN_*.md` (for enrichment)
Writes: `vault/Plans/` (via plan_task + optional Reasoning prepend), `vault/Needs_Action/` (status), `vault/Logs/`

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
    enabled: false               # set true after setup_session() completes
    poll_interval: 3600
    username: ""                 # LinkedIn profile username (e.g. "jane-smith-123")

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
    frequency_days: 3             # minimum days between posts (cadence guard in skill)
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

# Silver: WhatsApp (Playwright / WhatsApp Web)
# No API credentials — uses persistent browser session.
# Run setup_session() once to scan QR code. Session saved to vault/state/whatsapp_session/

# Silver: Claude API (generate_plan, generate_linkedin_post)
ANTHROPIC_API_KEY=sk-ant-xxxxxxxx
ANTHROPIC_PLAN_MODEL=claude-haiku-4-5

# Silver: LinkedIn (Playwright direct)
# No credentials in .env — LinkedIn uses a persisted Playwright browser session.
# On first run, call setup_session(). Session saved to vault/state/linkedin_session/

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
mcp>=1.0.0                # MCP Python SDK — action_executor calls email-mcp server
playwright>=1.40.0        # WhatsApp Web + LinkedIn browser automation
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
| `vault/Watch/linkedin_mock/` | Mock LinkedIn engagement items for dry-run | `orchestrator._ensure_vault_structure()` |

### New Vault Files

| File | Purpose |
|------|---------|
| `vault/Opt_Out_List.md` | Markdown list (`- email@example.com` per line); checked before every outbound send |
| `vault/Templates/linkedin_post_prompt.md` | Editable Claude prompt for LinkedIn post drafting |
| `vault/state/idempotency_keys.json` | Key → result map with TTL (auto-created) |
| `vault/state/rate_limits.json` | Hourly action counters (auto-created) |
| `vault/state/queue.json` | Rate-limited action overflow queue (auto-created) |
| `vault/state/linkedin_session/` | Persisted Playwright session (gitignored; written by `setup_session()` on first LinkedIn login) |

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

### SC-012 — Four Concurrent Watcher Threads Running
Start orchestrator with mock mode enabled. Orchestrator logs show all four watcher daemon threads:
`[watcher-gmail_watcher]`, `[watcher-whatsapp_watcher]`, `[watcher-linkedin_watcher]`, and
`[watcher-filesystem_watcher]`. None raises `NotImplementedError`. Gmail and filesystem watchers
write items to `vault/Inbox/` within one scan cycle (LinkedIn and WhatsApp require real sessions
or mock folders).

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
**Real mode**: With `vault/state/linkedin_session/` present, approve a `LINKEDIN_POST_*.md` plan. Executor audit
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

**Risk 2**: LinkedIn login via Playwright is fragile (UI changes break selectors; automation
may trigger platform security flags).
**Mitigation**: Wrap all Playwright calls in try/except; fallback to `simulated: true` with a
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
│   ├── gmail_auth.py              [NEW]        One-time OAuth2 setup script
│   ├── gmail_watcher.py           [IMPLEMENT]  Gmail API OAuth2 polling
│   ├── whatsapp_watcher.py        [DONE ✓]    Playwright WhatsApp Web (416 tests)
│   └── linkedin_watcher.py        [NEW]        Playwright LinkedIn engagement reader
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
    └── action_executor.py         [MODIFY]     Real email-mcp (MCP SDK) + Playwright wiring

vault/
├── Briefings/                     [NEW]
├── Quarantine/                    [NEW]
├── Templates/
│   └── linkedin_post_prompt.md    [NEW]
├── Business_Goals.md              [UPDATE — replace Bronze placeholder with Documents.md template]
├── Dashboard.md                   [UPDATE — add bank balance; rename Recent Actions→Recent Activity]
├── Company_Handbook.md            [UPDATE — add review_frequency: weekly to frontmatter]
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
