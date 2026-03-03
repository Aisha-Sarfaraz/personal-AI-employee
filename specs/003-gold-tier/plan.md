# Implementation Plan: Gold Tier — Autonomous AI Employee

**Branch**: `003-gold-tier` | **Date**: 2026-02-25 | **Spec**: `specs/003-gold-tier/spec.md`
**Input**: Feature specification from `/specs/003-gold-tier/spec.md`
**Status**: COMPLETE (all Phase 0 research resolved, Phase 1 artifacts written)
**Predecessor**: Silver Tier — 531 tests, 73.36% coverage, SC-010–SC-020 verified

---

## Summary

Gold Tier transforms the Silver personal AI assistant into a **fully autonomous business
employee** by activating live accounting (Odoo 19+ via custom MCP server), cross-platform
social media (Facebook + Instagram, Twitter/X), enterprise error recovery, structured audit
logging, and the Ralph Wiggum autonomous loop.

**Architecture approach**: Additive — Gold adds new modules; existing Silver/Bronze code is
unchanged except for minimal, targeted patches to `audit_logger.py`, `weekly_briefing.py`,
`execute_plan.py`, `install_schedule.py`, and `orchestrator.py`.

**Target**: 531 Silver + 385 Bronze + ~120 Gold = ~1,036 total tests; ≥70% line coverage.

---

## Technical Context

**Language/Version**: Python 3.10+
**Primary Dependencies**:
- `requests>=2.31` — Odoo JSON-RPC, Meta Graph API
- `tweepy>=4.14` — Twitter API v2
- `mcp>=1.0` — MCP server (odoo-mcp) and client
- `watchdog`, `pyyaml`, `python-dotenv` — unchanged from Silver
- `anyio` — MCP stdio transport (transitive via mcp)

**Storage**: Local filesystem — Obsidian-compatible Markdown vault + JSON state files + JSON-Lines audit logs + Docker-hosted Odoo/PostgreSQL

**Testing**: `pytest` + `pytest-asyncio` (for MCP async handler tests)

**Target Platform**: Windows 10 (dev) / Linux (production); Docker Desktop for Odoo

**Performance Goals**:
- Finance Watcher: poll cycle ≤ 300s
- Audit log write: non-blocking (write ≤5ms per entry)
- MCP server: stdio response ≤2s per tool call

**Constraints**:
- Twitter Free tier: 1 tweet/day; 300 reads/15min
- Meta Graph API: 200 calls/hour
- All 531 Silver + 385 Bronze tests must pass throughout implementation
- No refactoring of existing Bronze/Silver modules (additive only)

**Scale/Scope**: Solo-business use case; single orchestrator process; no concurrent users

**Constitution Reference**: `.specify/memory/constitution.md` §2.3 [GOLD]

---

## Constitution Check

| Rule | Status |
|------|--------|
| No implementation without approved spec | ✅ spec.md complete (v1.0.0), all clarifications resolved |
| TDD mandate (tests before code) | ✅ Tasks will enforce Red-Green-Refactor |
| No hardcoded secrets | ✅ All credentials via `.env` / env vars |
| Smallest viable diff | ✅ Additive-only; Silver/Bronze untouched |
| No unrelated refactoring | ✅ Patches minimal to `audit_logger.py`, `weekly_briefing.py`, `execute_plan.py`, `install_schedule.py`, `orchestrator.py` |
| Bronze invariant | ✅ All 385 Bronze tests must pass throughout |
| Silver invariant | ✅ All 531 Silver tests must pass throughout |
| DEV_MODE safe | ✅ All new watchers/skills respect `dev_mode: true` (no real external calls) |

---

## Project Structure

### Documentation (this feature)

