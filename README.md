# FTE System — Personal AI Employee

An autonomous AI business assistant that monitors your communication channels, reasons over incoming items, and takes actions on your behalf — with human-in-the-loop approval for anything sensitive.

**Current tier: Gold (Autonomous Business Operations)**

---

## What It Does

Drop a file into `vault/Watch/`. The system picks it up, triages it, generates a step-by-step action plan, executes low-risk steps automatically, and holds high-risk steps (like sending emails or creating invoices) in `vault/Pending_Approval/` until you approve them. Everything is tracked in an Obsidian-compatible Markdown vault.

```
vault/Watch/          ← drop files here
  ↓ filesystem watcher
vault/Inbox/          ← auto-tagged items
  ↓ triage skill
vault/Needs_Action/   ← classified items
  ↓ plan skill
vault/Plans/          ← generated action plans
  ↓ execute skill
vault/Pending_Approval/  ← HIGH/CRITICAL steps await your move
  ↓ you move to Approved/ or Rejected/
vault/Done/           ← completed items
vault/Logs/           ← JSON-Lines audit trail (Gold schema)
vault/Accounting/     ← Odoo transaction records
vault/Dashboard.md    ← live system status
```

---

## Architecture

| Layer | Component | Description |
|---|---|---|
| Perception | `FilesystemWatcher` + 3 Silver + 3 Gold watchers | Polls filesystem every 5 s; Gmail/WhatsApp/LinkedIn/Finance/Facebook/Twitter run as concurrent daemon threads |
| Vault | Obsidian Markdown | All state lives in human-readable `.md` files with YAML frontmatter |
| Reasoning | Skills (`src/skills/`) | Triage, plan, execute, detect_lead, generate_plan, linkedin_post, briefing, generate_invoice, accounting_audit, post_facebook, post_twitter — each a pure `run()` function |
| HITL | Approval workflow | HIGH/CRITICAL actions require file move to `vault/Approved/` |
| Action | `action_executor.py` + `odoo-mcp` | `send_email` (real SMTP), `create_invoice` (Odoo JSON-RPC), `post_social`, `update_calendar` |
| Safety | `core/` modules | Idempotency, rate limiting, opt-out list, `@with_retry` decorator, AI disclosure footer |
| Orchestration | `src/orchestrator.py` | Daemon with 7 watcher threads + scan cycle every 120 s + Ralph Wiggum autonomous loop |
| Health | `src/watchers/watchdog.py` | Auto-restarts dead watcher threads |
| Audit | JSON-Lines `vault/Logs/YYYY-MM-DD.json` | 9-field Gold schema; archives logs > 90 days |

---

## Quick Start

### 1. Install

```bash
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure

```bash
cp .env.example .env
# Edit .env — set DEV_MODE=true to simulate all actions (default)
```

### 3. Configure watchers (optional)

Edit `config/settings.yaml` to enable channels:

```yaml
watchers:
  gmail:
    enabled: true          # GMAIL_CLIENT_ID + GMAIL_CLIENT_SECRET in .env
  whatsapp:
    enabled: true          # requires setup_session() first
  linkedin:
    enabled: true          # reads engagement via browser-mcp
  finance:
    enabled: true          # ODOO_URL + ODOO_DB + ODOO_UID + ODOO_PASSWORD in .env
  facebook:
    enabled: true          # FACEBOOK_PAGE_ID + FACEBOOK_ACCESS_TOKEN in .env
  twitter:
    enabled: true          # TWITTER_* vars in .env
```

Without keys the relevant watchers are silently skipped; all other features work.

### 4. (Optional) Start Odoo for live finance

```bash
docker-compose -f docker-compose.odoo.yml up -d
# Odoo available at http://localhost:8069 — DB: fte_db
```

### 5. Run

```bash
python -m src.orchestrator
```

### 6. Test the pipeline

Drop a file into `vault/Watch/`:

```bash
cat > vault/Watch/test_item.md << 'EOF'
---
id: test_001
type: email
source: filesystem
status: new
priority: MEDIUM
timestamp: 2026-01-01T10:00:00
---

