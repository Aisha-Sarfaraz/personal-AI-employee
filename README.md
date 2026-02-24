# FTE System — Personal AI Employee

An autonomous AI business assistant that monitors your communication channels, reasons over incoming items, and takes actions on your behalf — with human-in-the-loop approval for anything sensitive.

**Current tier: Bronze (Foundation Layer)**

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
| Perception | `FilesystemWatcher` | Polls `vault/Watch/` every 5 s, creates frontmatter-tagged `.md` items |
| Vault | Obsidian Markdown | All state lives in human-readable `.md` files with YAML frontmatter |
| Reasoning | Skills (`src/skills/`) | Triage, plan, execute, dashboard update — each a pure `run()` function |
| HITL | Approval workflow | HIGH/CRITICAL actions require file move to `vault/Approved/` |
| Action | `action_executor.py` | `send_email`, `create_invoice`, `post_social`, `update_calendar` |
| Orchestration | `src/orchestrator.py` | Daemon that drives the full pipeline every scan cycle |
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

### 3. Run

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

### 4. Test the pipeline

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

### 5. Approve a pending action

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
  orchestrator.py          # main daemon
  watchdog_monitor.py      # auto-restart monitor
  skills/
    triage_inbox.py        # classify incoming items
    plan_task.py           # generate action plans
    execute_plan.py        # run plan steps + HITL gating
    update_dashboard.py    # regenerate Dashboard.md
    detect_lead.py         # keyword-based lead scoring
    generate_plan.py       # Claude AI plan generation
    generate_linkedin_post.py
    weekly_briefing.py
    install_schedule.py    # schedule orchestrator via cron/Task Scheduler
    uninstall_schedule.py
  watchers/
    filesystem_watcher.py  # active (Bronze)
    gmail_watcher.py       # Silver (disabled by default)
    whatsapp_watcher.py    # Silver (disabled by default)
    linkedin_watcher.py    # Silver (disabled by default)
  actions/
    action_executor.py     # send_email, create_invoice, post_social, ...
  core/
    vault.py               # vault read/write helpers
    audit_logger.py        # structured audit entries
    approval.py            # HITL approval detection
    idempotency.py         # dedup store (Silver)
    rate_limiter.py        # per-action rate limits (Silver)
    opt_out.py             # email opt-out list (Silver)

vault/                     # Obsidian vault (your working memory)
  Watch/                   # drop files here
  Inbox/                   # auto-triaged items
  Needs_Action/            # awaiting planning
  Plans/                   # generated plans
  Pending_Approval/        # awaiting your decision
  Approved/                # approved → executes
  Rejected/                # rejected → terminal
  Done/                    # completed items
  Logs/                    # audit trail
  Dashboard.md             # live status

specs/
  001-bronze-tier/         # Bronze spec, plan, tasks
  002-silver-tier/         # Silver spec, plan, tasks

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
| `DEV_MODE` | `true` = simulate all actions, no real sends |
| `DRY_RUN` | `true` = read-only, no vault writes |
| `ANTHROPIC_API_KEY` | Claude AI for plan generation (Silver) |
| `SMTP_HOST/PORT/USER/PASSWORD` | Real email send (Silver, requires `DEV_MODE=false`) |
| `GMAIL_CLIENT_ID/SECRET` | Gmail OAuth2 (Silver) |

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