```text
specs/003-gold-tier/
├── plan.md              ← this file
├── spec.md              ← requirements (v1.0.0, complete)
├── research.md          ← Phase 0 output (Odoo, Meta, Twitter, MCP patterns)
├── data-model.md        ← Gold entities (FinanceTransaction, AuditEntry, RalphLoopState, OdooInvoice, SocialPost)
├── quickstart.md        ← setup guide (Odoo Docker, Meta tokens, Twitter, env vars)
├── checklists/          ← sp.checklist output
├── contracts/
│   ├── odoo_mcp_tools.md    ← 6 MCP tools + OdooMCPClient interface
│   ├── social_skills.md     ← post_facebook, post_twitter, FB/Twitter watcher contracts
│   ├── finance_watcher.md   ← FinanceWatcher interface + dedup + CSV format
│   ├── error_recovery.md    ← @with_retry, ErrorCategory, degradation contracts
│   └── ralph_loop.md        ← RalphLoop + stop_hook interface
└── tasks.md             ← /sp.tasks output (next step)
```

### Source Code (new Gold files)

```text
src/
├── mcp_servers/
│   └── odoo_mcp/
│       ├── __init__.py
│       ├── server.py         [NEW] MCP stdio server (6 tools)
│       └── client.py         [NEW] Plain Python client (direct import)
├── watchers/
│   ├── finance_watcher.py    [PATCH] Silver stub → full implementation
│   ├── facebook_watcher.py   [NEW]
│   └── twitter_watcher.py    [NEW]
├── skills/
│   ├── post_facebook.py      [NEW]
│   ├── post_twitter.py       [NEW]
│   ├── generate_invoice.py   [NEW]
│   └── accounting_audit.py   [NEW]
├── core/
│   ├── retry_handler.py      [NEW] @with_retry + ErrorCategory
│   ├── ralph_loop.py         [NEW] autonomous loop
│   ├── audit_logger.py       [PATCH] Gold JSON-Lines schema + backward-compat wrapper
│   └── watchdog.py           [PATCH/NEW] enhanced thread monitor (may already exist as stub)
└── orchestrator.py           [PATCH] MCP server registry + Finance/FB/TW watcher threads + Ralph detection

config/
├── mcp_servers.yaml          [NEW] MCP server registry
├── audit_logic.yaml          [NEW] subscription patterns for CEO Briefing
└── settings.yaml             [PATCH] Gold stanzas (odoo, facebook, twitter, ralph_loop, audit, sla)

hooks/
└── stop_hook.py              [NEW] Ralph Wiggum Stop hook

docker-compose.odoo.yml       [NEW] Odoo 19 + PostgreSQL Docker Compose

vault/
├── Accounting/               [NEW] financial transaction logs
├── Watch/
│   ├── finance_mock/         [NEW] dev-mode JSON fixtures
│   ├── finance_drop/         [NEW] CSV fallback drop folder
│   ├── facebook_mock/        [NEW] dev-mode Facebook fixtures
│   └── twitter_mock/         [NEW] dev-mode Twitter fixtures
└── state/
    ├── finance_processed_ids.json  [NEW]
    └── ralph_loop_state.json       [NEW]
```

### Silver/Bronze Patches (minimal)

| File | Change |
|------|--------|
| `src/core/audit_logger.py` | Add `log()` method writing JSON-Lines; keep `log_action()` backward-compatible |
| `src/skills/weekly_briefing.py` | Add `accounting_audit.run()` call; add 5 new briefing sections |
| `src/skills/execute_plan.py` | Detect `requires_ralph: true`; delegate to `ralph_loop.run()` |
| `src/skills/install_schedule.py` | Add `_register_stop_hook()` call |
| `src/orchestrator.py` | Add Finance/FB/TW watcher threads; MCP server registry startup; watchdog thread |

---

## Scope

### In Scope (Gold)

