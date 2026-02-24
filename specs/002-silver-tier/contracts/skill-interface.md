# Silver Tier Skill Interface Contracts

**Feature**: 002-silver-tier
**Date**: 2026-02-20
**Extends**: `specs/001-bronze-tier/contracts/skill-interface.md`

All Silver skills conform to the Bronze `run(vault_root: str) -> dict` contract. Return dict
extensions are additive — no existing keys removed.

---

## detect_lead

```python
def run(vault_root: str) -> dict[str, Any]:
    """
    Scan vault/Needs_Action/ for items with lead signals.
    Upgrades matching items to type:lead, priority:CRITICAL, lead_score:<int>.

    Returns:
        processed (int): Items scanned
        leads_detected (int): Items upgraded to type:lead
        errors (list[str]): Error messages (non-fatal)
        skipped (int): Items skipped (already type:lead or no keywords matched)
    """
```

**Reads**: `vault/Needs_Action/` (frontmatter), `config/settings.yaml` (keywords list)
**Writes**: `vault/Needs_Action/` (frontmatter in-place), `vault/Logs/` (HIGH audit entry per lead)
**Side effects**: Updates `type`, `priority`, `lead_score` in item frontmatter
**Error behaviour**: Non-fatal; errors appended to `errors` list; processing continues

---

## generate_plan

```python
def run(vault_root: str) -> dict[str, Any]:
    """
    Generate Plan.md for items in vault/Needs_Action/ that have no plan yet.

    Flow:
      1. Call plan_task.run(vault_root) — creates PLAN_*.md using Bronze templates
      2. If ANTHROPIC_API_KEY set and dev_mode=false:
         read PLAN_*.md → call Claude API → prepend ## Reasoning section
      3. If API key absent or dev_mode=true: return plan as-is (no error)

    Returns:
        processed (int): Plans generated
        claude_enriched (int): Plans enriched with Claude reasoning
        template_fallback (int): Plans generated from template only (no Claude)
        errors (list[str]): Non-fatal errors
        skipped (int): Items with existing plans (skipped)
    """
```

**Reads**: `vault/Needs_Action/`, `vault/Business_Goals.md`, `vault/Plans/` (written PLAN_*.md)
**Writes**: `vault/Plans/PLAN_*.md` (via plan_task + optional Reasoning prepend), `vault/Logs/`
**Env deps**: `ANTHROPIC_API_KEY`, `ANTHROPIC_PLAN_MODEL` (default: `claude-haiku-4-5`)
**Bronze invariant**: `plan_task.py` is NOT modified; called as library

---

## generate_linkedin_post

```python
def run(vault_root: str) -> dict[str, Any]:
    """
    Draft a LinkedIn sales post using Claude. Subject to self-guards.

    Self-guards (checked on every call before doing any work):
      1. skills.generate_linkedin_post.enabled == true in settings.yaml
      2. No audit entry with action:linkedin_post in last frequency_days days

    Returns:
        processed (int): Post drafts attempted
        post_files_created (int): Draft files written to vault/Plans/
        skipped_rate_limit (int): Skipped due to cadence guard
        errors (list[str]): Non-fatal errors
        skipped (int): Skipped due to enabled=false or cadence guard
    """
```

**Reads**: `vault/Business_Goals.md`, `vault/Logs/` (7-day scan), `vault/Templates/linkedin_post_prompt.md`
**Writes**: `vault/Plans/LINKEDIN_POST_{timestamp}.md`, `vault/Logs/`
**Env deps**: `ANTHROPIC_API_KEY`
**Constraints**: Max 3,000 chars; must include `#AIAssisted`; risk_level HIGH; requires_approval true

---

## weekly_briefing

```python
def run(vault_root: str) -> dict[str, Any]:
    """
    Generate weekly CEO briefing. Self-guards: Monday only + briefing not yet written.

    Self-guards (checked before any log reading):
      1. datetime.now().weekday() == 0  (Monday)
      2. vault/Briefings/BRIEFING_{this-monday}.md does not exist

    Returns:
        processed (int): 1 if briefing written, 0 if skipped
        briefing_file (str | None): Path to written briefing file, or None if skipped
        week_start (str | None): ISO date of Monday (week start), or None if skipped
        errors (list[str]): Non-fatal errors
        skipped (int): 1 if self-guard triggered, 0 otherwise
    """
```

