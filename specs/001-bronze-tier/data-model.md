# Data Model: Bronze Tier

**Feature:** 001-bronze-tier
**Date:** 2026-02-17

---

## Entities

### 1. Vault Item (Inbox/Needs_Action file)

A Markdown file that moves through the pipeline. Created by watchers, triaged by skills.

**Frontmatter Schema:**

```yaml
---
id: string            # Unique ID: "{SOURCE}_{timestamp}_{name}" (e.g., "FILE_20260217_143022_invoice")
type: string           # One of: financial | communication | task | document | general | unknown
source: string         # Origin: "filesystem_watcher" | "gmail_watcher" | "whatsapp_watcher" | "finance_watcher" | "manual"
timestamp: string      # ISO-8601 creation time (e.g., "2026-02-17T14:30:22")
priority: string       # One of: CRITICAL | HIGH | MEDIUM | LOW
status: string         # One of: new | triaged | planned | in_progress | completed | rejected | expired
original_filename: string  # Original filename from Watch folder (if applicable)
tags: list[string]     # Optional classification tags (e.g., ["invoice", "vendor-abc"])
---
```

**Body:** Original file content (text) or "[Binary file — cannot display]" for non-text files.

**Identity:** `id` field is unique. Generated from source + timestamp + sanitized filename.

**Validation:**
- `type` must be one of the enum values
- `priority` must be one of the enum values
- `status` must be one of the enum values
- `timestamp` must be valid ISO-8601
- `id` must be non-empty

---

### 2. Plan (Plans/ file)

A Markdown file representing an execution plan for a triaged item.

**Frontmatter Schema:**

```yaml
---
id: string              # Unique ID: "PLAN_{timestamp}_{item_id}"
source_item: string     # ID of the originating Vault Item
type: string            # Copied from source item's type
priority: string        # Copied from source item's priority
status: string          # One of: pending | executing | completed | rejected | error
created: string         # ISO-8601 creation timestamp
updated: string         # ISO-8601 last update timestamp
step_count: int         # Number of steps in the plan
steps_completed: int    # Number of steps successfully executed
step_action_ids: dict   # Map of step_number → approval_request_uuid (for idempotent re-execution)
---
```

**Body:** Markdown with numbered steps:

```markdown
## Steps

### Step 1: [description]
- **action_type**: send_email | create_invoice | post_social | update_calendar | file_operation
- **description**: Human-readable description of the action
- **risk_level**: LOW | MEDIUM | HIGH | CRITICAL
- **requires_approval**: true | false
- **status**: pending | approved | executing | completed | skipped | rejected

### Step 2: [description]
...
```

**Identity:** `id` field. Links to source item via `source_item`.

**Validation:**
- `source_item` must reference an existing item
- Each step must have `action_type`, `risk_level`, `requires_approval`
- `step_action_ids` must be a valid dict (empty `{}` initially)

---

### 3. Approval Request (Pending_Approval/ file)

A Markdown file requesting human approval for a HIGH/CRITICAL action.

**Frontmatter Schema:**

```yaml
---
id: string              # UUID v4 (e.g., "a1b2c3d4-e5f6-7890-abcd-ef1234567890")
plan_id: string         # ID of the originating Plan
step_number: int        # Which step in the plan requires approval
action_type: string     # The action being requested
action_description: string  # Human-readable description
risk_level: string      # HIGH | CRITICAL
created: string         # ISO-8601 creation timestamp
expires: string         # ISO-8601 expiry timestamp (created + 24 hours)
status: string          # One of: pending | approved | rejected | expired
---
```

**Body:** Context for the human reviewer:

```markdown
## Action Details

**Action:** [description]
**Risk Level:** [HIGH/CRITICAL]
**Source:** [originating item summary]
**Plan:** [plan ID]

## Instructions

- Move this file to `vault/Approved/` to approve
- Move this file to `vault/Rejected/` to deny
- This request expires at [expiry time]
```

**Identity:** `id` (UUID). Links to plan via `plan_id` + `step_number`.

