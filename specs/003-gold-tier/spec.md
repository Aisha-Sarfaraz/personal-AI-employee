# Gold Tier Specification: Autonomous AI Employee — Full Business Operations

**Version:** 1.0.0
**Date:** 2026-02-25
**Status:** IMPLEMENTED
**Tier:** GOLD (Autonomous Employee)
**Branch:** `003-gold-tier`
**Constitution Reference:** `.specify/memory/constitution.md`
**Predecessor:** `specs/002-silver-tier/spec.md` (531 passing tests, SC-010–SC-020 verified)
**Bronze Baseline:** `specs/001-bronze-tier/spec.md` (385 passing tests, SC-001–SC-009 verified)

---

## Context

Gold Tier transforms the Silver personal AI assistant into a **fully autonomous business
employee** operating across Personal + Business domains simultaneously. Where Silver proved
multi-channel perception (Gmail, WhatsApp, LinkedIn) and real email sends, Gold activates:

- **Live accounting** via a custom Odoo Community MCP server (JSON-RPC, Odoo 19+)
- **Cross-platform social media** — Facebook, Instagram, Twitter/X posting with engagement
  metrics — alongside the existing LinkedIn skill
- **Finance Watcher** — the Silver stub now fully implemented, polling Odoo + CSV fallback
- **Enhanced CEO Briefing** — Revenue, Expense, Bottleneck, Social Summary sections powered
  by real Odoo data
- **Enterprise error recovery** — `@with_retry` decorator, `ErrorCategory` taxonomy,
  per-component graceful degradation contracts
- **Gold audit logging** — structured JSON-Lines schema with actor, approval status, result
- **Ralph Wiggum autonomous loop** — Stop hook drives multi-step plans to completion without
  human re-prompting

All Silver and Bronze infrastructure is preserved unchanged. Gold adds new files; it does not
replace or refactor existing Silver/Bronze code except where explicitly required (minimal
patches to `audit_logger.py`, `weekly_briefing.py`, `execute_plan.py`,
`install_schedule.py`, `orchestrator.py`).

**Architecture layers (Gold additions highlighted):**

```
External Sources  (Gmail, WhatsApp, filesystem, Odoo, Facebook, Instagram, Twitter/X)
  → Perception Layer    (existing watchers + FinanceWatcher [GOLD] + FacebookWatcher [GOLD]
                          + TwitterWatcher [GOLD] + enhanced watchdog [GOLD])
  → Obsidian Vault      (+ Accounting/ + Logs/Archive/ [GOLD])
  → Reasoning Layer     (existing skills + post_facebook [GOLD] + post_twitter [GOLD]
                          + generate_invoice [GOLD] + accounting_audit [GOLD]
                          + error_recovery [GOLD])
  → Action Layer        (email-mcp [Silver] + odoo-mcp [GOLD])
  → Orchestration Layer (existing + ralph_loop [GOLD] + retry_handler [GOLD]
                          + stop hook [GOLD])
```

---

## Clarifications

| ID  | Question                        | Decision                                                                                               | Rationale                                                         |
|-----|---------------------------------|--------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------|
| C1  | Odoo 19 setup method            | **Docker Compose** — `docker-compose.odoo.yml` included; URL `http://localhost:8069`, DB `fte_db`     | Easiest reproducible setup; one command to start Odoo + PostgreSQL |
| C2  | Meta Graph API auth             | **Long-lived Page access token** in `.env` as `FACEBOOK_ACCESS_TOKEN`; no OAuth2 refresh flow         | Simpler; 60-day token lifespan sufficient for dev/production use   |
| C3  | Twitter/X API tier              | **Free tier** — 1,500 tweets/month write; 24h poll interval; conservative rate limits                 | Zero cost; Free tier sufficient for solo-business use case         |
| C4  | Ralph Wiggum hook registration  | **Auto via `install_schedule.py` extension** — writes hook script to `.claude/hooks/Stop` on first run | Consistent with Silver's idempotent scheduling pattern            |
| C5  | Finance Watcher data source     | **Odoo primary + CSV fallback** — Odoo JSON-RPC first; falls back to `vault/Watch/finance_drop/` CSV   | Most resilient; Finance Watcher pauses gracefully if Odoo is down |
| C6  | CEO Briefing delivery           | **Vault-only** — writes to `vault/Briefings/BRIEFING_<date>.md`; email delivery is future scope        | Safety-first; avoids auto-sending sensitive financial data         |

### Session 2026-02-25

- Q: Does `odoo-mcp` run as a persistent daemon or spawned per-call? → A: **Persistent stdio
  process** — orchestrator starts it once on boot via `mcp` Python SDK subprocess client; health-
  checked each scan cycle. Same lifecycle as `email-mcp`.
- Q: How does `finance_watcher.py` call the Odoo MCP client from Python? → A: Direct import of
  `src/mcp_servers/odoo_mcp/client.py` — not via MCP protocol; the Odoo MCP client is also exposed
  as a plain Python module callable from within the same process. The MCP server interface is
  used only when Claude Code tools need to call it directly.
- Q: Does `post_facebook.py` post to Feed or Business Page? → A: **Facebook Page** via
  `/me/feed` API (Page token) + Instagram Business cross-post via `/{ig-user-id}/media` +
  `/{ig-user-id}/media_publish`. Single approval request covers both platforms.
- Q: What is the Finance Watcher dedup key? → A: Odoo **journal item ID** (`move_line_id`);
  for CSV rows, SHA-256 hash of `date + description + amount`. Stored in
  `vault/state/finance_processed_ids.json`. Matches `_make_item_id()` pattern from
  `base_watcher.py`.
- Q: How does Ralph Wiggum know which plan file to watch? → A: The plan frontmatter includes
  `requires_ralph: true` + `ralph_task_file: vault/Plans/PLAN_<id>.md`; `ralph_loop.py` receives
  this path at startup and the Stop hook reads it from the state file at each exit intercept.
- Q: What mock data format do `facebook_watcher` and `twitter_watcher` use in dry-run mode?
  → A: Same flat JSON schema pattern as `gmail_mock/` — `{"id", "text", "likes", "comments",
  "reach", "created_at"}` for Facebook; `{"id", "text", "retweet_count", "like_count",
  "reply_count", "created_at"}` for Twitter.
- Q: What column format do CSV files in `vault/Watch/finance_drop/` use? → A: **4-column format
  matching vault output exactly**: `date,description,amount,account`. Columns map 1-to-1 to
  the `Current_Month.md` Markdown table; no transformation needed. Header row required.
  Amount is a signed decimal (negative = expense). Account is a free-text account name.
- Q: How does `OdooMCPClient` authenticate with Odoo JSON-RPC? → A: **Per-call auth** —
  each JSON-RPC request body includes `[db, uid, password, ...]` as positional args to
  `/web/dataset/call_kw`. No session authentication step; no session cookie management.
  Stateless; `uid` and `password` read from env vars on client init.
- Q: How does `twitter_watcher.py` obtain the Twitter numeric user ID for
  `GET /2/users/:id/tweets`? → A: **Static env var** — `TWITTER_USER_ID=<numeric_id>` added
  to `.env.example`; watcher reads it at startup. No API round-trip required. User looks up
  their numeric ID once from their Twitter profile.
