# Silver Tier Data Model

**Feature**: 002-silver-tier
**Date**: 2026-02-20
**Phase**: Phase 1 — Design

---

## Entities

### 1. InboxItem (extended from Bronze)

All watchers produce items conforming to this normalized structure:

```python
{
    # Required (all watchers)
    "id": str,              # Unique dedup key — watcher-specific format below
    "source": str,          # "gmail" | "whatsapp" | "filesystem" | "linkedin"
    "type": str,            # Set by triage_inbox: "email" | "whatsapp" | "lead" |
                            #   "social_media_engagement" | "general"
    "priority": str,        # "LOW" | "MEDIUM" | "HIGH" | "CRITICAL"
    "filename": str,        # Vault filename: GMAIL_<id>.md, WA_<id>.md, etc.
    "tags": list[str],      # Empty on creation; enriched by skills
    "fail_count": int,      # Incremented by execute_plan on failure; ≥3 → Quarantine

    # Source-specific fields (Gmail)
    "subject": str,
    "from_address": str,
    "to_address": str,
    "message_id": str,      # Gmail message_id (= id for Gmail items)
    "received_at": str,     # ISO 8601
    "thread_id": str,
    "body": str,            # Plain text

    # Source-specific fields (WhatsApp)
    "from_number": str,
    "body": str,

    # Source-specific fields (LinkedIn)
    "platform": str,        # "linkedin"
    "reactions": int,
    "comments": int,
    "post_preview": str,    # First 200 chars
    "post_url": str,

    # Lead detection fields (added by detect_lead skill)
    "lead_score": int,      # 0-10; set when type is upgraded to "lead"
}
```

