# FTE System — Personal AI Employee

An autonomous AI business assistant that monitors your communication channels, reasons over incoming items, and takes actions on your behalf — with human-in-the-loop approval for anything sensitive.

**Current tier: Silver (Multi-Channel AI Layer)**

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
vault/Logs/           ← full audit trail
vault/Dashboard.md    ← live system status
```

---

## Architecture

| Layer | Component | Description |
|---|---|---|
| Perception | `FilesystemWatcher` + 3 Silver watchers | Polls filesystem every 5 s; Gmail/WhatsApp/LinkedIn run as concurrent daemon threads |
| Vault | Obsidian Markdown | All state lives in human-readable `.md` files with YAML frontmatter |
| Reasoning | Skills (`src/skills/`) | Triage, plan, execute, detect_lead, generate_plan, linkedin_post, briefing — each a pure `run()` function |
| HITL | Approval workflow | HIGH/CRITICAL actions require file move to `vault/Approved/` |
| Action | `action_executor.py` | `send_email` (real SMTP), `create_invoice`, `post_social`, `update_calendar` |
| Safety | `core/` modules | Idempotency, rate limiting (20 emails/h), opt-out list, AI disclosure footer |
| Orchestration | `src/orchestrator.py` | Daemon with 4 watcher threads + scan cycle every 120 s |
| Health | `watchdog_monitor.py` | Auto-restarts the orchestrator if it crashes |

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

### 3. Configure (Silver)

To activate Gmail, WhatsApp, or LinkedIn watchers edit `config/settings.yaml`:

```yaml
watchers:
  gmail:
    enabled: true          # requires GMAIL_CLIENT_ID + GMAIL_CLIENT_SECRET in .env
  whatsapp:
    enabled: true          # requires running setup_session() first
  linkedin:
    enabled: true          # reads engagement via browser-mcp
```

To use Claude AI for plan generation, set `ANTHROPIC_API_KEY` in `.env`. Without it, the system falls back to Bronze template-based plans automatically.

To send real emails (not simulated), set `DEV_MODE=false` and configure SMTP vars in `.env`.

### 4. Run

```bash
python -m src.orchestrator
```

You should see:

```
[orchestrator] Starting with 1 watcher(s)
[orchestrator] Vault: /path/to/vault
[orchestrator] DEV_MODE: True
[orchestrator] Press Ctrl+C to stop
[orchestrator] Watchers and monitor started
[orchestrator] Running initial scan...
[orchestrator] Ready. Watching for files...
```

### 5. Test the pipeline

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

Then open `vault/Dashboard.md` in Obsidian to see live status.

### 6. Approve a pending action

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
  orchestrator.py          # main daemon (4 watcher threads + scan cycle)
  watchdog_monitor.py      # auto-restart monitor
  skills/
    triage_inbox.py        # classify incoming items          [Bronze]
    plan_task.py           # template-based plan generation   [Bronze]
    execute_plan.py        # run plan steps + HITL gating     [Bronze+]
    update_dashboard.py    # regenerate Dashboard.md          [Bronze+]
    check_handbook.py      # handbook compliance check        [Bronze]
    detect_lead.py         # keyword lead scoring → CRITICAL  [Silver]
    generate_plan.py       # Claude AI plan generation        [Silver]
    generate_linkedin_post.py  # AI draft + HIGH HITL        [Silver]
    weekly_briefing.py     # weekly CEO briefing to vault     [Silver]
    install_schedule.py    # register cron/Task Scheduler     [Silver]
    uninstall_schedule.py  # remove scheduled tasks           [Silver]
  watchers/
    filesystem_watcher.py  # polls vault/Watch/               [Bronze]
    gmail_watcher.py       # Gmail OAuth2 polling             [Silver]
    whatsapp_watcher.py    # WhatsApp Web via Playwright       [Silver]
    linkedin_watcher.py    # LinkedIn engagement reader        [Silver]
  actions/
    action_executor.py     # send_email (SMTP), create_invoice, post_social, ...
  core/
    vault.py               # vault read/write helpers         [Bronze]
    audit_logger.py        # structured audit entries         [Bronze]
    approval.py            # HITL approval detection          [Bronze]
    frontmatter.py         # YAML frontmatter parsing         [Bronze]
    idempotency.py         # dedup key store                  [Silver]
    rate_limiter.py        # per-action rate caps             [Silver]
    opt_out.py             # email opt-out enforcement        [Silver]

vault/                     # Obsidian vault (your working memory)
  Watch/                   # drop files here
    gmail_mock/            # mock Gmail items for dev/test
    whatsapp_mock/         # mock WhatsApp messages
    linkedin_mock/         # mock LinkedIn engagement
  Inbox/                   # auto-triaged items
  Needs_Action/            # awaiting planning
  Plans/                   # generated plans
  Pending_Approval/        # awaiting your decision
  Approved/                # approved → executes
  Rejected/                # rejected → terminal
  Done/                    # completed items
  Logs/                    # audit trail
  Briefings/               # weekly CEO briefings             [Silver]
  Quarantine/              # items that failed 3+ times       [Silver]
  Opt_Out_List.md          # email addresses to never contact [Silver]
  Templates/               # LinkedIn post prompt templates   [Silver]
  Dashboard.md             # live system status

specs/
  001-bronze-tier/         # Bronze spec, plan, tasks
  002-silver-tier/         # Silver spec, plan, tasks, contracts, data-model

config/
  settings.yaml            # watcher config, intervals, vault paths
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
| `orchestrator.scan_interval` | `120` | Seconds between scan cycles |
| `approval.expiry_hours` | `48` | Hours before approval requests expire |

Key env vars in `.env`:

| Variable | Description |
|---|---|
| `DEV_MODE` | `true` = simulate all actions, no real sends (default) |
| `DRY_RUN` | `true` = read-only, no vault writes |
| `ANTHROPIC_API_KEY` | Claude AI for plan generation; falls back to templates if absent |
| `ANTHROPIC_PLAN_MODEL` | Model for planning (default: `claude-haiku-4-5-20251001`) |
| `SMTP_HOST` | SMTP server for real email sends (e.g. `smtp.gmail.com`) |
| `SMTP_PORT` | SMTP port (default: `587`) |
| `SMTP_USER` | SMTP login address |
| `SMTP_PASSWORD` | SMTP app password |
| `SMTP_FROM` | Display from address |
| `GMAIL_CLIENT_ID` | Gmail OAuth2 client ID |
| `GMAIL_CLIENT_SECRET` | Gmail OAuth2 client secret |

---

## Tests

```bash
# Run all tests
python -m pytest tests/ -q