- Q: What is the structure of `vault/state/ralph_loop_state.json` used by the Stop hook to
  identify the active task file? → A: **Minimal JSON with four keys**:
  `{"task_file": "<path>", "prompt": "<str>", "iteration": <int>, "status": "running|done|cancelled|quarantined"}`.
  `ralph_loop.py` writes/updates on each iteration start; Stop hook reads `task_file` to
  check whether it has moved to `vault/Done/`.

---

## 1. Feature Overview

Gold Tier adds ten capabilities on top of the unchanged Silver + Bronze foundation:

1. **Odoo Community MCP** — Custom Python stdio MCP server (`src/mcp_servers/odoo_mcp/`)
   wraps Odoo 19+ JSON-RPC External API. Six operations: `create_invoice`, `list_invoices`,
   `record_expense`, `get_account_balance`, `post_invoice`, `list_transactions`. Docker
   Compose setup at `docker-compose.odoo.yml`. All write ops require HIGH HITL approval.

2. **Finance Watcher** — Implements the Silver stub `src/watchers/finance_watcher.py`.
   Polls Odoo `list_transactions` every 300s; falls back to CSV files in
   `vault/Watch/finance_drop/` when Odoo unavailable. Appends new rows to
   `vault/Accounting/Current_Month.md`. Dev-mode reads `vault/Watch/finance_mock/*.json`.

3. **Facebook & Instagram integration** — `src/watchers/facebook_watcher.py` reads Page
   engagement via Meta Graph API (poll: 3600s). `src/skills/post_facebook.py` drafts posts
   with Claude, requires HIGH HITL, then publishes to Facebook Page + Instagram cross-post.

4. **Twitter/X integration (Free tier)** — `src/watchers/twitter_watcher.py` reads timeline
   metrics via Twitter API v2 (poll: 86400s). `src/skills/post_twitter.py` drafts tweets
   (<=280 chars), requires HIGH HITL, publishes via Twitter API v2. Rate: 1 tweet/day.

5. **MCP server registry** — `config/mcp_servers.yaml` formalises all MCP servers
   (`email-mcp`, `odoo-mcp`, `filesystem`). Orchestrator health-checks each on startup.

6. **Enhanced CEO Briefing** — `weekly_briefing.py` minimally extended to include Revenue
   (Odoo invoices), Expense (Odoo transactions + subscription audit), Bottleneck (task SLA
   delta), Proactive suggestions (unused subs), and Social Summary (all four platforms).

7. **Error recovery & graceful degradation** — `src/core/retry_handler.py` with
   `@with_retry` decorator + `ErrorCategory` enum. Per-component degradation contracts.
   Enhanced `src/watchers/watchdog.py` monitors all daemon threads.

8. **Gold audit logging schema** — `src/core/audit_logger.py` minimally extended to enforce
   the Gold JSON-Lines schema (`timestamp`, `action_type`, `actor`, `target`, `parameters`,
   `approval_status`, `approved_by`, `result`, `error`). 90-day retention + `Logs/Archive/`.

9. **Ralph Wiggum loop** — `src/core/ralph_loop.py` drives multi-step plans to completion
   using file-movement completion detection. Stop hook auto-registered by
   `install_schedule.py`. Max iterations configurable; overflow goes to quarantine.

10. **Full cross-domain integration** — Orchestrator `_scan_cycle` routes Personal domain
    items (Gmail, WhatsApp) and Business domain items (Odoo, Facebook, Twitter/X, Finance)
    through the same skill pipeline without conflict.

### What Silver + Bronze Stays Exactly the Same

- `src/core/vault.py`, `frontmatter.py`, `approval.py` — **unchanged**
- `src/watchers/gmail_watcher.py`, `whatsapp_watcher.py`, `linkedin_watcher.py`,
  `filesystem_watcher.py`, `base_watcher.py` — **unchanged**
- `src/skills/triage_inbox.py`, `check_handbook.py`, `detect_lead.py`,
  `generate_plan.py`, `generate_linkedin_post.py`, `plan_task.py`,
  `uninstall_schedule.py` — **unchanged**
- `src/core/idempotency.py`, `rate_limiter.py`, `opt_out.py` — **unchanged**
- `config/settings.yaml` existing keys — **unchanged** (only extended with new stanzas)
- All 531 Silver + 385 Bronze tests must pass throughout Gold implementation

---

## 2. User Stories

### User Story 1 — Finance Transactions Automatically Logged (Priority: P1)

As a business owner, I want bank transactions pulled from Odoo to appear automatically in
my vault each day, so I always have an up-to-date financial picture without manually
exporting data.

**Why this priority**: Financial visibility is the bedrock of the Gold CEO Briefing.
Without this, the Revenue and Expense sections of the briefing are empty.

**Independent Test**: Enable Finance Watcher in dev-mode with `vault/Watch/finance_mock/`
data; verify `vault/Accounting/Current_Month.md` is created/updated with correct rows.

**Acceptance Scenarios**:

1. **Given** `dev_mode: true` and mock JSON files exist in `vault/Watch/finance_mock/`,
   **When** the Finance Watcher polls, **Then** new transactions appear as rows in
   `vault/Accounting/Current_Month.md` within one poll cycle.
2. **Given** Odoo is unreachable (connection refused), **When** the Finance Watcher polls,
   **Then** it falls back to CSV files in `vault/Watch/finance_drop/` and logs a
   `result: degraded` audit entry.
3. **Given** a transaction has already been processed (dedup key exists in
   `finance_processed_ids.json`), **When** the Finance Watcher encounters it again,
   **Then** it is skipped (not re-added to the Accounting file).

---

### User Story 2 — Invoice Created from WhatsApp/Email Request (Priority: P1)

As a business owner, I want the AI to draft a customer invoice in Odoo when a client
requests one via WhatsApp or email, so I can approve and send invoices without opening Odoo.

**Why this priority**: Invoice creation is the primary revenue action in the Gold tier
accounting workflow and demonstrates the Odoo MCP integration end-to-end.

**Independent Test**: Place a `WHATSAPP_invoice_request.md` file in `vault/Needs_Action/`;
run orchestrator in dev-mode; verify `vault/Pending_Approval/INVOICE_<id>.md` is created.

**Acceptance Scenarios**:

1. **Given** a WhatsApp item in `vault/Needs_Action/` with `intent: invoice_request`,
   **When** `generate_invoice.run()` executes, **Then** a `vault/Pending_Approval/
   INVOICE_<timestamp>.md` approval file is created with partner, amount, and description.
2. **Given** the approval file is moved to `vault/Approved/`, **When** the orchestrator
   detects it (dev_mode: false), **Then** `odoo-mcp create_invoice` is called and a draft
   invoice exists in Odoo (verified by `list_invoices`).
3. **Given** `dev_mode: true`, **When** the invoice action runs, **Then** the Odoo MCP
   call is simulated and logged (`simulated: true`) but no real Odoo HTTP call is made.

---

### User Story 3 — Facebook & Instagram Post Published (Priority: P2)