1. Odoo MCP server (`src/mcp_servers/odoo_mcp/`) — 6 tools, JSON-RPC, HITL gate
2. Finance Watcher — Silver stub → full implementation; Odoo + CSV fallback; dev-mode mock
3. Facebook Watcher + `post_facebook.py` — Meta Graph API v20.0; engagement read; FB+IG post
4. Twitter Watcher + `post_twitter.py` — Twitter API v2; tweepy; 1 tweet/day guard
5. `generate_invoice.py` — invoice creation skill; delegates to Odoo MCP; HITL approval
6. `accounting_audit.py` — sub-skill for CEO Briefing; reads Odoo invoices/expenses
7. `retry_handler.py` — `@with_retry` + `ErrorCategory` + per-component degradation
8. `watchdog.py` — daemon thread monitor; auto-restart; alert after 3 failures
9. `audit_logger.py` patch — Gold JSON-Lines schema; 90-day archival; backward-compat
10. `ralph_loop.py` + `stop_hook.py` — autonomous multi-step plan completion
11. `weekly_briefing.py` patch — Revenue, Expense, Bottleneck, Suggestions, Social Summary
12. `config/mcp_servers.yaml` — MCP server registry
13. `config/audit_logic.yaml` — subscription detection patterns
14. `config/settings.yaml` patch — Gold stanzas
15. `docker-compose.odoo.yml` — Odoo 19 + PostgreSQL
16. Tests: ~120 new Gold tests (unit + integration, all in dev_mode)

### Out of Scope

- Cloud deployment (Platinum)
- WhatsApp/LinkedIn modifications (Silver)
- Full OAuth2 refresh flow for Meta tokens (manual refresh per quickstart.md)
- Real-time Odoo webhook integration (pull-only)
- Multi-user / multi-company Odoo support
- Instagram Stories / Reels (feed posts only)

### Non-Goals

- Modifying any Bronze or Silver test
- Refactoring Bronze core modules (`vault.py`, `frontmatter.py`, `approval.py`)
- Refactoring any Silver watcher or skill (patches only)

### Silver + Bronze Invariant

All 531 Silver + 385 Bronze tests must pass throughout Gold implementation.
Run at the start of each implementation phase:
```bash
python -m pytest tests/ -k "not gold" -q
```

---

## Implementation Phases

---

### Phase 1 — Core Infrastructure (no external API calls)

**Goal**: Foundation modules that all Gold components depend on. No external services.
**Invariant check**: `pytest tests/ -k "not gold" -q` green before merging.

#### P1-T01 — `src/core/retry_handler.py`

- Implement `ErrorCategory` enum: `TRANSIENT`, `AUTH`, `LOGIC`, `DATA`, `SYSTEM`
- Implement `@with_retry(max_attempts=3, base_delay=1.0, max_delay=60.0)` decorator
- Exponential back-off with uniform jitter: `delay = min(base * 2**n, max) + uniform(0, 0.5)`
- `AUTH` and `LOGIC`/`DATA` categories: raise immediately, no retry
- Emit Python logger `WARNING` on each retry attempt
- Tests: 8 unit tests (retry succeeds on 3rd, exhausted re-raises, AUTH no retry, etc.)

#### P1-T02 — `src/core/audit_logger.py` (patch)

- Add `log(action_type, actor, target, parameters, approval_status, approved_by, result, error)` method
- Write JSON-Lines to `vault/Logs/YYYY-MM-DD.json` (one object per line)
- Add `log_action(vault_root, agent, action, risk_tier, status, **kwargs)` backward-compatible wrapper
- Add `archive_old_logs(vault_root, retention_days=90)` function (runs on orchestrator startup)
- Validate all 9 mandatory fields present; raise `ValueError` on missing mandatory field
- Tests: 10 unit tests (schema validation, backward-compat call, archival, result=degraded)

#### P1-T03 — `config/settings.yaml` + `.env.example` (patch)