**ID formats by source**:
- Gmail: `message_id` (Gmail's native message ID)
- WhatsApp: `WA_{sender_norm}_{body_hash}` (SHA256-based content dedup)
- LinkedIn: SHA256 of `post_url[:12]`
- Filesystem: existing Bronze format

### 2. WatcherState (per watcher)

State file at `vault/state/{watcher_name}_state.json`:

```python
{
    "processed_ids": list[str],  # All item IDs seen; prevents re-processing
    "last_poll": str,            # ISO 8601 timestamp of last successful poll
    "error_count": int,          # Consecutive errors; reset on success
}
```

**Files**:
- `vault/state/gmail_watcher_state.json`
- `vault/state/whatsapp_watcher_state.json`

### 3. WatcherHealth (orchestrator shared dict)

Runtime-only (not persisted); read by `update_dashboard.py`:

```python
{
    "{watcher_name}": {
        "last_poll": str,        # ISO 8601 of last poll completion
        "items_this_cycle": int, # Items returned in last poll
        "status": str,           # "OK" | "ERROR"
    }
}
```

**Watcher names**: `gmail_watcher`, `whatsapp_watcher`, `linkedin_watcher`, `filesystem_watcher`

### 4. QueueEntry

Stored in `vault/state/queue.json` (list of entries):

```python
{
    "action_type": str,      # "send_email" | "post_social"
    "details": dict,         # Full action details dict
    "plan_id": str,          # Plan file that generated this action
    "queued_at": str,        # ISO 8601 when queued
}
```

**Lifecycle**: Created by `action_executor` when rate-limited. Drained by `execute_plan.py` at
start of each scan cycle. Entries older than 24h are purged without retry.

### 5. IdempotencyEntry

Stored in `vault/state/idempotency_keys.json` (dict keyed by idempotency key):

```python
{
    "{agent}:{action}:{sha256[:8]}:{epoch_day}": {
        "result": dict,       # Cached action result
        "stored_at": float,   # Unix timestamp
    }
}
```

**Key format**: `"{agent}:{action}:{sha256_of_details[:8]}:{epoch_day}"`
**TTL**: 24 hours (entries older than `idempotency.ttl_hours` are pruned on each check)

### 6. RateLimitCounter

Stored in `vault/state/rate_limits.json` (dict keyed by compound key):

```python
{
    "{action_type}:{epoch_hour}": int,   # Call count in this hour window
}
```

**Pruning**: Keys older than 2 hours are removed on each read/write cycle.

### 7. LinkedInPostPlan

A specialized Plan.md file in `vault/Plans/LINKEDIN_POST_{timestamp}.md`:

```yaml
---
type: linkedin_post
risk_level: HIGH
requires_approval: true
status: pending
created_at: "2026-02-20T10:00:00Z"
post_text: |
  [Full post text with #AIAssisted]
---
```

Plan steps follow the `linkedin_post` PLAN_TEMPLATE (FR-I01).

### 8. BriefingDocument

Output: `vault/Briefings/BRIEFING_{YYYY-MM-DD}.md`

Required sections:
1. Date range covered
2. Items by channel (gmail / whatsapp / filesystem counts)
3. Leads detected (count, top 3 by score, pending vs responded)
4. Emails sent (real vs simulated)
5. LinkedIn posts published (with engagement delta)
6. Plans summary (in-progress / completed / rejected counts)
7. Approvals summary (resolved / expired / pending)
8. Quarantine count and failure reasons
9. Next-week recommendations

### 9. OptOutList

File: `vault/Opt_Out_List.md`

Format:
```markdown
# Opt-Out List
- alice@example.com
- bob@example.com
```

Parsing: Lines starting with `- ` contain email addresses. Headings and blank lines are skipped.
Case-insensitive comparison.

---

## State Transitions

### Item Lifecycle (extended from Bronze)

```
[watcher produces item]
  → vault/Inbox/ITEM_*.md           (initial state: type=unclassified)
  → vault/Needs_Action/ITEM_*.md    (after triage; detect_lead may upgrade type/priority in-place)
  → vault/Plans/PLAN_*.md           (after generate_plan; Claude Reasoning prepended if API key)
  → vault/Pending_Approval/         (HIGH/CRITICAL step — HITL gate; expires in 48h)
  → vault/Done/                     (approved or rejected; terminal)
  → vault/Quarantine/               (fail_count ≥ 3; human rescue required; terminal from agent POV)
```

**New in Silver**:
- `fail_count` field tracked in frontmatter; incremented by `execute_plan.py` on each failure
- `type: lead` upgrade happens in-place in `vault/Needs_Action/` by `detect_lead`
- `type: linkedin_post` plans originate from `generate_linkedin_post` skill (not from inbox items)

### Queue Lifecycle

```
rate_limit exceeded in action_executor
  → append to vault/state/queue.json
  → [on next scan cycle] execute_plan.py drains queue
    ├── limit reset: re-attempt via action_executor → remove from queue
    ├── still limited: leave in queue, write MEDIUM audit entry
    └── age > 24h: purge without retry (stale action guard)
```

### Idempotency Key Lifecycle

```
generate_key(agent, action, details) → key string
check_and_store(vault_root, key, result)
  ├── key exists AND not expired → return (True, cached_result)   → skip MCP call
  └── key absent or expired      → call MCP → store (key, result) → return (False, None)
```

---

## Validation Rules

### InboxItem
- `id` MUST be non-empty and unique within the vault (enforced by watcher dedup check)
- `source` MUST be one of `{"gmail", "whatsapp", "filesystem", "linkedin"}`
- `priority` MUST be one of `{"LOW", "MEDIUM", "HIGH", "CRITICAL"}`
- `type` of `"lead"` requires `lead_score` to be present and in range 0–10
- `fail_count` MUST be 0 on creation (set by watcher); incremented only by `execute_plan.py`

### QueueEntry
- `queued_at` MUST be ISO 8601 format
- `action_type` MUST be one of `{"send_email", "post_social"}`
- `plan_id` MUST reference an existing plan file

### IdempotencyEntry
- Key MUST match pattern `{str}:{str}:{8hex}:{int}`
- `stored_at` MUST be Unix float timestamp
- Entries with `stored_at` older than `ttl_hours * 3600` are considered expired

### OptOutList
- Email addresses are stored and compared case-insensitively
- Invalid lines (not starting with `- `) are silently skipped

---

## Mock Schemas (Dry-Run)

### Gmail Mock (`vault/Watch/gmail_mock/sample_email.json`)
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
Detection: presence of `"payload"` key → real Gmail API response; absence → flat mock.

### WhatsApp Mock (`vault/Watch/whatsapp_mock/sample_message.json`)
```json
{
  "MessageSid": "SM12345",
  "From": "+15551234567",
  "Body": "Hello, I'd like to know your pricing",
  "To": "+15559876543"
}
```

### LinkedIn Mock (`vault/Watch/linkedin_mock/sample_post.json`)
```json
{
  "post_url": "https://www.linkedin.com/feed/update/urn:li:activity:example",
  "reactions": 42,
  "comments": 7,
  "post_preview": "First 200 characters of the post text..."
}
```