As a business owner, I want the AI to draft and publish social posts to Facebook and
Instagram (cross-posted) with my approval, so I maintain a consistent social presence
without manually writing each post.

**Why this priority**: Extends the LinkedIn-only Silver posting to the Meta platforms used
by most small business owners; completes the social media trifecta.

**Independent Test**: Trigger `post_facebook.run()` in dev-mode; verify
`vault/Pending_Approval/FB_POST_<timestamp>.md` is created; move to `vault/Approved/`;
verify simulation log entry (no real API call in dev-mode).

**Acceptance Scenarios**:

1. **Given** `post_facebook.run()` executes and no Facebook post has been published within
   `frequency_days` days, **When** the skill runs, **Then** a `vault/Pending_Approval/
   FB_POST_<timestamp>.md` file is created with draft text and `platforms: [facebook, instagram]`.
2. **Given** the approval file is in `vault/Approved/`, **When** `dev_mode: false` and
   credentials are set, **Then** the post is published to Facebook Page via `/me/feed`
   and Instagram via `/{ig-user-id}/media_publish`.
3. **Given** the Meta API returns a 429 rate-limit error, **When** the skill retries,
   **Then** `@with_retry` applies exponential back-off (3 attempts, max 60s delay) and
   logs `result: failure` if all retries exhausted.

---

### User Story 4 — Tweet Published with One Approval (Priority: P2)

As a business owner, I want to post a business tweet with a single approval action, so I
can maintain a Twitter presence without switching apps.

**Why this priority**: Twitter/X is a key business visibility channel; Free tier limits
make controlled once-a-day posting the appropriate pattern.

**Independent Test**: Trigger `post_twitter.run()` in dev-mode; verify TWEET approval file
created (<=280 chars); move to Approved; verify simulation log entry.

**Acceptance Scenarios**:

1. **Given** `post_twitter.run()` executes and no tweet has been posted today,
   **When** the skill generates a draft, **Then** a `vault/Pending_Approval/TWEET_
   <timestamp>.md` file of <=280 characters is created.
2. **Given** a tweet has already been posted today (rate_limiter check: 1/day),
   **When** `post_twitter.run()` executes again, **Then** it returns `{skipped: 1}`
   immediately without creating an approval file.
3. **Given** the approval file is moved to `vault/Approved/` and `dev_mode: false`,
   **When** the orchestrator processes it, **Then** the tweet is posted via `POST /2/tweets`
   and the audit log records `action_type: post_tweet, result: success`.

---

### User Story 5 — Transient API Failure Automatically Retried (Priority: P1)

As a business owner, I want the system to automatically recover from temporary network
failures without my intervention, so the AI employee stays productive during API hiccups.

**Why this priority**: Gold tier calls five external APIs (Odoo, Meta, Twitter, Gmail,
Claude). Without retry logic a single timeout would cause cascading task failures.

**Independent Test**: Mock an API call to raise a transient error twice then succeed;
verify `@with_retry` calls the function 3 times total and returns the success result.

**Acceptance Scenarios**:

1. **Given** an external API call raises a transient error on attempts 1 and 2,
   **When** `@with_retry(max_attempts=3)` wraps the call, **Then** the third attempt
   succeeds, the result is returned, and two warning-level log entries are emitted.
2. **Given** all 3 retry attempts fail, **When** `@with_retry` exhausts retries, **Then**
   the exception is re-raised; the calling skill catches it, logs `result: failure`, and
   does not crash the orchestrator.
3. **Given** an AUTH error is raised (expired token), **When** `@with_retry` sees it,
   **Then** it does NOT retry, immediately creates a vault alert Inbox item, and pauses
   the affected watcher.

---

### User Story 6 — Watchdog Restarts Crashed Watcher Thread (Priority: P2)

As a business owner, I want crashed watcher threads to restart automatically, so the AI
employee stays online even after unexpected failures overnight.

**Acceptance Scenarios**:

1. **Given** a watcher daemon thread has stopped unexpectedly, **When** the watchdog checks
   thread health (60s interval), **Then** it restarts the thread and logs
   `action_type: watchdog_restart, result: success`.
2. **Given** a watcher thread fails to restart 3 consecutive times, **When** the watchdog
   exhausts restart attempts, **Then** it creates a `vault/Inbox/WATCHDOG_ALERT_<watcher>_
   <timestamp>.md` item for human review.

---

### User Story 7 — Monday CEO Briefing Includes Financial Data (Priority: P1)

As a business owner, I want my weekly CEO Briefing to include revenue, expenses, and cost
alerts drawn from Odoo, so I start every Monday with a complete financial picture.

**Why this priority**: The Monday Briefing with financial data is the flagship Gold tier
feature that demonstrates full Personal + Business domain unification.

**Independent Test**: Populate `vault/Watch/finance_mock/` with sample transactions; trigger
`weekly_briefing.run()` on a mocked Monday; verify briefing contains all new sections.

**Acceptance Scenarios**:

1. **Given** it is Monday and no briefing exists for today's date, **When**
   `weekly_briefing.run()` executes, **Then** `vault/Briefings/BRIEFING_<YYYY-MM-DD>.md`
   is created with Revenue, Expense, Bottleneck, Proactive Suggestions, and Social Summary
   sections in addition to the existing Silver sections.
2. **Given** Odoo is unavailable during briefing generation, **When**
   `accounting_audit.run()` is called, **Then** Revenue and Expense sections show
   `[Data unavailable — Odoo offline]` and the briefing is still written (degraded output).
3. **Given** a subscription pattern in `config/audit_logic.yaml` matches an expense with no
   Odoo activity in 30 days, **When** the briefing generates, **Then** a Proactive
   Suggestions entry is added: `Flag subscription <name> ($X/mo) — no activity in 30 days`.

---

### User Story 8 — Multi-Step Plan Completes Without Re-Prompting (Priority: P2)

As a business owner, I want the AI to complete multi-step tasks autonomously end-to-end,
so I only need to approve once per task rather than babysit each step.

**Acceptance Scenarios**:

1. **Given** a plan file has `requires_ralph: true` in frontmatter, **When** the
   orchestrator detects it, **Then** `ralph_loop.py` is invoked and drives plan execution
   until `vault/Plans/PLAN_<id>.md` moves to `vault/Done/`.
2. **Given** the Ralph loop has iterated `max_iterations` times without completion,
   **When** the limit is exceeded, **Then** the task file is moved to `vault/Quarantine/`
   with `status: max_iterations_exceeded` and a human-alert Inbox item is created.
3. **Given** the user manually moves the task to `vault/Done/` during a loop, **When**
   the Stop hook checks, **Then** it detects completion and exits cleanly.

---

### User Story 9 — Audit Log Entries Conform to Gold Schema (Priority: P1)

As a compliance-aware business owner, I want every system action logged in a structured,
queryable format, so I can audit what the AI did, when, and whether it was approved.

**Acceptance Scenarios**:

1. **Given** any action executes (email send, invoice create, social post), **When**
   `audit_logger.log()` is called, **Then** the JSON-Lines entry contains all nine required
   fields with no null for mandatory fields.
