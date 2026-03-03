# Error Recovery & Graceful Degradation — Contract

**Feature**: 003-gold-tier
**Module**: `src/core/retry_handler.py`
**Date**: 2026-02-25

---

## `@with_retry` Decorator Contract

```python
from src.core.retry_handler import with_retry, ErrorCategory

@with_retry(max_attempts=3, base_delay=1.0, max_delay=60.0)
def call_odoo_api(...):
    ...
```

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `max_attempts` | int | 3 | Total number of attempts (1 + retries) |
| `base_delay` | float | 1.0 | Initial delay in seconds between retries |
| `max_delay` | float | 60.0 | Cap on exponential back-off delay |

### Back-off Formula

```
delay = min(base_delay * (2 ** attempt), max_delay) + uniform_jitter(0, 0.5)
```

Attempt 1 → delay ≈ 1s
Attempt 2 → delay ≈ 2s
Attempt 3 → delay ≈ 4s (capped at max_delay)

---

## `ErrorCategory` Enum

```python
from enum import Enum

class ErrorCategory(Enum):
    TRANSIENT = "transient"   # network timeout, 429 — retry allowed
    AUTH      = "auth"        # 401/403 — NO retry; alert + pause watcher
    LOGIC     = "logic"       # unexpected response format — quarantine item
    DATA      = "data"        # parse error (bad JSON, bad CSV row) — quarantine item
    SYSTEM    = "system"      # process crash / thread death — watchdog handles
```

### Category → Action Matrix

| Category | Retry? | Action on Exhaustion |
|----------|--------|----------------------|
| TRANSIENT | YES | Re-raise; calling skill logs `result: failure` |
| AUTH | NO | Immediately create vault alert item; pause affected watcher |
| LOGIC | NO | Move item to `vault/Quarantine/`; log `result: failure` |
| DATA | NO | Move item to `vault/Quarantine/`; log `result: failure` |
| SYSTEM | NO | Watchdog restarts thread; alert after 3 failed restarts |

### HTTP Status → ErrorCategory Mapping

```python
def categorise_http_error(status_code: int) -> ErrorCategory:
    if status_code in (401, 403):         return ErrorCategory.AUTH
    if status_code == 429:                return ErrorCategory.TRANSIENT
    if status_code in range(500, 600):    return ErrorCategory.TRANSIENT
    if status_code in range(400, 500):    return ErrorCategory.LOGIC
    return ErrorCategory.SYSTEM
```

---

## Per-Component Degradation Contracts

### Odoo MCP Unreachable

```
Trigger: ConnectionError, requests.Timeout, requests.ConnectionError
Response:
  - FinanceWatcher → CSV fallback; audit result: degraded
  - generate_invoice → return {status: "error", error: "Odoo offline"}
  - accounting_audit → briefing section shows "[Data unavailable — Odoo offline]"
  - One vault alert Inbox item per degraded session (idempotent: dedup by date)
```

### Meta API (Facebook/Instagram) Failure

```
Trigger: requests.HTTPError with 5xx
ErrorCategory: TRANSIENT
Response:
  - @with_retry (3 attempts)
  - On exhaustion: skip post this cycle; audit result: degraded
  - No vault alert (temporary condition)

Trigger: requests.HTTPError with 401/403
ErrorCategory: AUTH
Response:
  - No retry
  - Create vault/Inbox/META_AUTH_ALERT_<ts>.md
  - Pause FacebookWatcher (set status: "stopped")
```

### Twitter API Failure

```
Trigger: tweepy.TweepyException with 5xx
ErrorCategory: TRANSIENT
Response:
  - @with_retry (3 attempts)
  - On exhaustion: skip post this cycle; audit result: degraded

Trigger: tweepy.Unauthorized (401)
ErrorCategory: AUTH
Response:
  - No retry
  - Create vault/Inbox/TWITTER_AUTH_ALERT_<ts>.md
  - Pause TwitterWatcher
```

### Gmail API Down

```
Response:
  - FilesystemWatcher continues monitoring vault/
  - Outbound emails queued in vault/Pending_Approval/ (not sent)
  - No crash; next Gmail poll cycle retries
```

### Claude API Down

```
Response:
  - generate_plan falls back to PLAN_TEMPLATES in plan_task.py
  - post_facebook, post_twitter fall back to template text
  - generate_invoice uses template description placeholder
  - No crash; audit logs {result: degraded}
```

---

## `watchdog.py` — Thread Monitor Contract

```python
class Watchdog:
    """
    Monitors all daemon watcher threads. Runs every 60s.
    Attempts restart on thread death.
    Creates vault alert after 3 consecutive failed restarts.
    """
    CHECK_INTERVAL_S: int = 60
    MAX_RESTART_ATTEMPTS: int = 3

    def check_all_threads(self, watcher_registry: dict[str, BaseWatcher],
                          thread_registry: dict[str, threading.Thread]) -> None:
        """
        For each thread: if not alive → attempt restart.
        Track failure_count per watcher in _watcher_health.
        On failure_count >= MAX_RESTART_ATTEMPTS: create vault alert, stop retrying.
        """

    def _restart_watcher(self, name: str, watcher: BaseWatcher,
                         vault_root: str) -> threading.Thread | None:
        """Returns new thread on success, None on failure."""

    def _create_alert(self, vault_root: str, watcher_name: str) -> None:
        """Creates vault/Inbox/WATCHDOG_ALERT_<watcher>_<ts>.md."""
```

### Audit Log Entries

| Event | action_type | result |
|-------|-------------|--------|
| Thread restarted | `watchdog_restart` | `success` |
| Restart failed | `watchdog_restart` | `failure` |
| Alert created (3 failures) | `watchdog_alert` | `success` |
