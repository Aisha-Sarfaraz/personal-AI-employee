# Tasks: Gold Tier — Autonomous AI Employee (003-gold-tier)

**Input**: Design documents from `specs/003-gold-tier/`
**Prerequisites**: plan.md ✅ spec.md ✅ research.md ✅ data-model.md ✅ contracts/ ✅ quickstart.md ✅
**Branch**: `003-gold-tier`
**TDD Mandate**: Tests MUST be written RED (failing) before implementation (GREEN). All test tasks must fail before their paired implementation task begins.
**Invariant**: All 531 Silver + 385 Bronze tests must remain green throughout. Run `pytest tests/ -k "not gold" -q` at the start of each phase.
**Target**: 531 Silver + 385 Bronze + ~120 Gold = ~1,036 total tests; ≥70% coverage on `src/`

---

## Format: `[ID] [P?] [US?] Description with file path`

- **[P]**: Parallelizable (different files, no incomplete-task dependencies)
- **[US]**: User story label (US1–US9 from spec.md)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Vault folder structure, mock fixtures, Docker config, YAML configs, and env vars that all Gold components depend on. No Python code.

- [X] T001 Create vault folder extensions: `vault/Accounting/.gitkeep`, `vault/Watch/finance_mock/.gitkeep`, `vault/Watch/finance_drop/.gitkeep`, `vault/Watch/facebook_mock/.gitkeep`, `vault/Watch/twitter_mock/.gitkeep`, `vault/Logs/Archive/.gitkeep`
- [X] T002 [P] Create `vault/Watch/finance_mock/sample_transactions.json` with 3 mock transaction objects matching schema `{"id","date","description","amount","account"}` per `contracts/finance_watcher.md`
- [X] T003 [P] Create `vault/Watch/facebook_mock/sample_post.json` with 2 mock engagement objects matching schema `{"id","text","likes","comments","reach","created_at"}` per `contracts/social_skills.md`
- [X] T004 [P] Create `vault/Watch/twitter_mock/sample_tweet.json` with 2 mock tweet objects matching schema `{"id","text","retweet_count","like_count","reply_count","created_at"}` per `contracts/social_skills.md`
- [X] T005 [P] Create `docker-compose.odoo.yml` with `odoo:19.0` + `postgres:16` services; port 8069; internal DB network; bind-mount `config/odoo/odoo.conf`; create `config/odoo/odoo.conf` with `db_host=db`, `db_port=5432`
- [X] T006 [P] Create `config/mcp_servers.yaml` with `email-mcp` and `odoo-mcp` entries; fields: `name`, `command`, `args`, `transport: stdio`, `env_vars`, `health_check_interval_s: 60` per `contracts/odoo_mcp_tools.md` FR-S01
- [X] T007 [P] Create `config/audit_logic.yaml` with `SUBSCRIPTION_PATTERNS` list (e.g. `["subscription", "monthly fee", "saas", "recurring"]`) for CEO Briefing subscription detection per FR-R03
- [X] T008 Patch `config/settings.yaml` — append Gold stanzas: `odoo` (url, db, poll_interval_s: 300), `facebook` (enabled: false, frequency_days: 3), `twitter` (enabled: false, tweets_per_day: 1), `ralph_loop` (max_iterations: 10), `audit` (retention_days: 90, archive_dir), `sla` (task_completion_hours: 48)
- [X] T009 [P] Patch `.env.example` — append Gold env vars: `ODOO_URL`, `ODOO_DB`, `ODOO_UID`, `ODOO_PASSWORD`, `FACEBOOK_PAGE_ID`, `FACEBOOK_ACCESS_TOKEN`, `INSTAGRAM_USER_ID`, `TWITTER_BEARER_TOKEN`, `TWITTER_API_KEY`, `TWITTER_API_SECRET`, `TWITTER_ACCESS_TOKEN`, `TWITTER_ACCESS_SECRET`, `TWITTER_USER_ID`
- [X] T010 [P] Add `tweepy>=4.14` and `pytest-asyncio>=0.23` to `requirements.txt`; add `mcp_servers/` package stubs: `src/mcp_servers/__init__.py`, `src/mcp_servers/odoo_mcp/__init__.py`

**Checkpoint**: Setup complete — all config files present; `python -m pytest tests/ -k "not gold" -q` passes (no Python changes yet)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that ALL user stories depend on — `@with_retry`, Gold audit logging, and the Odoo MCP client/server. These must be complete before any user story phase begins.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

> **TDD RED RULE**: Write each test task first; confirm it FAILS before coding the paired implementation task.

### Error Recovery Foundation (US5 dependency)

- [X] T011 Write `tests/unit/test_retry_handler.py` RED — 8 failing tests: retry succeeds on 3rd attempt, all 3 fail re-raises, AUTH error no retry, LOGIC error no retry, jitter produces non-negative delay, max_delay cap respected, warning logged on each retry, decorated function signature preserved; run `pytest tests/unit/test_retry_handler.py -q` and confirm 8 failures
- [X] T012 Implement `src/core/retry_handler.py` — `ErrorCategory` enum (TRANSIENT, AUTH, LOGIC, DATA, SYSTEM); `@with_retry(max_attempts=3, base_delay=1.0, max_delay=60.0)` decorator; exponential back-off formula `min(base * 2**n, max) + uniform(0, 0.5)`; AUTH/LOGIC/DATA raise immediately; emit `logging.warning` on each retry; run `pytest tests/unit/test_retry_handler.py -q` and confirm 8 PASS