2. **Given** the current log file is 91 days old, **When** the archival check runs,
   **Then** it is moved to `vault/Logs/Archive/` and a new log file is started.
3. **Given** an existing Silver caller uses the old two-argument `audit_logger.log(action,
   details)` signature, **When** the Gold `audit_logger.py` is deployed, **Then** the call
   succeeds (backwards-compatible wrapper) and all 531 Silver tests still pass.

---

### Edge Cases

- What happens when the Odoo Docker container is not running on first orchestrator start?
  Finance Watcher logs `result: degraded`, uses CSV fallback; briefing shows `[Odoo offline]`;
  human-alert Inbox item created once per degraded session.
- What if a Facebook token expires (60-day limit)?
  `AUTH` error category — `@with_retry` does NOT retry; vault alert item created immediately
  on 401/403; `quickstart.md` documents token refresh procedure.
- What if a Ralph loop task is manually cancelled by moving the file to `vault/Rejected/`?
  Stop hook detects non-Done movement; exits loop; logs `result: cancelled`.
- What if `vault/Accounting/Current_Month.md` does not exist yet?
  Finance Watcher creates it with a heading and an empty table on first run.
- What happens on month rollover?
  Finance Watcher checks the `YYYY-MM` in the filename; creates a new file if the month has
  changed; old file remains in `vault/Accounting/` for CEO Briefing history.
- What if `generate_invoice` cannot parse the client name from an unstructured WhatsApp message?
  Skill creates approval file with `partner: [NEEDS HUMAN INPUT]`; human fills in the field
  before approving; Odoo call proceeds with corrected value.

---

## 3. Functional Requirements

### FR-K — Odoo MCP Server

- **FR-K01**: System MUST expose an Odoo MCP server as a stdio process at
  `src/mcp_servers/odoo_mcp/server.py` using the `mcp` Python SDK.
- **FR-K02**: MCP server MUST implement six tools: `create_invoice`, `list_invoices`,
  `record_expense`, `get_account_balance`, `post_invoice`, `list_transactions`.
- **FR-K03**: All write tools (`create_invoice`, `record_expense`, `post_invoice`) MUST
  create a `vault/Pending_Approval/` file and return `{status: "pending_approval"}` before
  performing any Odoo write; actual Odoo call made only after file moves to `vault/Approved/`.
- **FR-K04**: Read tools (`list_invoices`, `get_account_balance`, `list_transactions`) MUST
  be auto-approved and call Odoo JSON-RPC directly without HITL gate.
- **FR-K05**: MCP server MUST read connection from env vars: `ODOO_URL` (default:
  `http://localhost:8069`), `ODOO_DB` (default: `fte_db`), `ODOO_UID`, `ODOO_PASSWORD`.
  Authentication is **per-call**: each JSON-RPC request to `/web/dataset/call_kw` includes
  `db`, `uid`, and `password` as positional args; no session authentication step is required.
- **FR-K06**: When `dev_mode: true`, all MCP tool calls MUST return mocked responses and
  log `simulated: true`; no real Odoo HTTP calls are made.
- **FR-K07**: A `src/mcp_servers/odoo_mcp/client.py` module MUST expose the same six
  operations as plain Python functions callable from within the orchestrator process.

### FR-L — Finance Watcher

- **FR-L01**: `src/watchers/finance_watcher.py` MUST implement the `BaseWatcher` interface
  with `check_for_updates() -> list` and `create_action_file(item) -> Path`.
- **FR-L02**: Watcher MUST poll Odoo `list_transactions` as primary source every 300s
  (configurable via `settings.yaml` → `odoo.poll_interval_s`).
- **FR-L03**: When Odoo MCP is unreachable, watcher MUST fall back to CSV files in
  `vault/Watch/finance_drop/`; CSV files MUST have a header row and exactly four columns:
  `date,description,amount,account` (amount is a signed decimal; header row is skipped during
  import); dedup using SHA-256 hash of `date + description + amount`.
- **FR-L04**: New transactions MUST be appended to `vault/Accounting/Current_Month.md` as
  a Markdown table row (columns: Date, Description, Amount, Account).
- **FR-L05**: File MUST roll over on month change: new `Accounting/YYYY-MM_transactions.md`
  created; old file kept for CEO Briefing history.
- **FR-L06**: In `dev_mode: true`, watcher MUST read from `vault/Watch/finance_mock/*.json`
  (flat schema: `{"id", "date", "description", "amount", "account"}`).
- **FR-L07**: Processed transaction IDs MUST be persisted in
  `vault/state/finance_processed_ids.json` to survive orchestrator restarts.

### FR-M — Facebook & Instagram Integration

- **FR-M01**: `src/watchers/facebook_watcher.py` MUST poll Meta Graph API
  `/me/posts?fields=message,likes.summary(true),comments.summary(true),created_time`
  every 3600s.
- **FR-M02**: Watcher MUST write engagement summary items to `vault/Inbox/` with
  `type: social_media_engagement`, `source: facebook`.
- **FR-M03**: `src/skills/post_facebook.py` MUST follow `run(vault_root) -> dict` contract;
  self-guard: `enabled` flag + last-post age check via `vault/Logs/` (minimum
  `frequency_days` days, default: 3).
- **FR-M04**: Skill MUST draft post using Claude API; fall back to template text when
  `dev_mode: true` or `ANTHROPIC_API_KEY` absent.
- **FR-M05**: Skill MUST write `vault/Pending_Approval/FB_POST_<timestamp>.md` with
  `risk_level: HIGH`, `requires_approval: true`, `platforms: [facebook, instagram]`.
- **FR-M06**: On approval, skill MUST publish to Facebook Page via `POST /me/feed` and
  cross-post to Instagram via `POST /{ig-user-id}/media` then `POST /{ig-user-id}/media_publish`.
- **FR-M07**: Env vars: `FACEBOOK_PAGE_ID`, `FACEBOOK_ACCESS_TOKEN`, `INSTAGRAM_USER_ID`.
  In `dev_mode: true`, log-only; no real API calls made.

### FR-N — Twitter/X Integration (Free Tier)

- **FR-N01**: `src/watchers/twitter_watcher.py` MUST poll Twitter API v2
  `GET /2/users/:id/tweets?tweet.fields=public_metrics` every 86400s (24h).
- **FR-N02**: Watcher MUST write engagement summary items to `vault/Inbox/` with
  `type: social_media_engagement`, `source: twitter`.
- **FR-N03**: `src/skills/post_twitter.py` MUST follow `run(vault_root) -> dict` contract;
  self-guard: `rate_limiter` check (`post_tweet: 1/day`).
- **FR-N04**: Skill MUST draft tweet content of <=280 characters using Claude API.
- **FR-N05**: Skill MUST write `vault/Pending_Approval/TWEET_<timestamp>.md` with
  `risk_level: HIGH`, `requires_approval: true`, `character_count: <int>`.
