# Gold Tier Data Model

**Feature**: 003-gold-tier
**Date**: 2026-02-25
**Status**: COMPLETE
**Branch**: 003-gold-tier

---

## Overview

Gold Tier adds five new logical entities to the Silver data model. All Silver entities
(`InboxItem`, `WatcherState`, `ActionFile`, `AuditEntry`) are preserved unchanged; Gold
extends `AuditEntry` and adds new entities.

---

## Entity 1 — FinanceTransaction

Represents a single financial transaction sourced from Odoo or a CSV file.

```yaml
FinanceTransaction:
  id: str                  # Odoo move_line_id or SHA-256(date+description+amount)
  date: str                # ISO date YYYY-MM-DD
  description: str         # free text from Odoo or CSV
  amount: float            # signed decimal; negative = expense
  account: str             # Odoo account name or CSV account column
  source: enum             # "odoo" | "csv"
  processed_at: str        # ISO8601 timestamp when added to vault
```

**Dedup key**: `id` field. Persisted in `vault/state/finance_processed_ids.json` as a
JSON array of string IDs. Survives orchestrator restarts.

**Storage**:
- Live transactions: `vault/Accounting/Current_Month.md` (Markdown table)
- Month rollover: archived to `vault/Accounting/YYYY-MM_transactions.md`
- ID store: `vault/state/finance_processed_ids.json`

**Markdown table row format**:
```
| YYYY-MM-DD | description | +/-amount | account |
```

---

## Entity 2 — AuditEntry (Gold Extension)

Extends the Silver `AuditEntry` with a structured JSON-Lines schema. Silver callers using
the two-argument legacy signature continue to work via a backward-compatible wrapper.

```yaml
AuditEntry (Gold):
  timestamp: str           # ISO8601; mandatory
  action_type: str         # e.g. "create_invoice", "post_tweet", "watchdog_restart"; mandatory
  actor: str               # "claude_code" | "orchestrator" | "watcher:<name>" | "mcp:<server>"; mandatory
  target: str              # resource acted upon (file path, partner name, post URL); mandatory
  parameters: dict         # action-specific kwargs (e.g. {amount: 100.0, partner: "ACME"})
  approval_status: enum    # "auto" | "approved" | "rejected" | "pending"; mandatory
  approved_by: enum        # "human" | "system" | null; mandatory
  result: enum             # "success" | "failure" | "skipped" | "degraded"; mandatory
  error: str | null        # error message on failure; null on success
```

**Storage**: `vault/Logs/YYYY-MM-DD.json` (one JSON object per line, newline-delimited).
**Archive**: Files older than 90 days moved to `vault/Logs/Archive/` on orchestrator startup.
**Backward compatibility**: `audit_logger.log(action, details)` two-arg call wraps to
`action_type=action`, `parameters={"details": details}`, `actor="orchestrator"`, etc.

---

## Entity 3 — RalphLoopState

State file used by the Ralph Wiggum autonomous loop. Written by `ralph_loop.py` and read
by the `stop_hook.py` at each Claude Code session exit.

```yaml
RalphLoopState:
  task_file: str           # absolute path to vault/Plans/PLAN_<id>.md
  prompt: str              # the injected prompt text for each iteration
  iteration: int           # current iteration number (1-based)
  status: enum             # "running" | "done" | "cancelled" | "quarantined"
```

**Storage**: `vault/state/ralph_loop_state.json` (single JSON object, overwritten each iteration).

**Lifecycle**:
```
ralph_loop.py writes {status: "running", iteration: N}
  → Claude Code runs
  → stop_hook.py reads state file
     → task_file moved to vault/Done/ ? → writes {status: "done"} → exit 0
     → task_file NOT done + iteration < max → re-inject prompt → continue
     → task_file NOT done + iteration >= max → writes {status: "quarantined"}
                                              → moves task_file to vault/Quarantine/
```

---

## Entity 4 — OdooInvoice

Represents an invoice drafted and optionally posted in Odoo 19+. Used by `generate_invoice.py`
and `OdooMCPClient`.

```yaml
OdooInvoice:
  id: str                  # Odoo `account.move` ID (assigned by Odoo on create)
  partner: str             # customer/vendor name
  amount: float            # total amount (positive)
  currency: str            # ISO 4217 (default: "USD" from settings)
  description: str         # line item description
  move_type: enum          # "out_invoice" (customer) | "in_invoice" (vendor)
  state: enum              # "draft" | "posted" | "cancelled"
  approval_file: str       # path to vault/Pending_Approval/INVOICE_<ts>.md
  created_at: str          # ISO8601
```