- Add Gold stanzas: `odoo`, `facebook`, `twitter`, `ralph_loop`, `audit`, `sla`
- Add Gold env vars to `.env.example`: `ODOO_URL`, `ODOO_DB`, `ODOO_UID`, `ODOO_PASSWORD`,
  `FACEBOOK_PAGE_ID`, `FACEBOOK_ACCESS_TOKEN`, `INSTAGRAM_USER_ID`,
  `TWITTER_BEARER_TOKEN`, `TWITTER_API_KEY`, `TWITTER_API_SECRET`,
  `TWITTER_ACCESS_TOKEN`, `TWITTER_ACCESS_SECRET`, `TWITTER_USER_ID`
- Add `config/audit_logic.yaml` with `SUBSCRIPTION_PATTERNS` list
- Tests: 2 config load tests (new stanzas readable, no KeyError on access)

---

### Phase 2 — Odoo MCP Server

**Goal**: Fully working Odoo MCP server + Python client; all 6 tools; dev_mode mock.
**Invariant check**: All Phase 1 tests green.

#### P2-T01 — `docker-compose.odoo.yml`

- Define `odoo` (image: `odoo:19.0`) and `db` (image: `postgres:16`) services
- Bind-mount `config/odoo/odoo.conf` for Odoo configuration
- Expose port 8069; internal network for DB
- No tests (infrastructure file)

#### P2-T02 — `src/mcp_servers/odoo_mcp/client.py`

- Implement `OdooMCPClient` with 6 methods matching contract in `contracts/odoo_mcp_tools.md`
- `_execute_kw()` private method with per-call JSON-RPC auth
- All write methods: create approval file and return `{status: "pending_approval", ...}`
- `dev_mode=True`: return mocked responses, no real HTTP
- `@with_retry` applied to all `_execute_kw` calls (TRANSIENT errors only)
- Tests: 14 unit tests (each tool in dev_mode + real mode mocked via `requests-mock`)

#### P2-T03 — `src/mcp_servers/odoo_mcp/server.py`

- Implement `mcp.server.Server("odoo-mcp")` with `@server.list_tools()` + `@server.call_tool()`
- 6 tools matching schemas in contract
- Delegates to `OdooMCPClient` internally
- `anyio.run(main)` entry point for stdio transport
- Tests: 6 async unit tests (call each tool handler directly via `await call_tool(name, args)`)

#### P2-T04 — `config/mcp_servers.yaml`

- Define `email-mcp` and `odoo-mcp` server entries
- Fields: `name`, `command`, `args`, `transport: stdio`, `env_vars`, `health_check_interval_s`
- Tests: 1 config load test (YAML parseable, required fields present)

---

### Phase 3 — Finance Watcher

**Goal**: Implement the Silver stub `finance_watcher.py`; Odoo primary + CSV fallback + dev-mode mock.
**Invariant check**: All Phase 2 tests green; Silver stub test updated to expect real implementation.

#### P3-T01 — `src/watchers/finance_watcher.py` (patch Silver stub)

- Implement `check_for_updates()` → poll `OdooMCPClient.list_transactions()` then CSV fallback
- Implement `create_action_file()` → append row to `vault/Accounting/Current_Month.md`
- Implement `_make_item_id()` → Odoo: `str(move_line_id)`; CSV: SHA-256(date+desc+amount)[:16]
- Implement `_check_month_rollover()` → archive + create new file on month change
- Load processed IDs from `vault/state/finance_processed_ids.json`; save on each new item
- Dev-mode: read `vault/Watch/finance_mock/*.json`
- CSV fallback: parse `vault/Watch/finance_drop/*.csv` (header-skipped, 4 columns)
- Tests: 15 unit tests (Odoo path, CSV path, dev-mode path, dedup, month rollover, degradation)

#### P3-T02 — `src/skills/generate_invoice.py`

- Follow `run(vault_root) -> dict` contract
- Parse intent from WhatsApp/email items in `vault/Needs_Action/` with `intent: invoice_request`
- Call `OdooMCPClient.create_invoice()` → returns approval file path
- If partner unparseable: write `partner: [NEEDS HUMAN INPUT]` in approval file
- Tests: 8 unit tests (full flow, unparseable partner, dev_mode, idempotency)