### Gold Audit Logging Foundation (US9 dependency)

- [X] T013 Write `tests/unit/test_audit_logger_gold.py` RED — 10 failing tests: JSON-Lines entry written to `vault/Logs/YYYY-MM-DD.json`, all 9 mandatory fields present, no null for mandatory fields, `result: degraded` accepted, old `log_action(vault_root, agent, action, risk_tier, status)` call succeeds, `log_action` produces valid JSON-Lines entry, archive moves file older than 90 days, archive skips recent file, ValueError on missing mandatory field, concurrent writes don't corrupt file; confirm 10 failures
- [X] T014 Patch `src/core/audit_logger.py` — add `log(action_type, actor, target, parameters, approval_status, approved_by, result, error, vault_root)` method; write JSON-Lines to `vault/Logs/YYYY-MM-DD.json`; add backward-compatible `log_action(vault_root, agent, action, risk_tier, status, **kwargs)` wrapper mapping to `log()`; add `archive_old_logs(vault_root, retention_days=90)` moving files > 90 days to `vault/Logs/Archive/`; run `pytest tests/unit/test_audit_logger_gold.py -q` and confirm 10 PASS; run `pytest tests/ -k "not gold" -q` and confirm no regressions

### Odoo MCP Foundation (US1, US2 dependency)

- [X] T015 Write `tests/unit/test_odoo_mcp_client.py` RED — 14 failing tests: `list_transactions(dev_mode=True)` returns mock list, `create_invoice` returns `{status: pending_approval, approval_file: ...}`, approval file YAML contains all required fields, `list_invoices(dev_mode=True)` returns mock list, `get_account_balance(dev_mode=True)` returns balance dict, `record_expense` creates approval file, `post_invoice` creates approval file, `list_transactions` raises `ConnectionError` on bad URL (non-dev), `execute_kw` uses per-call auth (db/uid/pwd in body), `@with_retry` applied (TRANSIENT retries, AUTH does not), dev_mode logs `simulated: true`, all 6 methods exist and callable, `OdooMCPClient.__init__` reads from env vars, `create_invoice` validates required fields; confirm 14 failures
- [X] T016 Implement `src/mcp_servers/odoo_mcp/client.py` — `OdooMCPClient(url, db, uid, password, dev_mode=False)`; `_execute_kw(model, method, args, kwargs)` with per-call JSON-RPC auth per `contracts/odoo_mcp_tools.md` pattern; all 6 public methods: `create_invoice`, `list_invoices`, `record_expense`, `get_account_balance`, `post_invoice`, `list_transactions`; write tool HITL: create approval file, return `{status: pending_approval}`; `@with_retry` on `_execute_kw`; dev_mode: return mocked dicts; run `pytest tests/unit/test_odoo_mcp_client.py -q` and confirm 14 PASS
- [X] T017 [P] Write `tests/unit/test_odoo_mcp_server.py` RED — 6 failing async tests (`@pytest.mark.asyncio`): `list_tools()` returns 6 Tool objects, `call_tool("create_invoice", {...})` returns TextContent with JSON, `call_tool("list_transactions", {...})` returns TextContent, `call_tool("list_invoices", {...})` returns TextContent, `call_tool("unknown_tool", {})` raises ValueError, all tool inputSchemas are valid dicts; confirm 6 failures
- [X] T018 [P] Implement `src/mcp_servers/odoo_mcp/server.py` — `mcp.server.Server("odoo-mcp")`; `@server.list_tools()` returning 6 `Tool` objects with inputSchema; `@server.call_tool()` delegating to `OdooMCPClient` methods; `TextContent(type="text", text=json.dumps(result))` return format; `anyio.run(main)` stdio entry point; run `pytest tests/unit/test_odoo_mcp_server.py -q` and confirm 6 PASS

**Checkpoint**: Foundational phase complete — `pytest tests/unit/ -k "gold" -q` shows 38 PASS; `pytest tests/ -k "not gold" -q` still green

---

## Phase 3: User Story 1 — Finance Transactions Automatically Logged (P1) 🎯 MVP

**Goal**: Finance Watcher polls Odoo (or CSV fallback) and appends new transactions to `vault/Accounting/Current_Month.md` every 300s.

**Independent Test**: Set `DEV_MODE=true`; place mock JSON in `vault/Watch/finance_mock/`; run `python -m src.orchestrator` for 30s; verify `vault/Accounting/Current_Month.md` created with correct table rows.