Hi, I'd like a quote for your consulting services.
EOF
```

Within seconds you'll see the file flow through the pipeline:

```
[scan]      1 file(s) in Inbox
[triage]    processed=1
[detect_lead] leads=1
[plan]      processed=1
[execute]   processed=3
```

### 7. Approve a pending action

Open any file in `vault/Pending_Approval/`. It shows the action details and risk level. Move it to `vault/Approved/` to execute, or `vault/Rejected/` to cancel.

---

## Run as Daemon (pm2)

```bash
npm install -g pm2
pm2 start ecosystem.config.js
pm2 logs fte-orchestrator
pm2 stop fte-orchestrator
```

---

## Project Structure

```
src/
  orchestrator.py          # main daemon (7 watcher threads + scan cycle)
  skills/
    triage_inbox.py        # classify incoming items          [Bronze]
    plan_task.py           # template-based plan generation   [Bronze]
    execute_plan.py        # run plan steps + HITL gating     [Bronze+]
    update_dashboard.py    # regenerate Dashboard.md          [Bronze+]
    check_handbook.py      # handbook compliance check        [Bronze]
    detect_lead.py         # keyword lead scoring → CRITICAL  [Silver]
    generate_plan.py       # Claude AI plan generation        [Silver]
    generate_linkedin_post.py  # AI draft + HIGH HITL        [Silver]
    weekly_briefing.py     # CEO briefing incl. finance data  [Silver+Gold]
    install_schedule.py    # cron/Task Scheduler + Stop hook  [Silver+Gold]
    uninstall_schedule.py  # remove scheduled tasks           [Silver]
    generate_invoice.py    # Odoo invoice via HITL            [Gold]
    accounting_audit.py    # cost-spike + subscription audit  [Gold]
    post_facebook.py       # Facebook/Instagram post + HITL   [Gold]
    post_twitter.py        # Twitter/X tweet + HITL           [Gold]
  watchers/
    filesystem_watcher.py  # polls vault/Watch/               [Bronze]
    gmail_watcher.py       # Gmail OAuth2 polling             [Silver]
    whatsapp_watcher.py    # WhatsApp Web via Playwright       [Silver]
    linkedin_watcher.py    # LinkedIn engagement reader        [Silver]
    finance_watcher.py     # Odoo primary + CSV fallback       [Gold]
    facebook_watcher.py    # Facebook engagement reader        [Gold]
    twitter_watcher.py     # Twitter/X timeline reader         [Gold]
    watchdog.py            # auto-restarts dead watcher threads[Gold]
  mcp_servers/
    odoo_mcp/
      client.py            # OdooMCPClient (JSON-RPC)          [Gold]
      server.py            # MCP stdio server                  [Gold]
  actions/
    action_executor.py     # send_email, create_invoice, post_social
  core/
    vault.py               # vault read/write helpers         [Bronze]
    audit_logger.py        # JSON-Lines Gold schema + compat  [Bronze+Gold]
    approval.py            # HITL approval detection          [Bronze]
    frontmatter.py         # YAML frontmatter parsing         [Bronze]
    idempotency.py         # dedup key store                  [Silver]
    rate_limiter.py        # per-action rate caps             [Silver]
    opt_out.py             # email opt-out enforcement        [Silver]
    retry_handler.py       # @with_retry + ErrorCategory      [Gold]
    ralph_loop.py          # autonomous plan completion loop   [Gold]
  hooks/
    stop_hook.py           # Ralph Wiggum stop hook            [Gold]

vault/                     # Obsidian vault (your working memory)
  Watch/
    gmail_mock/            finance_drop/
    whatsapp_mock/         facebook_mock/
    linkedin_mock/         twitter_mock/
  Inbox/         Needs_Action/    Plans/
  Pending_Approval/        Approved/        Rejected/
  Done/          Quarantine/      Briefings/
  Accounting/    Logs/Archive/    Templates/
  Dashboard.md   Opt_Out_List.md

config/
  settings.yaml            # watcher config, intervals, vault paths
  mcp_servers.yaml         # MCP server registry              [Gold]
  audit_logic.yaml         # subscription + cost-spike rules  [Gold]
  odoo/                    # Odoo connection config            [Gold]

specs/
  001-bronze-tier/         # Bronze spec, plan, tasks
  002-silver-tier/         # Silver spec, plan, tasks
  003-gold-tier/           # Gold spec, plan, tasks            [Gold]