- **FR-N06**: On approval, skill MUST post via `POST /2/tweets` using OAuth 1.0a credentials.
- **FR-N07**: Env vars: `TWITTER_BEARER_TOKEN`, `TWITTER_API_KEY`, `TWITTER_API_SECRET`,
  `TWITTER_ACCESS_TOKEN`, `TWITTER_ACCESS_SECRET`, `TWITTER_USER_ID` (static numeric ID
  used as `:id` in `GET /2/users/:id/tweets`). In `dev_mode: true`, log-only.

### FR-O — Ralph Wiggum Autonomous Loop

- **FR-O01**: `src/core/ralph_loop.py` MUST accept `task_file_path` and `prompt` parameters;
  on each iteration start, MUST write `vault/state/ralph_loop_state.json` with keys
  `task_file`, `prompt`, `iteration`, and `status: "running"`; then start a Claude subprocess.
- **FR-O02**: Stop hook `hooks/stop_hook.py` MUST read `vault/state/ralph_loop_state.json` to
  obtain `task_file`; check whether that file has moved to `vault/Done/`; if YES: update
  `status: "done"` and exit 0 (complete); if NO: re-inject prompt and continue iteration.
- **FR-O03**: Max iterations MUST be read from `settings.yaml` → `ralph_loop.max_iterations`
  (default: 10); when exceeded, task file MUST move to `vault/Quarantine/` with
  `status: max_iterations_exceeded`.
- **FR-O04**: Orchestrator MUST detect `requires_ralph: true` in plan frontmatter and
  delegate to `ralph_loop.py` instead of the normal skill execution path.
- **FR-O05**: Stop hook MUST be registered to `.claude/hooks/Stop` by the extended
  `install_schedule.py`; registration MUST be idempotent.
- **FR-O06**: If the task file moves to `vault/Rejected/` during a loop, stop hook MUST
  exit cleanly and log `result: cancelled`.

### FR-P — Error Recovery & Graceful Degradation

- **FR-P01**: `src/core/retry_handler.py` MUST provide `@with_retry(max_attempts=3,
  base_delay=1, max_delay=60)` decorator with exponential back-off and uniform jitter.
- **FR-P02**: `ErrorCategory` enum MUST define: `TRANSIENT` (network timeout, 429 — retry),
  `AUTH` (401/403 — pause + alert, no retry), `LOGIC` (unexpected response — quarantine),
  `DATA` (parse error — quarantine), `SYSTEM` (process crash — watchdog).
- **FR-P03**: Per-component degradation contracts:
  - Odoo MCP unreachable: Finance Watcher uses CSV fallback; briefing shows `[Odoo offline]`
  - Meta API 5xx: skip Facebook/Instagram post this cycle; log `result: degraded`
  - Twitter API 5xx: skip Twitter post this cycle; log `result: degraded`
  - Gmail API down: filesystem watcher continues; outbound emails queued
  - Claude API down: `generate_plan` falls back to Bronze `PLAN_TEMPLATES`
- **FR-P04**: `src/watchers/watchdog.py` MUST monitor all daemon watcher thread objects;
  attempt restart on thread death; after 3 failed restarts, create vault alert Inbox item.
- **FR-P05**: `@with_retry` MUST be applied to all calls in `OdooMCPClient`,
  `FacebookWatcher`, and `TwitterWatcher`.

### FR-Q — Comprehensive Audit Logging (Gold JSON Schema)

- **FR-Q01**: Every `audit_logger.log()` call MUST write a JSON-Lines entry to
  `vault/Logs/YYYY-MM-DD.json` conforming to the Gold schema (9 mandatory fields).
- **FR-Q02**: Schema fields: `timestamp` (ISO8601), `action_type` (str), `actor`
  (`claude_code|orchestrator|watcher:<name>|mcp:<server>`), `target` (str),
  `parameters` (dict), `approval_status` (`auto|approved|rejected|pending`),
  `approved_by` (`human|system|null`), `result` (`success|failure|skipped|degraded`),
  `error` (str or null).
- **FR-Q03**: Existing Silver callers using the old `audit_logger.log(action, details)`
  two-argument signature MUST continue to work via a backwards-compatible wrapper.
- **FR-Q04**: Log files older than 90 days MUST be moved to `vault/Logs/Archive/` on each
  orchestrator startup archival pass.
- **FR-Q05**: `result: degraded` MUST be used when an action completes with reduced
  capability (e.g., briefing written with missing Odoo section).

### FR-R — Enhanced CEO Briefing

- **FR-R01**: `weekly_briefing.py` MUST be minimally extended to call `accounting_audit.run()`
  for Revenue and Expense data; fall back to `[Data unavailable — Odoo offline]` if Odoo
  MCP is unreachable.
- **FR-R02**: Revenue section MUST show: weekly invoices paid, MTD total, MTD vs goal
  (from `vault/Business_Goals.md` `monthly_revenue_target` field).
- **FR-R03**: Expense section MUST show: top 5 expense categories, flagged subscriptions
  matching `SUBSCRIPTION_PATTERNS` in `config/audit_logic.yaml`.
- **FR-R04**: Bottleneck section MUST compare `created_at` to `completed_at` delta for
  `vault/Done/` items from past 7 days against `settings.yaml` SLA threshold.
- **FR-R05**: Proactive suggestions MUST flag unused subscriptions (no Odoo activity > 30
  days) and cost spikes (> 20% increase vs prior month average).
- **FR-R06**: Social Summary MUST aggregate LinkedIn, Facebook, Instagram, Twitter
  engagement totals from `vault/Logs/` for the briefing period.
- **FR-R07**: Self-guard (Monday + file-not-exists) MUST remain unchanged from Silver.

### FR-S — MCP Server Registry

- **FR-S01**: `config/mcp_servers.yaml` MUST list all active MCP servers with fields:
  `name`, `command`, `args`, `transport` (`stdio`), `env_vars`, `health_check_interval_s`.
- **FR-S02**: Orchestrator MUST read this file on startup and attempt to start each server
  via `mcp` Python SDK subprocess client.
- **FR-S03**: If an MCP server fails to start, orchestrator MUST log the failure, create a
  vault alert item, and continue running in degraded mode.

---

## 4. System Architecture

### Gold Data Flow

```
EXTERNAL SOURCES (Gold additions highlighted)
  Gmail(Silver) | WhatsApp(Silver) | Filesystem(Bronze) | Odoo[GOLD] | Facebook[GOLD] | Twitter[GOLD]
          |              |                  |                  |              |               |
          v              v                  v                  v              v               v
PERCEPTION LAYER
  GmailWatcher | WhatsAppWatcher | FilesystemWatcher | FinanceWatcher[GOLD] | FacebookWatcher[GOLD] | TwitterWatcher[GOLD]
                                     Watchdog[GOLD] monitors all daemon threads
          |
          v
OBSIDIAN VAULT
  /Inbox/ /Needs_Action/ /Plans/ /Done/ /Pending_Approval/ /Approved/ /Rejected/
  /Quarantine/ /Briefings/ /Logs/ /Accounting/[GOLD] /Logs/Archive/[GOLD]
          |
          v
REASONING LAYER
  Silver skills (triage_inbox, check_handbook, detect_lead, generate_plan,
                 generate_linkedin_post, plan_task, weekly_briefing*)
  Gold skills:  post_facebook[GOLD] post_twitter[GOLD] generate_invoice[GOLD]
                accounting_audit[GOLD] error_recovery[GOLD]
                (*minimally extended)
          |
    +-----+-----+
    |           |
    v           v
HITL GATE    ACTION LAYER
/Pending     email-mcp(Silver) + odoo-mcp[GOLD]
/Approved    Meta Graph API + Twitter API v2
/Rejected
          |
          v
ORCHESTRATION LAYER
  orchestrator.py(extended) + ralph_loop.py[GOLD] + retry_handler.py[GOLD]
  config/mcp_servers.yaml[GOLD]
```