- [X] T019 Write `tests/unit/test_finance_watcher.py` [US1] RED — 15 failing tests: `check_for_updates(dev_mode=True)` returns list of FinanceTransaction dicts, Odoo path calls `OdooMCPClient.list_transactions`, CSV path parses 4-column CSV with header skip, dedup skips already-processed IDs, `_make_item_id` returns Odoo move_line_id str for Odoo source, `_make_item_id` returns SHA-256[:16] for CSV source, `create_action_file` creates `vault/Accounting/Current_Month.md` if absent, new transaction appended as Markdown table row, existing rows not duplicated, `finance_processed_ids.json` updated after processing, month rollover creates `YYYY-MM_transactions.md`, month rollover creates new `Current_Month.md`, Odoo unreachable falls back to CSV, CSV fallback logs `result: degraded`, dev_mode reads from finance_mock folder; confirm 15 failures
- [X] T020 [US1] Implement `src/watchers/finance_watcher.py` — replace `NotImplementedError` stub; `FinanceWatcher(BaseWatcher)` with `POLL_INTERVAL_S = 300`; `check_for_updates()`: try `OdooMCPClient.list_transactions()` first; on `ConnectionError` fall back to CSV; in dev_mode read `vault/Watch/finance_mock/*.json`; `_make_item_id()` per data-model.md spec; `create_action_file()`: append `| date | description | +/-amount | account |` row to `vault/Accounting/Current_Month.md`; create file with heading + table header if absent; `_check_month_rollover()`; persist processed IDs to `vault/state/finance_processed_ids.json`; `@with_retry` on Odoo calls; run `pytest tests/unit/test_finance_watcher.py -q` and confirm 15 PASS
- [X] T021 [P] [US1] Write `tests/integration/test_sc021_finance_mock_ingestion.py` RED — SC-021 scenario: given dev_mode=True and mock JSON in finance_mock, FinanceWatcher.check_for_updates() creates Current_Month.md with correct rows; confirm FAIL then PASS after T020
- [X] T022 [P] [US1] Write `tests/integration/test_sc022_csv_fallback.py` RED — SC-022 scenario: given Odoo connection refused (mocked), FinanceWatcher uses CSV from finance_drop; audit entry has `result: degraded`; confirm FAIL then PASS after T020
- [X] T023 [P] [US1] Write `tests/integration/test_sc032_month_rollover.py` RED — SC-032 scenario: given existing Current_Month.md with prior month heading, on first new transaction of new month, old file archived to YYYY-MM_transactions.md and new Current_Month.md created; confirm FAIL then PASS after T020

**Checkpoint**: US1 complete — `pytest tests/ -k "sc021 or sc022 or sc032 or finance" -q` all PASS; `Current_Month.md` created in tmp vault during test; Bronze+Silver unchanged

---

## Phase 4: User Story 2 — Invoice Created from WhatsApp/Email Request (P1)

**Goal**: `generate_invoice.py` reads `intent: invoice_request` items from `vault/Needs_Action/`, calls `OdooMCPClient.create_invoice`, creates HITL approval file in `vault/Pending_Approval/`.

**Independent Test**: Create `vault/Needs_Action/WHATSAPP_invoice_request.md` with `intent: invoice_request`; run `generate_invoice.run(vault_root)` in dev_mode; verify `vault/Pending_Approval/INVOICE_<ts>.md` created with correct YAML frontmatter.

- [X] T024 Write `tests/unit/test_generate_invoice.py` [US2] RED — 8 failing tests: `run(vault_root)` returns `{created: 1, approval_file: ...}`, approval file exists at returned path, approval frontmatter has `type: invoice_request`, approval frontmatter has `partner`, `amount`, `description`, `risk_level: HIGH`, unparseable partner sets `partner: [NEEDS HUMAN INPUT]`, idempotency: same item not processed twice (idempotency.py check), dev_mode returns `{simulated: 1}`, no real Odoo HTTP call in dev_mode; confirm 8 failures
- [X] T025 [US2] Implement `src/skills/generate_invoice.py` — `run(vault_root) -> dict`; scan `vault/Needs_Action/` for items with `intent: invoice_request` and not in processed set; parse partner/amount/description from frontmatter or body (use regex; fallback to `[NEEDS HUMAN INPUT]`); call `OdooMCPClient(dev_mode=...).create_invoice(partner, amount, description)`; client returns approval_file path; use `idempotency.mark_processed`; audit log `action_type: generate_invoice`; run `pytest tests/unit/test_generate_invoice.py -q` and confirm 8 PASS
- [X] T026 [US2] Write + run `tests/integration/test_sc023_invoice_approval_flow.py` — SC-023 scenario: given WhatsApp item with `intent: invoice_request` in Needs_Action, `generate_invoice.run()` creates approval file; given approval file moved to Approved (dev_mode), Odoo call simulated, audit records `simulated: true`; both sub-scenarios pass

**Checkpoint**: US2 complete — `pytest tests/ -k "generate_invoice or sc023" -q` all PASS; approval file YAML validated; Bronze+Silver unchanged

---

## Phase 5: User Story 7 — Monday CEO Briefing Includes Financial Data (P1)

**Goal**: `weekly_briefing.py` extended with Revenue, Expense, Bottleneck, Proactive Suggestions, and Social Summary sections powered by Odoo data via `accounting_audit.py`.

**Independent Test**: Populate `vault/Watch/finance_mock/`; run `weekly_briefing.run(vault_root, force=True)` on mocked Monday; verify briefing Markdown contains all 5 new section headings.