#### P3-T03 — Vault structure for Finance

- Create `vault/Accounting/.gitkeep`
- Create `vault/Watch/finance_mock/sample_transactions.json`
- Create `vault/Watch/finance_drop/.gitkeep`
- No tests (fixture files)

---

### Phase 4 — Social Media (Facebook, Instagram, Twitter)

**Goal**: Facebook + Instagram watcher + post skill; Twitter watcher + post skill.
**Invariant check**: All Phase 3 tests green.

#### P4-T01 — `src/watchers/facebook_watcher.py`

- Extend `BaseWatcher`; `check_for_updates()` polls Meta Graph API
- Engagement read: `GET /v20.0/me/posts?fields=message,likes.summary(true),...`
- `create_action_file()` → `vault/Inbox/FB_ENGAGEMENT_<id>_<ts>.md`
- Dev-mode: read `vault/Watch/facebook_mock/sample_post.json`
- `@with_retry` on all Meta API calls
- Tests: 8 unit tests (dev-mode, live-mode mocked, dedup, AUTH error handling)

#### P4-T02 — `src/skills/post_facebook.py`

- Self-guards: `facebook.enabled` setting + last-post age check
- Draft: Claude API or template fallback
- Write `vault/Pending_Approval/FB_POST_<timestamp>.md`
- On approval: `POST /v20.0/{page-id}/feed` + Instagram two-step
- `@with_retry` on Meta API calls
- Tests: 10 unit tests (disabled guard, frequency guard, draft, approval path dev_mode, AUTH error)

#### P4-T03 — `src/watchers/twitter_watcher.py`

- Extend `BaseWatcher`; `check_for_updates()` polls Twitter API v2 via tweepy
- `GET /2/users/:id/tweets?tweet.fields=public_metrics`
- `create_action_file()` → `vault/Inbox/TW_ENGAGEMENT_<id>_<ts>.md`
- Dev-mode: read `vault/Watch/twitter_mock/sample_tweet.json`
- Tests: 8 unit tests (dev-mode, live-mode mocked, dedup, AUTH error handling)

#### P4-T04 — `src/skills/post_twitter.py`

- Self-guards: `twitter.enabled` + `rate_limiter.check_and_increment("post_tweet", 1)`
- Draft: Claude API; enforce ≤280 chars (truncate at 277 + "..." if over)
- Write `vault/Pending_Approval/TWEET_<timestamp>.md`
- On approval: `tweepy.Client.create_tweet(text=draft_text)`
- Tests: 9 unit tests (rate limit guard, draft length, approval dev_mode, AUTH, truncation)

#### P4-T05 — Vault social mock fixtures

- `vault/Watch/facebook_mock/sample_post.json`
- `vault/Watch/twitter_mock/sample_tweet.json`
- No tests (fixture files)

---

### Phase 5 — Ralph Wiggum Autonomous Loop

**Goal**: `ralph_loop.py` + `stop_hook.py`; orchestrator integration; `install_schedule.py` patch.
**Invariant check**: All Phase 4 tests green.

#### P5-T01 — `src/core/ralph_loop.py`

- Implement `RalphLoop(vault_root, task_file, prompt, max_iterations=10)`
- `run()` loop: write state → launch Claude subprocess → check completion
- State file: `vault/state/ralph_loop_state.json`
- Completion check: `task_file` moved to `vault/Done/`
- Cancellation check: `task_file` moved to `vault/Rejected/`
- Overflow: move to `vault/Quarantine/`; create alert Inbox item
- Tests: 8 unit tests (done detection, cancelled detection, overflow, state file contents)

#### P5-T02 — `hooks/stop_hook.py`