**Approval file frontmatter** (`vault/Pending_Approval/INVOICE_<timestamp>.md`):
```yaml
---
type: invoice_approval
partner: ACME Corp
amount: 1250.00
description: Consulting services — Feb 2026
move_type: out_invoice
risk_level: HIGH
requires_approval: true
created_at: 2026-02-25T10:00:00Z
---
```

---

## Entity 5 — SocialPost

Represents a drafted social media post pending approval or published. Covers Facebook +
Instagram (cross-post) and Twitter/X.

```yaml
SocialPost:
  id: str                  # timestamp-based unique ID
  platforms: list[str]     # ["facebook", "instagram"] or ["twitter"]
  draft_text: str          # post content (≤280 chars for Twitter)
  character_count: int     # relevant for Twitter gate
  status: enum             # "draft" | "pending_approval" | "published" | "failed"
  approval_file: str       # path to vault/Pending_Approval/FB_POST_<ts>.md or TWEET_<ts>.md
  published_at: str | null # ISO8601; null until published
  platform_ids: dict       # {"facebook": "post-id", "instagram": "media-id", "twitter": "tweet-id"}
  risk_level: str          # "HIGH" (all social posts require explicit approval)
```

**Approval file frontmatter** (`vault/Pending_Approval/FB_POST_<timestamp>.md`):
```yaml
---
type: social_post_approval
platforms: [facebook, instagram]
draft_text: "Excited to announce our Q1 milestone..."
character_count: 52
risk_level: HIGH
requires_approval: true
created_at: 2026-02-25T10:00:00Z
---
```

**Approval file frontmatter** (`vault/Pending_Approval/TWEET_<timestamp>.md`):
```yaml
---
type: social_post_approval
platforms: [twitter]
draft_text: "Q1 milestone achieved ✓ Thread below..."
character_count: 44
risk_level: HIGH
requires_approval: true
created_at: 2026-02-25T10:00:00Z
---
```

---

## Entity 6 — WatcherHealth (Orchestrator Runtime, Gold Extended)

Already defined in Silver; Gold extends with `failure_count` and `last_restart`.

```yaml
WatcherHealth:
  name: str                # watcher identifier (e.g. "finance", "facebook", "twitter")
  status: enum             # "healthy" | "degraded" | "stopped" | "restarting"
  last_checked: str        # ISO8601
  failure_count: int       # [GOLD] consecutive restart failures (reset to 0 on success)
  last_restart: str | null # [GOLD] ISO8601 of most recent watchdog restart
  error: str | null        # last error message if status != healthy
```

**Storage**: In-memory dict in `orchestrator.py` (`_watcher_health`). Not persisted.

---

## State File Summary

| File | Entity | Format |
|------|--------|--------|
| `vault/state/finance_processed_ids.json` | FinanceTransaction dedup set | JSON array of strings |
| `vault/state/ralph_loop_state.json` | RalphLoopState | JSON object |
| `vault/state/rate_limits.json` | Rate limit counters (Silver) | JSON object (unchanged) |
| `vault/Logs/YYYY-MM-DD.json` | AuditEntry (Gold) | JSON-Lines |
| `vault/Logs/Archive/` | AuditEntry archive | JSON-Lines files |
| `vault/Accounting/Current_Month.md` | FinanceTransaction rows | Markdown table |
| `vault/Accounting/YYYY-MM_transactions.md` | Monthly archive | Markdown table |

---

## Vault Folder Extensions (Gold Additions)

```
vault/
├── Accounting/                   # [GOLD] financial transaction logs
│   ├── Current_Month.md          # live Markdown table
│   └── YYYY-MM_transactions.md   # month-rollover archives
├── Logs/
│   └── Archive/                  # [GOLD] logs older than 90 days moved here
├── Watch/
│   ├── finance_mock/             # [GOLD] dev-mode JSON fixtures for FinanceWatcher
│   │   └── sample_transactions.json
│   ├── finance_drop/             # [GOLD] CSV fallback drop folder
│   │   └── .gitkeep
│   ├── facebook_mock/            # [GOLD] dev-mode JSON fixtures for FacebookWatcher
│   │   └── sample_post.json
│   └── twitter_mock/             # [GOLD] dev-mode JSON fixtures for TwitterWatcher
│       └── sample_tweet.json
└── state/
    ├── finance_processed_ids.json # [GOLD]
    └── ralph_loop_state.json      # [GOLD]
```