- [X] T027 Write `tests/unit/test_accounting_audit.py` [US7] RED — 8 failing tests: `run(vault_root)` returns dict with `revenue`, `expenses`, `suggestions` keys, `revenue.weekly_paid` is a number (from mocked list_invoices), `expenses.top_categories` is a list, subscription in expenses matching SUBSCRIPTION_PATTERNS flagged in suggestions, cost spike > 20% triggers suggestion, `run()` on Odoo ConnectionError returns `{revenue: None, expenses: None, error: "Odoo offline"}`, `run()` returns `{degraded: True}` on error, all numeric fields are float not string; confirm 8 failures
- [X] T028 [US7] Implement `src/skills/accounting_audit.py` — `run(vault_root) -> dict`; read Odoo data via `OdooMCPClient.list_invoices(state="posted")` and `list_transactions()`; calculate `revenue.weekly_paid`, `revenue.mtd_total`, `revenue.mtd_vs_goal` (from `vault/Business_Goals.md` `monthly_revenue_target`); calculate `expenses.top_categories` (5 categories by total spend), `expenses.flagged_subscriptions` (matches `audit_logic.yaml` patterns); calculate `suggestions` (no Odoo activity > 30 days, cost spike > 20%); on `ConnectionError` return degraded dict; run `pytest tests/unit/test_accounting_audit.py -q` and confirm 8 PASS
- [X] T029 [P] Write `tests/unit/test_weekly_briefing_gold.py` [US7] RED — 10 failing tests: briefing output contains `## Revenue` section, briefing contains `## Expenses` section, briefing contains `## Bottleneck` section, briefing contains `## Proactive Suggestions` section, briefing contains `## Social Summary` section, Revenue section shows MTD total, Expense section shows top-5 categories, Odoo offline shows `[Data unavailable — Odoo offline]` in Revenue + Expense sections, Bottleneck section computes SLA delta for vault/Done items, Social Summary aggregates LinkedIn + Facebook + Twitter counts from vault/Logs; confirm 10 failures
- [X] T030 [US7] Patch `src/skills/weekly_briefing.py` — add `accounting_audit.run()` call; append 5 new sections to briefing Markdown: `## Revenue`, `## Expenses`, `## Bottleneck`, `## Proactive Suggestions`, `## Social Summary`; degradation: show `[Data unavailable — Odoo offline]` when accounting_audit returns error; Bottleneck: compare `created_at` vs `completed_at` in vault/Done/ items for past 7 days vs `sla.task_completion_hours`; Social Summary: read `vault/Logs/*.json` for `action_type` in `[post_facebook, post_twitter, post_linkedin]`; self-guard (Monday + file-not-exists) UNCHANGED; run `pytest tests/unit/test_weekly_briefing_gold.py -q` and confirm 10 PASS; run `pytest tests/ -k "briefing" -q` and confirm no Silver regressions
- [X] T031 [US7] Write + run `tests/integration/test_sc028_ceo_briefing_with_finance.py` — SC-028 scenario: given dev_mode + finance_mock populated + mocked Monday, `weekly_briefing.run()` produces briefing with all 5 new sections; given Odoo offline, briefing still written with degraded sections; both sub-scenarios pass

**Checkpoint**: US7 complete — `pytest tests/ -k "accounting_audit or sc028 or briefing" -q` all PASS; briefing Markdown validated; Bronze+Silver unchanged

---

## Phase 6: User Story 5 — Transient API Failure Automatically Retried (P1)

**Purpose**: Validate `@with_retry` integration across all external API callers. The decorator was implemented in Phase 2 (T011/T012); this phase adds integration-level tests and per-component degradation validation.

**Independent Test**: Mock an API call to raise `requests.Timeout` twice then succeed; verify `@with_retry(max_attempts=3)` calls function 3 times total; verify two `logging.WARNING` entries emitted.

- [X] T032 Write + run `tests/integration/test_sc026_retry_handler.py` [US5] — SC-026 scenario: mock raises TRANSIENT error on attempts 1 and 2, succeeds on 3; verify call count = 3 and result returned; mock all 3 fail; verify exception re-raised; mock AUTH error; verify no retry, exception raised immediately; all 3 sub-scenarios pass

**Checkpoint**: US5 integration validated — `pytest tests/ -k "sc026 or retry" -q` all PASS

---

## Phase 7: User Story 9 — Audit Log Entries Conform to Gold Schema (P1)

**Purpose**: Validate Gold JSON-Lines schema integration end-to-end. Core implementation was in Phase 2 (T013/T014); this phase adds schema integration tests and backward-compatibility verification.

**Independent Test**: Trigger any action (email send mock); inspect `vault/Logs/YYYY-MM-DD.json`; validate all 9 mandatory fields present in each line using `json.loads()`.

- [X] T033 Write + run `tests/integration/test_sc030_audit_log_schema.py` [US9] — SC-030 scenario: trigger `audit_logger.log()` for action_types: `post_tweet`, `create_invoice`, `watchdog_restart`; read resulting JSON-Lines file; assert each entry has all 9 fields (`timestamp`, `action_type`, `actor`, `target`, `parameters`, `approval_status`, `approved_by`, `result`, `error`); assert no null for mandatory fields; assert `result: degraded` accepted; pass
- [X] T034 [P] Write + run `tests/integration/test_sc031_audit_backward_compat.py` [US9] — SC-031 scenario: call `audit_logger.log_action(vault_root, "orchestrator", "test_action", "LOW", "success")`; verify call succeeds (no exception); verify JSON-Lines entry written; verify all 531 Silver tests still pass (run `pytest tests/ -k "silver" -q`); pass

**Checkpoint**: US9 integration validated — `pytest tests/ -k "sc030 or sc031 or audit" -q` all PASS

---

## Phase 8: User Story 3 — Facebook & Instagram Post Published (P2)

**Goal**: `FacebookWatcher` reads Page engagement via Meta Graph API; `post_facebook.py` drafts FB+IG cross-post, writes HITL approval file, publishes on approval.

**Independent Test**: Run `post_facebook.run(vault_root)` in dev_mode with `facebook.enabled: true`; verify `vault/Pending_Approval/FB_POST_<ts>.md` created with `platforms: [facebook, instagram]`; move to Approved; verify simulation log entry.