**Validation:**
- `risk_level` must be HIGH or CRITICAL (LOW/MEDIUM don't create approval requests)
- `expires` must be exactly 24 hours after `created`
- `id` must be UUID format

---

### 4. Audit Entry (Logs/ file)

A Markdown file recording an action taken by the system.

**Frontmatter Schema:**

```yaml
---
id: string              # "AUDIT_{timestamp}_{agent}_{action_hash}"
timestamp: string       # ISO-8601 timestamp
agent: string           # Which skill/component performed the action
action: string          # Brief action description
risk_tier: string       # LOW | MEDIUM | HIGH | CRITICAL
status: string          # success | failure | skipped | expired
related_item: string    # ID of the related Vault Item or Plan (if applicable)
details: string         # Additional context
---
```

**Body:** Human-readable summary of the action and its result.

**Identity:** `id` field. `related_item` links to the originating entity.

---

### 5. Watcher State (vault/state/watcher_state.json)

A JSON file persisting processed item IDs for deduplication.

**Schema:**

```json
{
  "watcher_name": "filesystem_watcher",
  "last_updated": "2026-02-17T14:30:22",
  "processed_ids": {
    "file_hash_or_name": {
      "timestamp": "2026-02-17T14:30:22",
      "filename": "test_invoice.txt",
      "status": "processed"
    }
  }
}
```

**Identity:** One file per watcher. Keyed by filename or content hash.

---

### 6. Configuration (config/settings.yaml)

**Schema:**

```yaml
vault:
  root: "vault"
  folders:
    inbox: "Inbox"
    needs_action: "Needs_Action"
    plans: "Plans"
    done: "Done"
    logs: "Logs"
    pending_approval: "Pending_Approval"
    approved: "Approved"
    rejected: "Rejected"
    watch: "Watch"
  state_dir: "state"

watchers:
  filesystem:
    enabled: true
    watch_folder: "vault/Watch"
    poll_interval: 5  # seconds
    stability_wait: 2  # seconds to wait for file write completion
  gmail:
    enabled: false
  whatsapp:
    enabled: false
  finance:
    enabled: false

orchestrator:
  scan_interval: 30  # seconds between scan cycles
  max_plan_age_hours: 48  # plans older than this are flagged as stuck

approval:
  expiry_hours: 24
  check_interval: 10  # seconds between approval status checks

dev_mode: true  # When true, all external actions are simulated

logging:
  level: "INFO"
  audit_format: "markdown"  # Bronze: markdown, Gold+: json
```

---

## State Transitions

### Vault Item Lifecycle

```
[new] → (triage_inbox) → [triaged] → (plan_task) → [planned] → (execute_plan) → [in_progress]
                                                                                      ↓
                                                               [completed] ← (all steps done)
                                                               [rejected]  ← (approval denied)
                                                               [expired]   ← (approval timeout)
```

**Folder mapping:**
| Status | Vault Folder |
|--------|-------------|
| new | /Inbox |
| triaged | /Needs_Action |
| planned | /Plans (as Plan entity) |
| in_progress | /Plans (plan executing) |
| completed | /Done |
| rejected | /Done (with rejection metadata) |
| expired | /Needs_Action (re-queued) |

### Plan Lifecycle

```
[pending] → (execute_plan starts) → [executing] → [completed] (all steps done)
                                         ↓
                                    [rejected] (approval denied → terminal)
                                    [error] (unrecoverable failure)
```

### Approval Request Lifecycle

```
[pending] → (human moves to /Approved) → [approved]
         → (human moves to /Rejected) → [rejected]
         → (24h expiry) → [expired]
```

---

## Entity Relationships

```
Vault Item (1) ←→ (1) Plan
Plan (1) ←→ (0..N) Approval Request
Any Entity (1) ←→ (0..N) Audit Entry
Watcher State (1) ←→ (N) processed file records
```

- One Vault Item produces exactly one Plan
- A Plan may produce 0 to N Approval Requests (one per HIGH/CRITICAL step)
- Any action on any entity produces Audit Entries
- Watcher State tracks all processed files for deduplication