# With coverage
python -m pytest tests/ --cov=src --cov-report=term-missing -q

# Specific module
python -m pytest tests/test_execute_plan.py -v
```

**531 tests, 73% coverage** — Bronze (SC-001–SC-009) and Silver (SC-010–SC-020) criteria all verified.

---

## Silver Tier — What's New

Silver adds multi-channel perception, AI reasoning, and safety infrastructure on top of the unchanged Bronze foundation.

### New Skills

| Skill | Description |
|---|---|
| `detect_lead.py` | Scores items for buying signals (keywords: budget, quote, demo, partnership…). Items scoring ≥ 2 are upgraded to `type: lead`, `priority: CRITICAL` and routed to a lead response plan |
| `generate_plan.py` | Calls Claude API to generate plans with intent summary, step rationale, and a `## Reasoning` trace. Falls back to Bronze templates when `ANTHROPIC_API_KEY` is absent or `DEV_MODE=true` |
| `generate_linkedin_post.py` | AI-drafted LinkedIn post with HIGH HITL approval gate. All posts include `#AIAssisted` tag |
| `weekly_briefing.py` | Aggregates vault audit logs into `vault/Briefings/BRIEFING_<date>.md` — items by channel, leads, emails sent, LinkedIn posts, approvals, quarantined items, next-week recommendations |
| `install_schedule.py` | Registers orchestrator at system startup + weekly briefing at Monday 08:00 via Windows Task Scheduler or crontab. Idempotent — safe to run multiple times |

### New Watchers (disabled by default)

| Watcher | Enable | Description |
|---|---|---|
| `GmailWatcher` | `watchers.gmail.enabled: true` | OAuth2 polling; uses `message_id` for dedup; token auto-refreshes |
| `WhatsAppWatcher` | `watchers.whatsapp.enabled: true` | WhatsApp Web via Playwright; requires `setup_session()` first |
| `LinkedInWatcher` | `watchers.linkedin.enabled: true` | Reads post engagement metrics via browser-mcp |

### New Safety Infrastructure

| Module | Description |
|---|---|
| `core/idempotency.py` | Content-hash dedup store — prevents duplicate email sends or posts across restarts |
| `core/rate_limiter.py` | Caps sends per hour: 20 emails, 5 LinkedIn posts, 10 invoices |
| `core/opt_out.py` | Checks `vault/Opt_Out_List.md` before every outbound email |
| AI footer | `"This message was drafted with AI assistance."` appended to every outbound email |
| Quarantine | Plans that fail 3+ times are moved to `vault/Quarantine/` with a MEDIUM audit entry |
| Queue drain | Queued (rate-limited) actions are retried on the next scan cycle |

### New Vault Folders

```
vault/Briefings/     ← weekly CEO briefing documents
vault/Quarantine/    ← plans isolated after 3 failures
vault/Opt_Out_List.md
vault/Templates/     ← LinkedIn post prompt templates
vault/Watch/
  gmail_mock/        ← sample items for Gmail dev/test
  whatsapp_mock/     ← sample items for WhatsApp dev/test
  linkedin_mock/     ← sample items for LinkedIn dev/test
```

---

## Bronze Tier Success Criteria

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

## Silver Tier Success Criteria

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

---

## HITL Safety Model

All actions are classified by risk level:

| Risk | Approval | Examples |
|---|---|---|
| LOW | Auto-execute | File operations, calendar reads |
| MEDIUM | Notify only | Draft creation, internal notes |
| HIGH | Explicit approval required | Send email, create invoice |
| CRITICAL | Explicit approval + confirm | Bulk sends, financial posts |

In `DEV_MODE=true` (default), **no real external calls are made**. All actions are simulated and logged.

---

## Tiers

| Tier | Status | Description |
|---|---|---|
| Bronze | **Complete** | Filesystem watcher, full pipeline, HITL, dashboard, audit, pm2 daemon |
| Silver | **Complete** | Gmail/WhatsApp/LinkedIn watchers, Claude AI planning, lead detection, scheduling |
| Gold | Planned | Odoo finance integration, Slack, advanced reasoning loop |
