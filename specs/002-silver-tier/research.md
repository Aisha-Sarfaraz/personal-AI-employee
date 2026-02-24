# Silver Tier Research

**Feature**: 002-silver-tier
**Date**: 2026-02-20
**Phase**: Phase 0 — Research & Decision Resolution
**Status**: Complete

All implementation unknowns from the Technical Context are resolved below. No NEEDS CLARIFICATION
items remain.

---

## Decision 1: MCP Python SDK usage pattern for email-mcp

**Decision**: Use `mcp` Python client library to spawn and connect to the `npx @anthropic/email-mcp`
subprocess, then invoke its `send_email` tool via JSON-RPC over stdio.

**Rationale**: The `email-mcp` server is a Node.js process launched via `npx`. The MCP Python SDK
(`mcp>=1.0.0`) provides a `StdioServerParameters` + `stdio_client` context manager to spawn and
communicate with stdio-based MCP servers without manual subprocess management or HTTP.

**Pattern**:
```python
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def _send_via_mcp(to, subject, body):
    server_params = StdioServerParameters(
        command="npx",
        args=["@anthropic/email-mcp"],
        env={"GMAIL_CLIENT_ID": ..., "GMAIL_CLIENT_SECRET": ...,
             "GMAIL_REFRESH_TOKEN": ...}
    )
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(
                "send_email",
                {"to": to, "subject": subject, "body": body}
            )
            return result
```

**Sync wrapper**: `action_executor.py` is synchronous. Wrap with `asyncio.run()` or use
`anyio.run()` for test compatibility.

**Alternatives considered**:
- Direct `subprocess` + JSON-RPC manually — rejected (error-prone, no reconnect logic)
- HTTP transport — rejected (email-mcp uses stdio, not HTTP)

---

## Decision 2: Gmail OAuth2 / google-auth library patterns

**Decision**: Use `google-auth` + `google-api-python-client`. Token stored at
`vault/.gmail_token.json`. Automatic refresh via `google.auth.transport.requests.Request`.

**Rationale**: Standard Google client library. Token file written by a one-time `gmail_auth.py`
OAuth2 flow using `google_auth_oauthlib.flow.InstalledAppFlow`. `GmailWatcher` loads the token
with `google.oauth2.credentials.Credentials.from_authorized_user_file()` and passes a
`google.auth.transport.requests.Request` object to `credentials.refresh()` when expired.

**Pattern for GmailWatcher.check_for_updates()**:
```python
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

TOKEN_PATH = os.path.join(vault_root, ".gmail_token.json")
SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]

creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
if creds.expired and creds.refresh_token:
    creds.refresh(Request())
    # Write refreshed token back
    with open(TOKEN_PATH, "w") as f:
        f.write(creds.to_json())

service = build("gmail", "v1", credentials=creds)
result = service.users().messages().list(userId="me", q=query, maxResults=max_results).execute()
```

**Alternatives considered**:
- `GMAIL_REFRESH_TOKEN` env var — rejected (session 2 clarification; token file is simpler)
- Application Default Credentials — rejected (requires gcloud CLI, not portable)

---

## Decision 3: Playwright persistent context for WhatsApp Web and LinkedIn

**Decision**: Use `playwright.sync_api.sync_playwright` with `browser.launch_persistent_context()`
pointing to a user data directory in the vault. Session survives process restarts.

**Rationale**: `launch_persistent_context(user_data_dir=...)` stores all cookies, localStorage,
and session data to disk. On subsequent runs, the browser loads the session automatically without
re-authentication. This is the same pattern already proven in `whatsapp_watcher.py`.

**Pattern**:
```python
from playwright.sync_api import sync_playwright

SESSION_DIR = os.path.join(vault_root, "state", "linkedin_session")

with sync_playwright() as p:
    context = p.chromium.launch_persistent_context(
        user_data_dir=SESSION_DIR,
        headless=True,  # False for setup_session()
    )
    page = context.new_page()
    page.goto("https://www.linkedin.com/in/<username>/detail/recent-activity/")
    # ... extract engagement items
    context.close()
```

**Session expiry handling**: If the page URL contains `/login`, session has expired. Log LOW audit
entry with re-login instructions and return `[]`. Do not crash.

**Alternatives considered**:
- `browser.new_context()` with saved storage state — rejected (JSON file approach is less robust
  than user data directory for multi-session persistence)
- Selenium — rejected (Playwright already used for WhatsApp watcher; consistency wins)