docker-compose.odoo.yml    # Odoo 19 + PostgreSQL              [Gold]
```

---

## Configuration

Key settings in `config/settings.yaml`:

| Key | Default | Description |
|---|---|---|
| `watchers.filesystem.enabled` | `true` | Filesystem watcher on/off |
| `watchers.filesystem.poll_interval` | `5` | Seconds between polls |
| `watchers.gmail.enabled` | `false` | Gmail watcher (Silver) |
| `watchers.whatsapp.enabled` | `false` | WhatsApp watcher (Silver) |
| `watchers.finance.enabled` | `false` | Finance/Odoo watcher (Gold) |
| `watchers.facebook.enabled` | `false` | Facebook watcher (Gold) |
| `watchers.twitter.enabled` | `false` | Twitter watcher (Gold) |
| `orchestrator.scan_interval` | `120` | Seconds between scan cycles |
| `approval.expiry_hours` | `48` | Hours before approval requests expire |
| `audit.retention_days` | `90` | Days before logs archived |

Key env vars in `.env`:

| Variable | Description |
|---|---|
| `DEV_MODE` | `true` = simulate all actions, no real sends (default) |
| `DRY_RUN` | `true` = read-only, no vault writes |
| `ANTHROPIC_API_KEY` | Claude AI for plan generation; falls back to templates if absent |
| `ANTHROPIC_PLAN_MODEL` | Model for planning (default: `claude-haiku-4-5-20251001`) |
| `SMTP_HOST` / `SMTP_PORT` / `SMTP_USER` / `SMTP_PASSWORD` / `SMTP_FROM` | SMTP for real email sends |
| `GMAIL_CLIENT_ID` / `GMAIL_CLIENT_SECRET` | Gmail OAuth2 |
| `ODOO_URL` / `ODOO_DB` / `ODOO_UID` / `ODOO_PASSWORD` | Odoo finance (Gold) |
| `FACEBOOK_PAGE_ID` / `FACEBOOK_ACCESS_TOKEN` / `INSTAGRAM_USER_ID` | Facebook/IG (Gold) |
| `TWITTER_BEARER_TOKEN` / `TWITTER_API_KEY` / `TWITTER_API_SECRET` / `TWITTER_ACCESS_TOKEN` / `TWITTER_ACCESS_SECRET` / `TWITTER_USER_ID` | Twitter/X (Gold) |

---

## Tests

```bash
# Run all tests
python -m pytest tests/ -q

# With coverage report
python -m pytest tests/ --cov=src --cov-report=term-missing -q

# HTML coverage report
python -m pytest tests/ --cov=src --cov-report=html -q

# Specific tier
python -m pytest tests/ -k "sc02" -q    # Gold scenarios only
python -m pytest tests/ -k "sc01" -q    # Silver scenarios only
```

**749 tests, 76% coverage** — Bronze (SC-001–SC-009), Silver (SC-010–SC-020), and Gold (SC-021–SC-032) all verified.

---

## Gold Tier — What's New

Gold transforms the Silver multi-channel assistant into a fully autonomous business employee operating across personal + business domains.

### New Skills

| Skill | Description |
|---|---|
| `generate_invoice.py` | Parses invoice requests, extracts partner/amount/description, creates draft in Odoo via JSON-RPC. HIGH HITL gate before posting |
| `accounting_audit.py` | Detects subscription cost spikes and anomalous recurring charges from Odoo transaction data. Writes alerts to `vault/Needs_Action/` |
| `post_facebook.py` | AI-drafted Facebook Page post + Instagram Business cross-post. Single approval covers both platforms |
| `post_twitter.py` | AI-drafted tweet (≤ 280 chars), rate-capped at 1/day. HITL approval before posting |

### New Watchers

| Watcher | Enable | Description |
|---|---|---|
| `FinanceWatcher` | `watchers.finance.enabled: true` | Polls Odoo journal items every 5 min; CSV fallback when Odoo unavailable; dedup via `move_line_id`; month rollover archives to `YYYY-MM_transactions.md` |
| `FacebookWatcher` | `watchers.facebook.enabled: true` | Reads Page engagement metrics (reach, reactions, comments, shares) |
| `TwitterWatcher` | `watchers.twitter.enabled: true` | Reads timeline mentions and engagement via Bearer token |
| `WatchdogGold` | Always | Monitors all watcher threads; auto-restarts dead threads via `_restart_watcher()` |

### New Core Infrastructure

| Module | Description |
|---|---|
| `core/retry_handler.py` | `@with_retry(max_attempts=3, base_delay=1.0)` — exponential back-off with jitter. `ErrorCategory` enum: TRANSIENT retries; AUTH/LOGIC/DATA raise immediately |
| `core/ralph_loop.py` | Autonomous plan completion loop. Detects file movement (Done/Rejected) to exit. Hard cap: 10 iterations → quarantine on overflow |
| `hooks/stop_hook.py` | Claude Code Stop hook — signals Ralph loop on file-movement detection; registered by `install_schedule.py` |

### Odoo MCP Server

```
src/mcp_servers/odoo_mcp/
  client.py   # OdooMCPClient — direct Python import for in-process use
  server.py   # MCP stdio server — exposes 6 tools to Claude Code