### Ralph Wiggum Stop Hook Flow

```
Orchestrator detects requires_ralph: true in plan frontmatter
  -> ralph_loop.py: loads {task_file_path, prompt, iteration=0}
  -> Claude subprocess started with prompt
  -> Claude executes plan steps
  -> Claude tries to exit
  -> Stop hook (.claude/hooks/Stop) intercepts:
       Check: task_file_path in vault/Done/?
         YES -> exit 0  (complete)
         NO  -> iteration++; check max_iterations
                  EXCEEDED -> move to Quarantine + alert + exit 0
                  OK       -> re-inject prompt; Claude resumes
```

---

## 5. New Components Map

### Files to Create

| File | Purpose |
|------|---------|
| `docker-compose.odoo.yml` | Odoo 19 + PostgreSQL Docker Compose |
| `src/mcp_servers/__init__.py` | Package marker |
| `src/mcp_servers/odoo_mcp/__init__.py` | Package marker |
| `src/mcp_servers/odoo_mcp/server.py` | stdio MCP server (6 tools) |
| `src/mcp_servers/odoo_mcp/client.py` | Plain Python Odoo JSON-RPC client |
| `src/watchers/finance_watcher.py` | Implements existing stub (Odoo + CSV) |
| `src/watchers/facebook_watcher.py` | Meta Graph API engagement watcher |
| `src/watchers/twitter_watcher.py` | Twitter API v2 timeline metrics watcher |
| `src/watchers/watchdog.py` | Daemon thread health monitor + restarter |
| `src/skills/post_facebook.py` | Facebook + Instagram post drafting + HITL |
| `src/skills/post_twitter.py` | Twitter post drafting + HITL |
| `src/skills/generate_invoice.py` | Invoice request to Odoo draft via HITL |
| `src/skills/accounting_audit.py` | Revenue/expense aggregation sub-skill |
| `src/skills/error_recovery.py` | Component failure handler skill |
| `src/core/retry_handler.py` | @with_retry decorator + ErrorCategory enum |
| `src/core/ralph_loop.py` | Ralph Wiggum loop driver |
| `hooks/stop_hook.py` | Claude Stop hook for Ralph Wiggum |
| `config/mcp_servers.yaml` | MCP server registry |
| `config/audit_logic.yaml` | SUBSCRIPTION_PATTERNS + SLA config |
| `vault/Accounting/.gitkeep` | Accounting folder marker |
| `vault/Logs/Archive/.gitkeep` | Log archive folder marker |
| `vault/Watch/finance_mock/` | Mock finance JSON files (dev-mode) |
| `vault/Watch/facebook_mock/` | Mock Facebook engagement JSON (dev-mode) |
| `vault/Watch/twitter_mock/` | Mock Twitter metrics JSON (dev-mode) |
| `vault/Watch/finance_drop/` | CSV bank export drop folder |
| `tests/test_odoo_mcp.py` | Odoo MCP server + client unit tests |
| `tests/test_finance_watcher.py` | Finance Watcher unit tests |
| `tests/test_facebook_watcher.py` | Facebook Watcher unit tests |
| `tests/test_twitter_watcher.py` | Twitter Watcher unit tests |
| `tests/test_post_facebook.py` | post_facebook skill tests |
| `tests/test_post_twitter.py` | post_twitter skill tests |
| `tests/test_generate_invoice.py` | generate_invoice skill tests |
| `tests/test_accounting_audit.py` | accounting_audit sub-skill tests |
| `tests/test_retry_handler.py` | @with_retry + ErrorCategory tests |
| `tests/test_ralph_loop.py` | Ralph Wiggum loop tests |
| `tests/test_audit_logger_gold.py` | Gold schema validation tests |
| `tests/test_weekly_briefing_gold.py` | Enhanced briefing section tests |
| `tests/test_watchdog.py` | Watchdog restart tests |

### Files to Modify (Minimal Patches Only)

| File | Change | Scope |
|------|--------|-------|
| `src/core/audit_logger.py` | Enforce Gold JSON schema; backwards-compatible wrapper | Additive: new `log_v2()` + wrapper for existing `log()` |
| `src/skills/weekly_briefing.py` | Add Revenue, Expense, Bottleneck, Social Summary | Additive: call `accounting_audit.run()` + social log scan |
| `src/skills/execute_plan.py` | Wire `requires_ralph: true` flag to `ralph_loop.py` | Prepend: check frontmatter flag at plan entry |
| `src/skills/install_schedule.py` | Register Stop hook to `.claude/hooks/Stop` | Additive: write hook script on first run (idempotent) |
| `src/orchestrator.py` | Start new watcher threads + health-check MCP servers | Additive: new daemon thread starts + startup health check |
| `config/settings.yaml` | New Gold stanzas | Additive: `odoo`, `facebook`, `twitter`, `ralph_loop`, `audit`, `sla` stanzas |
| `.env.example` | Add Gold env vars | Additive: `ODOO_*`, `FACEBOOK_*`, `INSTAGRAM_*`, `TWITTER_*` |
| `requirements.txt` | Add Gold dependencies | Additive: `mcp`, `tweepy>=4.14`, `requests>=2.31` |

---

## 6. Skill Interface Contracts

All Gold skills conform to `run(vault_root: str) -> dict` contract (same as Silver).

### post_facebook

```python
def run(vault_root: str) -> dict[str, Any]:
    """
    Draft a Facebook + Instagram cross-post using Claude.
    Self-guards: skills.post_facebook.enabled == true
                 + no audit entry with action:post_facebook in last frequency_days days
    Returns: processed, post_files_created, skipped_rate_limit, errors, skipped
    """
```

- **Reads**: `vault/Business_Goals.md`, `vault/Logs/` (frequency_days scan)
- **Writes**: `vault/Pending_Approval/FB_POST_<timestamp>.md`, `vault/Logs/`
- **Risk**: HIGH (requires_approval: true)
- **Constraints**: Max 2000 chars; must include `#AIAssisted`

### post_twitter

```python
def run(vault_root: str) -> dict[str, Any]:
    """
    Draft a tweet (<=280 chars) using Claude.
    Self-guards: rate_limiter post_tweet: 1/day check
    Returns: processed, tweet_files_created, skipped_rate_limit, errors, skipped
    """
```