---

## Decision 4: Threading model for daemon watcher threads with shared health dict

**Decision**: Each watcher runs in `threading.Thread(daemon=True, target=watcher_loop)` where
`watcher_loop` sleeps for `poll_interval` seconds between calls. A shared `threading.Lock`-
protected dict in the orchestrator stores per-watcher health data.

**Rationale**: This matches the existing Bronze FilesystemWatcher pattern. Daemon threads exit
automatically when the main process exits (no cleanup needed). Each watcher has its own interval
so LinkedIn (3600s) does not block Gmail (120s).

**Health dict pattern**:
```python
# orchestrator.py
import threading
_watcher_health = {}  # {watcher_name: {last_poll, items_this_cycle, status}}
_health_lock = threading.Lock()

def _watcher_loop(watcher, name):
    while True:
        try:
            items = watcher.check_for_updates()
            with _health_lock:
                _watcher_health[name] = {
                    "last_poll": datetime.utcnow().isoformat(),
                    "items_this_cycle": len(items),
                    "status": "OK"
                }
        except Exception as e:
            with _health_lock:
                _watcher_health[name] = {
                    "last_poll": datetime.utcnow().isoformat(),
                    "items_this_cycle": 0,
                    "status": "ERROR"
                }
        time.sleep(watcher.poll_interval)
```

**Alternatives considered**:
- asyncio event loop — rejected (mixing asyncio with Playwright sync_api is complex; threading is
  simpler and already proven in Bronze)
- Sequential polling (no threads) — rejected (per-watcher intervals become impossible)

---

## Decision 5: Rate limiter and idempotency key storage patterns

**Decision**: Both modules store JSON state in `vault/state/`. Rate limiter uses hourly windows
(epoch-hour as key). Idempotency store uses compound keys with TTL.

**Rate limiter pattern** (`src/core/rate_limiter.py`):
```python
RATE_FILE = os.path.join(vault_root, "state", "rate_limits.json")
epoch_hour = int(time.time() // 3600)
key = f"{action_type}:{epoch_hour}"
data = load_json(RATE_FILE)
count = data.get(key, 0)
if count >= limit_per_hour:
    return False  # rate-limited
data[key] = count + 1
# Prune old keys (older than 2 hours)
save_json(RATE_FILE, data)
return True  # allowed
```

**Idempotency pattern** (`src/core/idempotency.py`):
```python
IDEMPOTENCY_FILE = os.path.join(vault_root, "state", "idempotency_keys.json")

def generate_key(agent, action, details):
    details_hash = hashlib.sha256(json.dumps(details, sort_keys=True).encode()).hexdigest()[:8]
    epoch_day = int(time.time() // 86400)
    return f"{agent}:{action}:{details_hash}:{epoch_day}"

def check_and_store(vault_root, key, result=None, ttl_hours=24):
    data = load_json(IDEMPOTENCY_FILE)
    # Expire old entries
    now = time.time()
    data = {k: v for k, v in data.items()
            if now - v.get("stored_at", 0) < ttl_hours * 3600}
    if key in data:
        return True, data[key].get("result")  # key existed
    data[key] = {"result": result, "stored_at": now}
    save_json(IDEMPOTENCY_FILE, data)
    return False, None  # key was new
```

**Alternatives considered**:
- SQLite for rate limiting — rejected (JSON file is simpler; hourly precision sufficient)
- Redis — rejected (external dependency; no Silver requirement for distributed rate limiting)

---

## Decision 6: opt_out.py parsing approach

**Decision**: Parse `vault/Opt_Out_List.md` line by line. Lines starting with `- ` have the email
extracted from the rest of the line (stripped). All other lines (headings, blanks, comments) are
skipped. Comparison is case-insensitive.

**Pattern**:
```python
def is_opted_out(vault_root, email_address):
    opt_out_file = os.path.join(vault_root, "Opt_Out_List.md")
    if not os.path.exists(opt_out_file):
        return False
    with open(opt_out_file) as f:
        for line in f:
            line = line.strip()
            if line.startswith("- "):
                stored = line[2:].strip().lower()
                if stored == email_address.lower():
                    return True
    return False
```

**Alternatives considered**:
- YAML/JSON opt-out file — rejected (spec specifies Markdown list; human-editable in Obsidian)
- Database — rejected (over-engineering for a personal list of < 1000 entries)

---

## Decision 7: generate_linkedin_post self-guard audit log scan