```

Tools: `create_invoice`, `list_invoices`, `record_expense`, `get_account_balance`, `post_invoice`, `list_transactions`.

### Enhanced CEO Briefing (Gold)

Monday briefing now includes:

| Section | Source |
|---|---|
| Revenue this week | Odoo `account.move.line` |
| Expenses this week | Odoo journal entries |
| Bottlenecks | Items stuck > 48 h in `Needs_Action/` |
| Social Summary | Facebook + Twitter + LinkedIn engagement metrics |
| Proactive Suggestions | Claude-generated based on data patterns |

### Gold Audit Schema

All audit entries conform to the 9-field JSON-Lines schema:

```json
{
  "timestamp": "2026-03-01T09:00:00Z",
  "action_type": "create_invoice",
  "actor": "generate_invoice",
  "target": "Acme Corp",
  "parameters": {"amount": 1500.00, "currency": "USD"},
  "approval_status": "pending",
  "approved_by": null,
  "result": "pending_approval",
  "error": null
}
```

Logs rotate to `vault/Logs/Archive/` after `audit.retention_days` (default: 90).

### New Vault Folders

```
vault/Accounting/          ← Odoo transaction records (Current_Month.md)
vault/Logs/Archive/        ← Rotated audit logs
vault/Watch/finance_drop/  ← CSV fallback drop zone
vault/Watch/facebook_mock/ ← Facebook dev/test samples
vault/Watch/twitter_mock/  ← Twitter dev/test samples
```

---

## Silver Tier — What's New

Silver adds multi-channel perception, AI reasoning, and safety infrastructure on top of the unchanged Bronze foundation.

### New Skills

| Skill | Description |
|---|---|
| `detect_lead.py` | Scores items for buying signals (keywords: budget, quote, demo, partnership…). Items scoring ≥ 2 are upgraded to `type: lead`, `priority: CRITICAL` |
| `generate_plan.py` | Calls Claude API; includes `## Reasoning` trace. Falls back to Bronze templates when API key absent or `DEV_MODE=true` |
| `generate_linkedin_post.py` | AI-drafted LinkedIn post with HIGH HITL gate. All posts include `#AIAssisted` tag |
| `weekly_briefing.py` | Aggregates vault audit logs into `vault/Briefings/BRIEFING_<date>.md` |
| `install_schedule.py` | Registers orchestrator at startup + Monday 08:00 briefing via Task Scheduler / crontab. Idempotent |

### New Watchers

| Watcher | Enable | Description |
|---|---|---|
| `GmailWatcher` | `watchers.gmail.enabled: true` | OAuth2 polling; `message_id` dedup; token auto-refreshes |
| `WhatsAppWatcher` | `watchers.whatsapp.enabled: true` | WhatsApp Web via Playwright; `setup_session()` first |
| `LinkedInWatcher` | `watchers.linkedin.enabled: true` | Post engagement metrics via browser-mcp |

### New Safety Infrastructure

| Module | Description |
|---|---|
| `core/idempotency.py` | Content-hash dedup — prevents duplicate sends across restarts |
| `core/rate_limiter.py` | 20 emails/h, 5 LinkedIn posts/h, 10 invoices/h |
| `core/opt_out.py` | Checks `vault/Opt_Out_List.md` before every outbound email |
| AI footer | `"This message was drafted with AI assistance."` on every outbound email |
| Quarantine | Plans failing 3+ times move to `vault/Quarantine/` |

---

## Success Criteria

### Bronze (SC-001–SC-009)