- [X] T035 Write `tests/unit/test_facebook_watcher.py` [P] [US3] RED — 8 failing tests: `check_for_updates(dev_mode=True)` reads facebook_mock, returns list with `id`, `text`, `likes`, `comments`, `reach`, `created_at` keys, dedup skips already-processed post IDs, `create_action_file` writes `vault/Inbox/FB_ENGAGEMENT_<id>_<ts>.md`, frontmatter has `type: social_media_engagement, source: facebook`, `@with_retry` applied to Meta API call (mock TRANSIENT: retries), 401 from Meta API sets watcher status `stopped`, dev_mode does not call `requests.get`; confirm 8 failures
- [X] T036 [P] [US3] Implement `src/watchers/facebook_watcher.py` — `FacebookWatcher(BaseWatcher)` with `POLL_INTERVAL_S = 3600`; `check_for_updates()`: in dev_mode read `vault/Watch/facebook_mock/sample_post.json`; live: `GET /v20.0/me/posts?fields=message,likes.summary(true),comments.summary(true),created_time` with `Authorization: Bearer {FACEBOOK_ACCESS_TOKEN}`; `create_action_file()`: `vault/Inbox/FB_ENGAGEMENT_<id>_<ts>.md`; `@with_retry` on requests calls; AUTH (401/403): log error, set `_paused=True`; run `pytest tests/unit/test_facebook_watcher.py -q` and confirm 8 PASS
- [X] T037 Write `tests/unit/test_post_facebook.py` [P] [US3] RED — 10 failing tests: `run()` returns `{skipped: 1, reason: disabled}` when `facebook.enabled: false`, `run()` returns `{skipped: 1, reason: too_soon}` when last post within frequency_days, `run()` returns `{created: 1, approval_file: ...}` when enabled + old enough, approval file has `platforms: [facebook, instagram]`, approval file has `risk_level: HIGH`, approval file frontmatter has `draft_text`, dev_mode: no real requests.post call, `@with_retry` applied (mock 429: retries), AUTH error: no retry + vault alert created, template fallback used when `ANTHROPIC_API_KEY` absent; confirm 10 failures
- [X] T038 [US3] Implement `src/skills/post_facebook.py` — `run(vault_root) -> dict`; self-guards: read `settings.yaml` facebook.enabled; scan `vault/Logs/*.json` for last `action_type: post_facebook` and check `frequency_days`; draft: Claude API (`ANTHROPIC_API_KEY` present) or template fallback; write `vault/Pending_Approval/FB_POST_<timestamp>.md`; on approval (approval file in Approved + dev_mode=false): `POST /v20.0/{FACEBOOK_PAGE_ID}/feed` then Instagram two-step; `@with_retry` on all requests; AUTH: create `vault/Inbox/META_AUTH_ALERT_<ts>.md`; audit log; run `pytest tests/unit/test_post_facebook.py -q` and confirm 10 PASS
- [X] T039 [US3] Write + run `tests/integration/test_sc024_facebook_post_approval.py` — SC-024 scenario: dev_mode + facebook.enabled: true; `post_facebook.run()` creates approval file; approval file moved to Approved; simulation logged (`simulated: true`); 429 from mocked Meta API: retried 3 times, audit `result: failure`; both sub-scenarios pass

**Checkpoint**: US3 complete — `pytest tests/ -k "facebook or sc024" -q` all PASS; Bronze+Silver unchanged

---

## Phase 9: User Story 4 — Tweet Published with One Approval (P2)

**Goal**: `TwitterWatcher` reads timeline metrics via Twitter API v2 (tweepy); `post_twitter.py` drafts ≤280-char tweet, writes HITL approval file, publishes on approval via OAuth 1.0a.

**Independent Test**: Run `post_twitter.run(vault_root)` in dev_mode with `twitter.enabled: true`; verify `vault/Pending_Approval/TWEET_<ts>.md` created with `character_count ≤ 280`; move to Approved; verify simulation log entry.