- Read `vault/state/ralph_loop_state.json`; check task_file location
- Update state to `done` or `cancelled` as appropriate; exit 0
- Graceful: exits 0 if no state file (no active loop)
- Tests: 6 unit tests (no state file, done, cancelled, running, quarantined, bad JSON)

#### P5-T03 — `install_schedule.py` (patch)

- Add `_register_stop_hook()` function
- Write `hooks/stop_hook.py` content and register in `.claude/hooks/Stop`
- Idempotent: skip if already registered
- Tests: 3 unit tests (registers, idempotent, path correct)

---

### Phase 6 — Watchdog + Orchestrator Integration

**Goal**: Thread monitor; orchestrator wires all new watchers + MCP registry + Finance/Social threads.
**Invariant check**: All Phase 5 tests green.

#### P6-T01 — `src/watchers/watchdog.py` (new/patch)

- Implement `Watchdog(check_interval_s=60, max_restart_attempts=3)`
- `check_all_threads()`: iterate thread registry; attempt restart on dead thread
- `_create_alert()`: `vault/Inbox/WATCHDOG_ALERT_<watcher>_<ts>.md`
- Track `failure_count` per watcher; stop retrying after 3 failures
- Audit log: `watchdog_restart` / `watchdog_alert`
- Tests: 8 unit tests (restart success, restart fail x3, alert creation, healthy threads)

#### P6-T02 — `src/orchestrator.py` (patch)

- On startup: parse `config/mcp_servers.yaml`; start `odoo-mcp` subprocess alongside `email-mcp`
- Add `FinanceWatcher`, `FacebookWatcher`, `TwitterWatcher` daemon threads
- Add `Watchdog` daemon thread
- Add `archive_old_logs()` call on startup archival pass
- `_scan_cycle()`: detect `requires_ralph: true` plan frontmatter → delegate to `RalphLoop`
- Tests: 6 integration tests (watcher thread starts, MCP server starts, Ralph delegation)

---

### Phase 7 — Enhanced CEO Briefing + Accounting Audit

**Goal**: `accounting_audit.py` sub-skill; `weekly_briefing.py` patch with 5 new sections.
**Invariant check**: All Phase 6 tests green; existing Silver briefing tests still pass.

#### P7-T01 — `src/skills/accounting_audit.py`

- `run(vault_root) -> dict` → returns `{revenue: {...}, expenses: {...}, suggestions: [...]}`
- Revenue: reads Odoo `list_invoices(state="posted")` for current week/month
- Expenses: reads Odoo `list_transactions` + matches `SUBSCRIPTION_PATTERNS` from `audit_logic.yaml`
- Suggestions: flags subs with no Odoo activity > 30 days; cost spike > 20% vs prior month avg
- Degradation: returns `{revenue: None, expenses: None, error: "Odoo offline"}` on ConnectionError
- Tests: 8 unit tests (revenue calc, expense calc, subscription flag, cost spike, degradation)

#### P7-T02 — `src/skills/weekly_briefing.py` (patch)

- Call `accounting_audit.run()` for financial data
- Add 5 new sections: Revenue, Expense, Bottleneck, Proactive Suggestions, Social Summary
- Degradation: show `[Data unavailable — Odoo offline]` when accounting_audit returns error
- Bottleneck: compare `created_at` vs `completed_at` delta for `vault/Done/` items past 7 days
- Social Summary: aggregate engagement from `vault/Logs/` for LinkedIn + Facebook + Twitter
- Self-guard (Monday + file-not-exists) unchanged from Silver
- Tests: 10 unit tests (all new sections, Odoo offline degradation, social summary, SLA check)

---

### Phase 8 — Gold E2E Integration Tests

**Goal**: Full-stack Gold scenario tests (dev-mode only).
**Invariant check**: All Phases 1-7 tests green.

#### P8-T01 — Gold Success Criteria Tests