**Decision**: Scan `vault/Logs/` directory for audit log files in date range (last `frequency_days`
days). Check each file's content for any entry containing `"action": "linkedin_post"`. If found,
return `{skipped: 1}` immediately.

**Pattern**:
```python
from datetime import datetime, timedelta
import os, json, re

def _posted_recently(vault_root, frequency_days):
    logs_dir = os.path.join(vault_root, "Logs")
    cutoff = datetime.utcnow() - timedelta(days=frequency_days)
    for fname in os.listdir(logs_dir):
        if not fname.endswith(".md"):
            continue
        fpath = os.path.join(logs_dir, fname)
        # Parse date from filename (e.g. AUDIT_2026-02-20_...)
        date_match = re.search(r"(\d{4}-\d{2}-\d{2})", fname)
        if date_match:
            file_date = datetime.strptime(date_match.group(1), "%Y-%m-%d")
            if file_date < cutoff:
                continue
        with open(fpath) as f:
            if "action: linkedin_post" in f.read():
                return True
    return False
```

**Alternatives considered**:
- Separate LinkedIn post tracker file — rejected (audit log is single source of truth per
  constitution S10; no separate state file needed)
- Database query — rejected (over-engineering)

---

## Decision 8: weekly_briefing audit log aggregation

**Decision**: Read all audit log files from `vault/Logs/` dated in the past week (Monday–Sunday).
Parse each file for structured data using regex on Markdown content. Aggregate counts by channel,
action type, and outcome. Generate briefing with Claude (if API key) or template.

**Pattern**: Audit logs are Markdown files. Each entry has a line pattern like:
```
- **action**: send_email
- **source**: gmail
- **status**: success
- **simulated**: false
```
Parse with regex `r"\*\*(\w+)\*\*: (.+)"` to extract key-value pairs per entry.

**Alternatives considered**:
- Structured JSON audit logs — rejected (Gold tier requirement per spec Section 10 Out of Scope)
- Parse only filenames — rejected (insufficient detail for briefing)

---

## Decision 9: install_schedule.py platform detection and idempotency

**Decision**: Use `sys.platform` to detect Windows vs POSIX. On Windows, use `subprocess.run`
with `schtasks.exe`. On POSIX, use `crontab -l`, modify, and `crontab -` pipe.

**Idempotency**: Before registering, check if task exists (`schtasks /query /tn FTE-*`) and
delete+recreate (update). For crontab: read existing crontab, remove all `# FTE` tagged lines,
append new entries.

**Pattern (Windows)**:
```python
import subprocess, sys

def _register_windows(script_path, python_exe):
    # Remove if exists (idempotent)
    subprocess.run(["schtasks", "/delete", "/tn", "FTE-Orchestrator", "/f"],
                   capture_output=True)
    # Create
    subprocess.run([
        "schtasks", "/create", "/tn", "FTE-Orchestrator",
        "/tr", f"{python_exe} {script_path}",
        "/sc", "ONSTART", "/ru", "SYSTEM"
    ], check=True)
```

**Alternatives considered**:
- Windows Service — rejected (complexity; Task Scheduler is simpler and sufficient)
- APScheduler in-process — rejected (spec requires OS-level scheduling that survives reboots)

---

## Summary of Resolved Unknowns

| Unknown | Resolution |
|---------|-----------|
| MCP Python SDK usage | `stdio_client` + `ClientSession` with asyncio; sync wrapper via `asyncio.run()` |
| Gmail OAuth2 pattern | `google.oauth2.credentials.Credentials.from_authorized_user_file()` + auto-refresh |
| Playwright persistent session | `launch_persistent_context(user_data_dir=...)` — same as WhatsApp watcher |
| Daemon thread + health dict | `threading.Thread(daemon=True)` + `threading.Lock`-protected shared dict |
| Rate limiter storage | JSON file in `vault/state/rate_limits.json`, epoch-hour window keys |
| Idempotency storage | JSON file in `vault/state/idempotency_keys.json`, compound key + TTL |
| Opt-out parsing | Line-by-line Markdown list; skip non `- ` lines; case-insensitive |
| LinkedIn post cadence guard | Scan `vault/Logs/` for `action: linkedin_post` in last N days |
| Weekly briefing aggregation | Regex parse Markdown audit logs; Gold tier JSON deferred |
| Scheduling idempotency | Delete+recreate (Windows); strip+append (crontab) |