- [X] T040 Write `tests/unit/test_twitter_watcher.py` [P] [US4] RED — 8 failing tests: `check_for_updates(dev_mode=True)` reads twitter_mock, returns list with `id`, `text`, `retweet_count`, `like_count`, `reply_count`, `created_at` keys, dedup skips already-processed tweet IDs, `create_action_file` writes `vault/Inbox/TW_ENGAGEMENT_<id>_<ts>.md`, frontmatter has `type: social_media_engagement, source: twitter`, tweepy.Client used for reads (mock), AUTH error pauses watcher, dev_mode does not call tweepy.Client; confirm 8 failures
- [X] T041 [P] [US4] Implement `src/watchers/twitter_watcher.py` — `TwitterWatcher(BaseWatcher)` with `POLL_INTERVAL_S = 86400`; `check_for_updates()`: in dev_mode read `vault/Watch/twitter_mock/sample_tweet.json`; live: `tweepy.Client(bearer_token=TWITTER_BEARER_TOKEN).get_users_tweets(id=TWITTER_USER_ID, tweet_fields=["public_metrics"], max_results=10)`; `create_action_file()`: `vault/Inbox/TW_ENGAGEMENT_<id>_<ts>.md`; AUTH error: log, set `_paused=True`; run `pytest tests/unit/test_twitter_watcher.py -q` and confirm 8 PASS
- [X] T042 Write `tests/unit/test_post_twitter.py` [P] [US4] RED — 9 failing tests: `run()` returns `{skipped: 1, reason: disabled}` when `twitter.enabled: false`, rate_limiter exceeded returns `{skipped: 1, reason: rate_limit}`, `run()` returns `{created: 1, approval_file: ...}` when enabled + under limit, approval file frontmatter has `platforms: [twitter]`, `character_count ≤ 280`, tweet > 280 chars truncated to 277 + "...", dev_mode no tweepy.Client.create_tweet call, AUTH (Unauthorized): no retry + vault alert, approval file `risk_level: HIGH`; confirm 9 failures
- [X] T043 [US4] Implement `src/skills/post_twitter.py` — `run(vault_root) -> dict`; self-guards: `twitter.enabled` setting; `rate_limiter.check_and_increment(vault_root, "post_tweet", limit_per_hour=1)`; draft: Claude API or template; enforce ≤280 chars (truncate at 277 + "..."); write `vault/Pending_Approval/TWEET_<timestamp>.md`; on approval + dev_mode=false: `tweepy.Client(consumer_key, consumer_secret, access_token, access_secret).create_tweet(text=draft_text)`; AUTH (tweepy.Unauthorized): create vault alert; audit log; run `pytest tests/unit/test_post_twitter.py -q` and confirm 9 PASS
- [X] T044 [US4] Write + run `tests/integration/test_sc025_tweet_approval.py` — SC-025 scenario: dev_mode + twitter.enabled: true; `post_twitter.run()` creates approval file with `character_count ≤ 280`; already tweeted today: returns `{skipped: 1, reason: rate_limit}`; approval file moved to Approved: simulation logged; all 3 sub-scenarios pass

**Checkpoint**: US4 complete — `pytest tests/ -k "twitter or sc025" -q` all PASS; Bronze+Silver unchanged

---

## Phase 10: User Story 6 — Watchdog Restarts Crashed Watcher Thread (P2)

**Goal**: `watchdog.py` monitors all daemon watcher threads; auto-restarts dead threads; creates vault alert after 3 consecutive failures.

**Independent Test**: Inject a dead thread into `watchdog.check_all_threads()`; verify it starts a new thread; inject 3 consecutive failures; verify `vault/Inbox/WATCHDOG_ALERT_<watcher>_<ts>.md` created.

- [X] T045 Write `tests/unit/test_watchdog.py` [P] [US6] RED — 8 failing tests: `check_all_threads` detects dead thread and calls `_restart_watcher`, successful restart resets `failure_count` to 0, failed restart increments `failure_count`, after 3 failures `_create_alert` called, alert creates `vault/Inbox/WATCHDOG_ALERT_<name>_<ts>.md`, after 3 failures watcher not retried again, healthy thread not touched, audit log emits `action_type: watchdog_restart`; confirm 8 failures
- [X] T046 [US6] Implement `src/watchers/watchdog.py` — `Watchdog(check_interval_s=60, max_restart_attempts=3)`; `check_all_threads(watcher_registry, thread_registry)`: for each thread not `is_alive()` → `_restart_watcher()`; track `failure_count` per watcher name; on `failure_count >= MAX_RESTART_ATTEMPTS`: `_create_alert()` + stop retrying; `_restart_watcher()`: start new thread, return thread or None on exception; `_create_alert()`: write `vault/Inbox/WATCHDOG_ALERT_<watcher>_<ts>.md`; audit log `watchdog_restart`/`watchdog_alert`; run `pytest tests/unit/test_watchdog.py -q` and confirm 8 PASS
- [X] T047 [US6] Write + run `tests/integration/test_sc027_watchdog_restart.py` — SC-027 scenario: given dead watcher thread (mock `is_alive() = False`), `check_all_threads` restarts it and audit logs `result: success`; given 3 consecutive restart failures, vault alert Inbox item created and audit logs `result: failure`; both sub-scenarios pass

**Checkpoint**: US6 complete — `pytest tests/ -k "watchdog or sc027" -q` all PASS; Bronze+Silver unchanged

---

## Phase 11: User Story 8 — Multi-Step Plan Completes Without Re-Prompting (P2)

**Goal**: `ralph_loop.py` drives multi-step plans to completion via file-movement detection; `stop_hook.py` registered to `.claude/hooks/Stop`; `install_schedule.py` extended for idempotent hook registration.

**Independent Test**: Create `vault/Plans/PLAN_test001.md` with `requires_ralph: true`; run `ralph_loop.py` pointing at it; move file to `vault/Done/`; verify loop exits with `{status: "done"}`; verify `ralph_loop_state.json` shows `status: done`.