| ID | Scenario | Test |
|----|----------|------|
| SC-021 | Finance Watcher reads mock, appends to Accounting | `test_sc021_finance_watcher_mock_ingestion` |
| SC-022 | CSV fallback when Odoo unreachable | `test_sc022_finance_csv_fallback` |
| SC-023 | Invoice approval flow (dev_mode) | `test_sc023_invoice_approval_flow` |
| SC-024 | Facebook post approval + simulation | `test_sc024_facebook_post_approval` |
| SC-025 | Tweet approval + simulation | `test_sc025_tweet_approval` |
| SC-026 | @with_retry retries TRANSIENT, not AUTH | `test_sc026_retry_handler` |
| SC-027 | Watchdog restarts dead thread | `test_sc027_watchdog_restart` |
| SC-028 | Monday CEO Briefing with financial sections | `test_sc028_ceo_briefing_with_finance` |
| SC-029 | Ralph loop completes when file moves to Done | `test_sc029_ralph_loop_done` |
| SC-030 | Gold audit log JSON-Lines schema valid | `test_sc030_audit_log_schema` |
| SC-031 | Silver backward-compat log_action still works | `test_sc031_audit_backward_compat` |
| SC-032 | Month rollover creates new Accounting file | `test_sc032_month_rollover` |

Tests: 12 E2E tests; all in dev_mode=True.

---

## Risk Analysis

1. **Odoo JSON-RPC version drift** — Odoo 19 API may differ from documented 17 patterns.
   *Mitigation*: Smoke-test `list_transactions` against Docker Odoo before writing Finance Watcher.
   *Fallback*: CSV-only mode is functional for dev and early production.

2. **Meta long-lived token expiry** — 60-day token expires silently; AUTH error halts FB/IG posting.
   *Mitigation*: `quickstart.md` documents refresh procedure; vault alert created on 401.
   *Fallback*: Social posting is additive; system operates normally without it.

3. **MCP SDK breaking changes** — `mcp` Python library is young; API may change between versions.
   *Mitigation*: Pin to `mcp>=1.0,<2.0` in `requirements.txt`; test handler-direct pattern avoids subprocess complexity.

---

## ADR Suggestions

The following decisions meet all three significance criteria (long-term impact, alternatives
considered, cross-cutting scope):

1. **Odoo MCP transport (stdio vs HTTP)**: Confirmed stdio; consistent with `email-mcp`.
   → Already resolved in spec clarifications. Document if desired: `/sp.adr odoo-mcp-transport`

2. **Meta Graph API auth (Page token vs OAuth2 refresh)**: Long-lived token chosen.
   → `/sp.adr meta-graph-api-auth`

3. **Ralph Wiggum hook registration (auto vs manual)**: Auto via `install_schedule.py`.
   → `/sp.adr ralph-wiggum-hook-registration`

📋 Three architectural decisions detected. Document reasoning and tradeoffs?
Run `/sp.adr odoo-mcp-transport`, `/sp.adr meta-graph-api-auth`, `/sp.adr ralph-wiggum-hook-registration`

---

## Acceptance Checklist

- [ ] All 385 Bronze tests pass (`pytest tests/ -k bronze -q`)
- [ ] All 531 Silver tests pass (`pytest tests/ -k silver -q`)
- [ ] All ~120 Gold tests pass (`pytest tests/ -k gold -q`)
- [ ] Coverage ≥ 70% on `src/` (`pytest --cov=src --cov-report=term-missing`)
- [ ] SC-021 through SC-032 all verified
- [ ] `DEV_MODE=true python -m src.orchestrator` runs without error for 60s
- [ ] `vault/Accounting/Current_Month.md` created by Finance Watcher in dev-mode
- [ ] `vault/Logs/YYYY-MM-DD.json` contains valid JSON-Lines entries
- [ ] No hardcoded secrets in any new file (grep for `sk-`, `EAA`, `Bearer`)
- [ ] `quickstart.md` reviewed; Odoo Docker, Meta token, Twitter setup verified end-to-end