**Reads**: `vault/Logs/`, `vault/Needs_Action/`, `vault/Done/`, `vault/Quarantine/`
**Writes**: `vault/Briefings/BRIEFING_{YYYY-MM-DD}.md`, `vault/Logs/`
**Risk**: LOW (no external actions; read-only aggregation)
**Env deps**: `ANTHROPIC_API_KEY` (optional; falls back to template text)

---

## install_schedule

```python
def run(vault_root: str) -> dict[str, Any]:
    """
    Register OS-level scheduled tasks for orchestrator and weekly briefing. Idempotent.

    Platforms:
      Windows: schtasks.exe — FTE-Orchestrator (ONSTART) + FTE-WeeklyBriefing (Mon 08:00)
      POSIX:   crontab — @reboot + "0 8 * * 1" entries tagged # FTE

    Returns:
        processed (int): Tasks processed
        platform (str): "windows" | "posix"
        tasks_created (int): New tasks registered
        tasks_updated (int): Existing tasks updated (idempotent)
        errors (list[str]): Non-fatal errors
        skipped (int): Always 0 (this skill is never skipped)
    """
```

---

## Core Module Contracts

### src/core/idempotency.py

```python
def generate_key(agent: str, action: str, details: dict) -> str:
    """
    Generate compound idempotency key.
    Format: "{agent}:{action}:{sha256_of_details[:8]}:{epoch_day}"
    details is JSON-serialized with sorted keys before hashing.
    """

def check_and_store(
    vault_root: str,
    key: str,
    result: dict | None = None,
    ttl_hours: int = 24,
) -> tuple[bool, dict | None]:
    """
    Check if key exists and is not expired. Store result if key is new.

    Returns:
        (True, cached_result)  if key existed and was not expired
        (False, None)          if key was absent or expired (result has been stored)

    Side effects:
        - Prunes expired entries (older than ttl_hours) on every call
        - Writes vault/state/idempotency_keys.json
    """
```

### src/core/rate_limiter.py

```python
def check_and_increment(
    vault_root: str,
    action_type: str,
    limit_per_hour: int,
) -> bool:
    """
    Check if action_type is within hourly limit. Increment counter if allowed.

    Returns:
        True   if call is allowed (counter incremented)
        False  if rate limit exceeded (counter NOT incremented)

    Key format: "{action_type}:{epoch_hour}" where epoch_hour = int(time.time() // 3600)
    Side effects: Writes vault/state/rate_limits.json; prunes keys older than 2 hours
    """
```

### src/core/opt_out.py

```python
def is_opted_out(vault_root: str, email_address: str) -> bool:
    """
    Check if email_address is in vault/Opt_Out_List.md.
    Case-insensitive. Lines starting with "- " are email entries.
    Headings, blanks, comments are skipped.
    Returns False if Opt_Out_List.md does not exist.
    """
```

---

## action_executor.py Extended Contract

The existing Bronze `execute_action(action_type, details, plan_id, vault_root)` interface
is extended. No existing callers are broken.

### send_email (extended)

**Real mode** (`dev_mode=false`, credentials present):
1. Check `opt_out.is_opted_out()` → if opted out: log `skipped:opted_out`; return skip result
2. Append AI disclosure footer: `"This message was drafted with AI assistance."`
3. Check `rate_limiter.check_and_increment("send_email", 20)` → if limited: queue + return
4. `idempotency.check_and_store()` → if key exists: return cached result
5. Call `email-mcp` via MCP Python SDK with exponential backoff (1s, 2s, 4s)
6. On success: store idempotency result; return `{success:true, simulated:false, message_id}`
7. On 3 failures: increment `fail_count`; return `{success:false, simulated:false}`

**Simulation mode** (`dev_mode=true`): Return `{success:true, simulated:true}` (Bronze behaviour)

### post_social (new)

**Real mode** (`dev_mode=false`, LinkedIn session present):
1. Validate `platform == "linkedin"` in details
2. Check `rate_limiter.check_and_increment("post_social", 10)` → if limited: queue + return
3. `idempotency.check_and_store()` → if key exists: return cached result
4. Launch Playwright with `vault/state/linkedin_session/` persistent context
5. Navigate to LinkedIn post composer; enter text; submit
6. Store idempotency result; log `action:linkedin_post`
7. Return `{success:true, simulated:false, action:"published_linkedin_post"}`

**Simulation mode**: Return `{success:true, simulated:true}` (no Playwright call)