- [X] T048 Write `tests/unit/test_ralph_loop.py` [P] [US8] RED — 8 failing tests: `_write_state(1, "running")` creates/overwrites `vault/state/ralph_loop_state.json`, state file has correct 4 keys, `_is_done()` returns True when task_file in Done/, `_is_done()` returns False when task_file in Plans/, `_is_cancelled()` returns True when task_file in Rejected/, `run()` returns `{status: "done"}` when file moves to Done after iteration 1, `run()` returns `{status: "cancelled"}` when file moves to Rejected, `run()` moves file to Quarantine + returns `{status: "quarantined"}` when max_iterations exceeded; confirm 8 failures
- [X] T049 [US8] Implement `src/core/ralph_loop.py` — `RalphLoop(vault_root, task_file, prompt, max_iterations=10)`; `run() -> dict`; `_write_state(iteration, status)` writes `vault/state/ralph_loop_state.json`; `_is_done()` checks if `task_file` basename exists under `vault/Done/`; `_is_cancelled()` checks `vault/Rejected/`; overflow: `shutil.move(task_file, vault/Quarantine/)` + create `vault/Inbox/RALPH_TIMEOUT_ALERT_<ts>.md`; audit log `ralph_loop_complete`; run `pytest tests/unit/test_ralph_loop.py -q` and confirm 8 PASS
- [X] T050 Write `tests/unit/test_stop_hook.py` [P] [US8] RED — 6 failing tests: no state file → exits 0, state `status: done` → exits 0, state `status: cancelled` → exits 0, task_file found in Done/ → updates state to `done` + exits 0, task_file found in Rejected/ → updates state to `cancelled` + exits 0, corrupt JSON in state file → exits 0 (graceful); confirm 6 failures
- [X] T051 [P] [US8] Implement `hooks/stop_hook.py` — read `vault/state/ralph_loop_state.json`; handle missing file, corrupt JSON, done/cancelled/quarantined status; check `task_file` location (Done/, Rejected/); update state accordingly; exit 0 always (graceful); run `pytest tests/unit/test_stop_hook.py -q` and confirm 6 PASS
- [X] T052 Write `tests/unit/test_install_schedule_gold.py` [P] [US8] RED — 3 failing tests: `_register_stop_hook(vault_root)` creates `.claude/hooks/Stop` pointing to `hooks/stop_hook.py`, second call is idempotent (no error, no duplicate), registered hook file path is correct; confirm 3 failures
- [X] T053 [US8] Patch `src/skills/install_schedule.py` — add `_register_stop_hook(vault_root)` function: create `.claude/hooks/` dir if absent; write `.claude/hooks/Stop` with `#!/usr/bin/env python3\nimport subprocess, sys\nsys.exit(subprocess.call(["python", "hooks/stop_hook.py"]))`; idempotent: skip if content matches; call `_register_stop_hook` from `run()` main function; run `pytest tests/unit/test_install_schedule_gold.py -q` and confirm 3 PASS
- [X] T054 [US8] Write + run `tests/integration/test_sc029_ralph_loop_done.py` — SC-029 scenario: given PLAN file with `requires_ralph: true`, `RalphLoop(task_file=...).run()` drives until file moved to Done/; loop exits `{status: "done", iterations: N}`; given max_iterations=2 exceeded, task moved to Quarantine; given manual move to Done/ during loop, `_is_done()` detects and exits cleanly; all 3 sub-scenarios pass

**Checkpoint**: US8 complete — `pytest tests/ -k "ralph or stop_hook or sc029" -q` all PASS; Bronze+Silver unchanged

---

## Phase 12: Orchestrator Integration + Polish

**Purpose**: Wire all new Gold watchers and services into the orchestrator; run full Gold E2E suite; final polish.

**⚠️ NOTE**: `src/orchestrator.py` patch touches existing Silver code — run `pytest tests/ -k "not gold" -q` before and after to confirm no regressions.

- [X] T055 Write `tests/integration/test_orchestrator_gold.py` [P] RED — 6 failing tests: orchestrator startup reads `config/mcp_servers.yaml`, `FinanceWatcher` daemon thread created on startup, `FacebookWatcher` daemon thread created, `TwitterWatcher` daemon thread created, `Watchdog` daemon thread created, plan with `requires_ralph: true` in frontmatter triggers `RalphLoop.run()` (mock); confirm 6 failures
- [X] T056 Patch `src/orchestrator.py` — add `_start_mcp_servers()` reading `config/mcp_servers.yaml` and starting each server subprocess; add `FinanceWatcher`, `FacebookWatcher`, `TwitterWatcher` daemon threads to `_watcher_threads`; add `Watchdog` daemon thread; call `archive_old_logs(vault_root)` on startup; in `_scan_cycle()`: detect `requires_ralph: true` in plan frontmatter and delegate to `RalphLoop`; run `pytest tests/integration/test_orchestrator_gold.py -q` and confirm 6 PASS; run `pytest tests/ -k "not gold" -q` and confirm no regressions
- [X] T057 [P] Write + run `tests/integration/test_sc021_to_sc032_full_suite.py` — Gold E2E sweep: run all 12 SC tests (SC-021 through SC-032) in sequence using shared tmp vault; verify all pass; this is the final acceptance gate; confirm `character_count` ≤ 280 in tweet approval file, `Current_Month.md` Markdown valid, `YYYY-MM-DD.json` all 9 fields valid
- [X] T058 [P] Run `pytest tests/ -q --cov=src --cov-report=term-missing` — verify total count ≥ 1,036 tests; verify ≥ 70% coverage on `src/`; if coverage below 70% add targeted unit tests for uncovered branches in `retry_handler.py`, `audit_logger.py`, `finance_watcher.py`
- [X] T059 [P] Security scan: `grep -r "sk-\|EAA\|Bearer\|password\s*=\s*['\"]" src/ hooks/ config/ --include="*.py" --include="*.yaml"` — confirm no hardcoded secrets in any Gold file; check `.env.example` contains only placeholder values
- [X] T060 Review and update `specs/003-gold-tier/spec.md` status field to `IMPLEMENTED`; update `MEMORY.md` with Gold Tier completion status and final test count