| ID | Criterion | Status |
|---|---|---|
| SC-001 | All tests pass with 0 failures | ✅ |
| SC-002 | Orchestrator starts, filesystem watcher + watchdog running | ✅ |
| SC-003 | Drop file → full pipeline within 60 s | ✅ |
| SC-004 | `Dashboard.md` reflects vault state after each scan cycle | ✅ |
| SC-005 | Every pipeline action produces an audit entry in `vault/Logs/` | ✅ |
| SC-006 | HIGH/CRITICAL actions block until human approves/rejects | ✅ |
| SC-007 | Re-running executor on same plan does not duplicate approval requests | ✅ |
| SC-008 | `pm2 start ecosystem.config.js` keeps orchestrator running as daemon | ✅ |
| SC-009 | Silver/Gold stub watchers exist as importable classes | ✅ |

### Silver (SC-010–SC-020)

| ID | Criterion | Status |
|---|---|---|
| SC-010 | Gmail watcher processes mock items without errors | ✅ |
| SC-011 | WhatsApp watcher processes mock messages without errors | ✅ |
| SC-012 | Four concurrent watcher threads running (filesystem + 3 Silver) | ✅ |
| SC-013 | Lead detection end-to-end: buying-signal item → CRITICAL plan → email approval | ✅ |
| SC-014 | Real email send via SMTP (gated on `DEV_MODE=false` + SMTP config) | ✅ |
| SC-015 | LinkedIn post drafted, approved via HITL, marked published | ✅ |
| SC-016 | Claude plan reasoning: plans include `## Reasoning` section when API key present | ✅ |
| SC-017 | Weekly briefing written to `vault/Briefings/BRIEFING_<date>.md` | ✅ |
| SC-018 | `install_schedule.py` registers tasks idempotently; `uninstall_schedule.py` removes them | ✅ |
| SC-019 | Item with `failure_count >= 3` is quarantined, not retried indefinitely | ✅ |
| SC-020 | All 531 tests pass; coverage ≥ 70% | ✅ |

### Gold (SC-021–SC-032)

| ID | Criterion | Status |
|---|---|---|
| SC-021 | Finance Watcher writes Odoo (or CSV fallback) transactions to `vault/Accounting/Current_Month.md` | ✅ |
| SC-022 | Finance Watcher falls back to CSV when Odoo unavailable; dedup by hash | ✅ |
| SC-023 | `generate_invoice` creates Odoo draft on approval (simulated in DEV_MODE) | ✅ |
| SC-024 | Facebook post drafted, HITL approval, published (simulated in DEV_MODE) | ✅ |
| SC-025 | Tweet drafted (≤ 280 chars), HITL approval, posted (simulated in DEV_MODE) | ✅ |
| SC-026 | Monday CEO Briefing includes Revenue, Expense, Bottleneck, Social Summary sections | ✅ |
| SC-027 | `@with_retry` recovers transient failure within 3 attempts with exponential back-off | ✅ |
| SC-028 | Ralph Wiggum loop drives multi-step plan to `vault/Done/` without re-prompting | ✅ |
| SC-029 | All audit entries conform to 9-field Gold JSON schema | ✅ |
| SC-030 | All 531 Silver + 385 Bronze tests pass with zero regressions | ✅ |
| SC-031 | Silver `log_action()` wrapper still works; produces Gold JSON-Lines entry | ✅ |
| SC-032 | Month rollover archives prior month transactions; new month file created | ✅ |

---

## HITL Safety Model

All actions are classified by risk level:

| Risk | Approval | Examples |
|---|---|---|
| LOW | Auto-execute | File operations, calendar reads, engagement reads |
| MEDIUM | Notify only | Draft creation, internal notes |
| HIGH | Explicit approval required | Send email, create invoice, publish post |
| CRITICAL | Explicit approval + confirm | Bulk sends, financial posts, account changes |

In `DEV_MODE=true` (default), **no real external calls are made**. All actions are simulated and logged.

---

## Tiers

| Tier | Status | Tests | Description |
|---|---|---|---|
| Bronze | **Complete** | 385 | Filesystem watcher, full pipeline, HITL, dashboard, audit, pm2 daemon |
| Silver | **Complete** | 531 | Gmail/WhatsApp/LinkedIn watchers, Claude AI planning, lead detection, scheduling |
| Gold | **Complete** | 749 | Odoo finance, Facebook/Instagram/Twitter, invoice generation, retry handler, Ralph loop, Gold audit |