- **Reads**: `vault/Business_Goals.md`, `vault/Logs/` (today's post_tweet count)
- **Writes**: `vault/Pending_Approval/TWEET_<timestamp>.md`, `vault/Logs/`
- **Risk**: HIGH (requires_approval: true)
- **Constraints**: <=280 chars; `#AIAssisted` appended if space allows

### generate_invoice

```python
def run(vault_root: str) -> dict[str, Any]:
    """
    Detect invoice intent in vault/Needs_Action/ and create Odoo draft via HITL.
    Intent signals: frontmatter type == 'invoice_request' OR
                    detect_lead-assigned intent == 'invoice'
    Returns: processed, invoices_created, skipped, errors
    """
```

- **Reads**: `vault/Needs_Action/`, `vault/Business_Goals.md`
- **Writes**: `vault/Pending_Approval/INVOICE_<timestamp>.md`, `vault/Logs/`
- **Risk**: HIGH (requires_approval: true before Odoo write)

### accounting_audit

```python
def run(vault_root: str, period_days: int = 7) -> dict[str, Any]:
    """
    Aggregate Revenue and Expense data from Odoo for the specified period.
    Called by weekly_briefing.py as a sub-skill.
    Does NOT write to vault directly; returns structured data dict.
    Returns: revenue_total, revenue_items, expense_total, expense_items,
             subscription_flags, proactive_suggestions, error (when Odoo offline)
    """
```

- **Reads**: Odoo via `odoo_mcp.client.list_invoices()`, `list_transactions()`
- **Writes**: Nothing (data returned to caller)
- **Risk**: LOW (read-only Odoo calls, auto-approved)
- **Degradation**: Returns `{error: "Odoo offline", revenue_total: None, ...}`

### error_recovery

```python
def run(vault_root: str) -> dict[str, Any]:
    """
    Handle component failure events in vault/Inbox/ with type: system_error.
    Classifies error, attempts recovery action, logs outcome.
    Returns: processed, recovered, escalated, errors
    """
```

- **Reads**: `vault/Inbox/` items with `type: system_error`
- **Writes**: `vault/Inbox/` (escalation items), `vault/Logs/`
- **Risk**: LOW (no external actions without HITL)

### OdooMCPClient (src/mcp_servers/odoo_mcp/client.py)

```python
class OdooMCPClient:
    def __init__(self, url: str, db: str, uid: int, password: str): ...

    @with_retry(max_attempts=3)
    def list_invoices(self, state: str = "open") -> list[dict]: ...

    @with_retry(max_attempts=3)
    def list_transactions(self, date_from: str, date_to: str) -> list[dict]: ...

    @with_retry(max_attempts=3)
    def get_account_balance(self, account_code: str) -> dict: ...

    def create_invoice(self, partner: str, amount: float,
                       description: str, currency: str = "USD") -> dict:
        """Returns {status: 'pending_approval', approval_file: str}"""

    def record_expense(self, vendor: str, amount: float,
                       category: str, date: str) -> dict:
        """Returns {status: 'pending_approval', approval_file: str}"""

    def post_invoice(self, invoice_id: int) -> dict:
        """Returns {status: 'pending_approval', approval_file: str}"""
```

---

## 7. Config Changes

### settings.yaml New Stanzas (append after Silver stanzas)

```yaml
odoo:
  url: "${ODOO_URL:-http://localhost:8069}"
  db: "${ODOO_DB:-fte_db}"
  uid: "${ODOO_UID:-2}"
  poll_interval_s: 300

facebook:
  enabled: false
  poll_interval_s: 3600
  frequency_days: 3

twitter:
  enabled: false
  poll_interval_s: 86400
  frequency_days: 1

ralph_loop:
  max_iterations: 10
  state_file: "vault/state/ralph_loop_state.json"

audit:
  retention_days: 90
  archive_dir: "vault/Logs/Archive"

sla:
  task_hours_warning: 48
  subscription_inactive_days: 30

skills:
  post_facebook:
    enabled: false
    frequency_days: 3
  post_twitter:
    enabled: false
    frequency_days: 1
  generate_invoice:
    enabled: true
  accounting_audit:
    enabled: true
  error_recovery:
    enabled: true
```

### .env.example New Variables

```bash
# Gold Tier — Odoo MCP
ODOO_URL=http://localhost:8069
ODOO_DB=fte_db
ODOO_UID=2
ODOO_PASSWORD=admin

# Gold Tier — Meta (Facebook + Instagram)
FACEBOOK_PAGE_ID=your_page_id
FACEBOOK_ACCESS_TOKEN=your_long_lived_page_token
INSTAGRAM_USER_ID=your_ig_user_id

# Gold Tier — Twitter/X (Free Tier)
TWITTER_USER_ID=your_numeric_user_id
TWITTER_BEARER_TOKEN=your_bearer_token
TWITTER_API_KEY=your_api_key
TWITTER_API_SECRET=your_api_secret
TWITTER_ACCESS_TOKEN=your_access_token
TWITTER_ACCESS_SECRET=your_access_secret
```

---

## 8. Vault Changes

### New Folders

```
vault/
├── Accounting/                        # Finance Watcher output [NEW]
│   └── Current_Month.md               # Created on first Finance Watcher run
├── Logs/
│   └── Archive/                       # Audit log files >90 days old [NEW]
├── Watch/
│   ├── finance_mock/                  # Mock JSON for Finance Watcher dev-mode [NEW]
│   ├── facebook_mock/                 # Mock JSON for Facebook Watcher dev-mode [NEW]
│   ├── twitter_mock/                  # Mock JSON for Twitter Watcher dev-mode [NEW]
│   └── finance_drop/                  # CSV bank export drop folder [NEW]
└── state/
    ├── finance_processed_ids.json     # Finance Watcher dedup state [NEW]
    └── ralph_loop_state.json          # Ralph Wiggum loop state [NEW]
```

### vault/Accounting/Current_Month.md Template

```markdown
---
month: YYYY-MM
last_updated: ISO8601
source: odoo | csv_fallback | mock
---

# Transactions — YYYY-MM

| Date       | Description          | Amount    | Account               |
|------------|----------------------|-----------|-----------------------|
```

---

## 9. Success Criteria

| SC     | Criterion |
|--------|-----------|
| SC-021 | Finance Watcher writes Odoo (or CSV fallback) transactions to `vault/Accounting/Current_Month.md` within one poll cycle in dev-mode |
| SC-022 | Facebook post drafted by Claude, written to `vault/Pending_Approval/`, published on approval (simulated in dev-mode) |
| SC-023 | Instagram Business Account receives cross-post alongside every approved Facebook post |
| SC-024 | Twitter/X tweet drafted (<=280 chars), written to `vault/Pending_Approval/`, posted on approval (simulated in dev-mode); rate: max 1/day |
| SC-025 | Odoo `create_invoice` creates a draft invoice via JSON-RPC on approval (simulated in dev-mode) |
| SC-026 | Monday CEO Briefing contains all Silver sections plus Revenue, Expense, Bottleneck, Proactive Suggestions, and Social Summary |
| SC-027 | `@with_retry` decorator recovers a transient failure within 3 attempts with exponential back-off; verified by unit test with mock |
| SC-028 | Ralph Wiggum loop drives a multi-step plan to `vault/Done/` without human re-prompting; Stop hook exits cleanly on file-movement detection |
| SC-029 | All audit log entries written by Gold code conform to the 9-field Gold JSON schema; schema validation passes in `test_audit_logger_gold.py` |
| SC-030 | All 531 Silver tests + 385 Bronze tests pass after Gold implementation (zero regressions) |

---

## 10. Out of Scope

- **Platinum Tier** cloud deployment (24/7 VM, Git/Syncthing vault sync)
- **A2A (Agent-to-Agent)** direct messaging between agents
- **Banking direct API** (open banking, Plaid, Stripe) — Odoo is the finance source of truth
- **Real-time WebSocket streams** — polling-only watchers in Gold
- **WhatsApp Business API** (Twilio) — already resolved as Playwright in Silver
- **Paid social scheduling platforms** (Buffer, Hootsuite)
- **Multi-currency Odoo support** — single currency (USD default)
- **Facebook/Instagram Stories or Reels** — Page Feed posts only
- **Twitter/X media attachments** — text-only tweets (Free tier)
- **Circuit breaker pattern** — `@with_retry` + degradation sufficient for Gold; circuit
  breakers deferred to Platinum

---

## 11. Risks & Mitigations

| Risk | Likelihood | Blast Radius | Mitigation |
|------|-----------|-------------|------------|
| **Odoo Docker complexity** — first-time Odoo setup non-trivial; container networking, admin password, module install can trip users | HIGH | Finance Watcher + CEO Briefing unusable without Odoo | `docker-compose.odoo.yml` with pre-configured env; `quickstart.md` step-by-step setup; full dev-mode CSV fallback means all other Gold features work without Odoo |
| **Meta token expiry** — long-lived Page tokens expire after ~60 days; silent expiry causes AUTH errors | MEDIUM | Facebook/Instagram go dark | `AUTH` error category does NOT retry; vault alert on 401/403; `quickstart.md` documents token refresh procedure |
| **Twitter Free tier quota** — strict monthly caps; over-posting exhausts quota mid-month | MEDIUM | Twitter disabled until month reset | `rate_limiter.py` enforces 1 tweet/day hard cap; briefing warns when >80% of monthly quota consumed |
| **Ralph Wiggum infinite loop** — poorly written plan or Claude reasoning failure causes endless iteration | LOW | CPU/API cost spike; plan stuck | `max_iterations` hard cap (default: 10) with quarantine on overflow; stop hook uses file-movement detection (not Claude output) |

---

## 12. Project Structure

```
fte-employe/
├── docker-compose.odoo.yml            # NEW
├── CLAUDE.md
├── AGENTS.md
├── .env.example                       # EXTENDED
├── requirements.txt                   # EXTENDED
├── config/
│   ├── settings.yaml                  # EXTENDED
│   ├── mcp_servers.yaml               # NEW
│   └── audit_logic.yaml               # NEW
├── hooks/
│   └── stop_hook.py                   # NEW
├── src/
│   ├── orchestrator.py                # EXTENDED
│   ├── core/
│   │   ├── vault.py                   # unchanged
│   │   ├── frontmatter.py             # unchanged
│   │   ├── approval.py                # unchanged
│   │   ├── audit_logger.py            # EXTENDED (Gold schema)
│   │   ├── idempotency.py             # unchanged
│   │   ├── rate_limiter.py            # unchanged
│   │   ├── opt_out.py                 # unchanged
│   │   ├── retry_handler.py           # NEW
│   │   └── ralph_loop.py              # NEW
│   ├── watchers/
│   │   ├── base_watcher.py            # unchanged
│   │   ├── filesystem_watcher.py      # unchanged
│   │   ├── gmail_watcher.py           # unchanged
│   │   ├── gmail_auth.py              # unchanged
│   │   ├── whatsapp_watcher.py        # unchanged
│   │   ├── linkedin_watcher.py        # unchanged
│   │   ├── finance_watcher.py         # IMPLEMENTED (was stub)
│   │   ├── facebook_watcher.py        # NEW
│   │   ├── twitter_watcher.py         # NEW
│   │   └── watchdog.py                # NEW
│   ├── skills/
│   │   ├── triage_inbox.py            # unchanged
│   │   ├── check_handbook.py          # unchanged
│   │   ├── plan_task.py               # unchanged
│   │   ├── execute_plan.py            # EXTENDED (requires_ralph flag)
│   │   ├── update_dashboard.py        # unchanged
│   │   ├── detect_lead.py             # unchanged
│   │   ├── generate_plan.py           # unchanged
│   │   ├── generate_linkedin_post.py  # unchanged
│   │   ├── weekly_briefing.py         # EXTENDED (5 new sections)
│   │   ├── install_schedule.py        # EXTENDED (Stop hook registration)
│   │   ├── uninstall_schedule.py      # unchanged
│   │   ├── post_facebook.py           # NEW
│   │   ├── post_twitter.py            # NEW
│   │   ├── generate_invoice.py        # NEW
│   │   ├── accounting_audit.py        # NEW
│   │   └── error_recovery.py          # NEW
│   ├── actions/
│   │   └── action_executor.py         # unchanged
│   └── mcp_servers/
│       └── odoo_mcp/
│           ├── __init__.py            # NEW
│           ├── server.py              # NEW
│           └── client.py             # NEW
├── specs/
│   ├── 001-bronze-tier/               # complete
│   ├── 002-silver-tier/               # complete
│   └── 003-gold-tier/                 # THIS SPEC
├── tests/
│   ├── [385 Bronze tests — unchanged]
│   ├── [146 Silver tests — unchanged]
│   └── [~120 Gold tests — new, TDD red-first]
└── vault/
    ├── Accounting/                    # NEW
    ├── Logs/Archive/                  # NEW
    └── Watch/
        ├── finance_mock/              # NEW
        ├── facebook_mock/             # NEW
        ├── twitter_mock/              # NEW
        └── finance_drop/              # NEW
```

---

## 13. Constitution Traceability

| Gold Capability | Constitution Section | Success Criterion |
|-----------------|----------------------|-------------------|
| Odoo MCP Server (G2) | S4.3 Gold Layer 1 — Business accounting integration | SC-025 |
| Finance Watcher (G3) | S4.3 Gold Layer 2 — Finance perception | SC-021 |
| Facebook/Instagram (G4) | S4.3 Gold Layer 3 — Multi-platform social | SC-022, SC-023 |
| Twitter/X (G5) | S4.3 Gold Layer 3 — Multi-platform social | SC-024 |
| Enhanced CEO Briefing (G7) | S4.3 Gold Layer 4 — Business audit | SC-026 |
| Error Recovery (G8) | S5.2 Reliability — Resilience + graceful degradation | SC-027 |
| Gold Audit Logging (G9) | S6.1 Compliance — Structured audit trail | SC-029 |
| Ralph Wiggum Loop (G10) | S4.3 Gold Layer 5 — Autonomous completion | SC-028 |
| Silver Regression Guard | S3.1 Tier Inheritance — Cumulative, no regressions | SC-030 |
| HITL Gates on all writes | S2.2 Safety before autonomy | SC-022, SC-023, SC-024, SC-025 |
| dev_mode on all new watchers | S2.1 Augment, never replace | SC-021 through SC-026 |