**Checkpoint**: Gold Tier COMPLETE — all SC-021–SC-032 verified; `pytest tests/ -q` shows ~1,036 tests passing; coverage ≥ 70%

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1 (Setup)     — No deps; start immediately
Phase 2 (Foundational) — Requires Phase 1; BLOCKS all user story phases
Phase 3 (US1)       — Requires Phase 2; MVP increment
Phase 4 (US2)       — Requires Phase 2; can parallel with Phase 3
Phase 5 (US7)       — Requires Phase 2 + Phase 3 (accounting_audit reads finance data)
Phase 6 (US5)       — Requires Phase 2; integration tests for retry_handler
Phase 7 (US9)       — Requires Phase 2; integration tests for audit_logger
Phase 8 (US3)       — Requires Phase 2; can parallel with Phases 3-7
Phase 9 (US4)       — Requires Phase 2; can parallel with Phase 8
Phase 10 (US6)      — Requires Phase 2; can parallel with Phases 8-9
Phase 11 (US8)      — Requires Phase 2; can parallel with Phases 8-10
Phase 12 (Polish)   — Requires Phases 3-11 complete
```

### User Story Dependencies

- **US1 (P1)**: Depends on Phase 2 (Odoo MCP client) — no US dependencies
- **US2 (P1)**: Depends on Phase 2 (Odoo MCP client) — no US dependencies; can parallel with US1
- **US7 (P1)**: Depends on US1 (reads finance data) + Phase 2 — implement after US1
- **US5 (P1)**: Integration tests only; decorator already in Phase 2 — can run any time after Phase 2
- **US9 (P1)**: Integration tests only; implementation in Phase 2 — can run any time after Phase 2
- **US3, US4, US6, US8 (P2)**: All depend only on Phase 2 — can all parallel after P1 stories

### Parallel Opportunities (Within Phases)

**Phase 1**: T001–T010 all can run in parallel (different files)
**Phase 2**: T011+T012 parallel with T013+T014; T015+T016 parallel with T017+T018; T013–T014 must precede T015 (audit_logger used in client)
**Phase 3**: T019 (RED) → T020 (GREEN); T021+T022+T023 parallel (different test files)
**Phase 8–11**: Entire phases can run in parallel (different modules, different test files)

---

## Parallel Execution Examples

### Phase 8 + Phase 9 in Parallel

```bash
# Terminal 1 — US3 (Facebook)
pytest tests/unit/test_facebook_watcher.py -q   # RED
# implement src/watchers/facebook_watcher.py     # GREEN
pytest tests/unit/test_post_facebook.py -q       # RED
# implement src/skills/post_facebook.py           # GREEN

# Terminal 2 — US4 (Twitter)
pytest tests/unit/test_twitter_watcher.py -q     # RED
# implement src/watchers/twitter_watcher.py       # GREEN
pytest tests/unit/test_post_twitter.py -q        # RED
# implement src/skills/post_twitter.py            # GREEN
```

### Phase 10 + Phase 11 in Parallel

```bash
# Terminal 1 — US6 (Watchdog)
pytest tests/unit/test_watchdog.py -q            # RED → implement → GREEN

# Terminal 2 — US8 (Ralph)
pytest tests/unit/test_ralph_loop.py -q          # RED → implement → GREEN
pytest tests/unit/test_stop_hook.py -q           # RED → implement → GREEN
```

---

## Implementation Strategy

### MVP First (US1 Only)

1. Phase 1: Setup (T001–T010)
2. Phase 2: Foundational (T011–T018) — blocks all stories
3. Phase 3: US1 Finance Transactions (T019–T023)
4. **STOP and VALIDATE**: SC-021 + SC-022 pass; `Current_Month.md` populated in dev_mode
5. **MVP DEMO**: Finance Watcher running in dev_mode, writing accounting data

### Incremental Delivery (P1 Stories)

1. MVP (US1) → Finance data flowing
2. US2 → Invoice creation working
3. US7 → CEO Briefing with financial sections
4. US5 + US9 integration validation → Error recovery + Audit logging confirmed
5. **P1 COMPLETE**: All P1 stories verified

### Full Gold Delivery (All Stories)

6. US3 + US4 in parallel → Social media posting
7. US6 + US8 in parallel → Reliability + Autonomy
8. Phase 12 → Orchestrator wired + all SC tests passing

---

## Summary

| Phase | Stories | Tasks | Tests |
|-------|---------|-------|-------|
| 1 Setup | — | T001–T010 | 0 |
| 2 Foundational | US5+US9 core | T011–T018 | 38 unit |
| 3 Finance Transactions | US1 (P1) | T019–T023 | 15+3 E2E |
| 4 Invoice Creation | US2 (P1) | T024–T026 | 8+1 E2E |
| 5 CEO Briefing | US7 (P1) | T027–T031 | 8+10+1 E2E |
| 6 Error Recovery Integration | US5 (P1) | T032 | 1 E2E |
| 7 Audit Logging Integration | US9 (P1) | T033–T034 | 2 E2E |
| 8 Facebook + Instagram | US3 (P2) | T035–T039 | 8+10+1 E2E |
| 9 Twitter | US4 (P2) | T040–T044 | 8+9+1 E2E |
| 10 Watchdog | US6 (P2) | T045–T047 | 8+1 E2E |
| 11 Ralph Wiggum | US8 (P2) | T048–T054 | 8+6+3+1 E2E |
| 12 Polish + E2E | — | T055–T060 | 6+12 sweep |
| **TOTAL** | **9 stories** | **60 tasks** | **~120 new tests** |

**Gold Tier Success Criteria**: SC-021 through SC-032 all pass ✅
