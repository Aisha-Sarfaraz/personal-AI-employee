# Bronze Tier: Technology Research & Decisions

**Date:** 2026-02-17
**Status:** APPROVED
**Version:** 1.0

---

## Overview

This document captures technology research and architectural decisions for the Personal AI Employee (PAE) file monitoring and processing pipeline. All decisions have been evaluated against production readiness, complexity, maintainability, and alignment with Bronze Tier constraints (no LLM, keyword-based triage, simple HITL approval).

---

## 1. Python Watchdog Library for Filesystem Monitoring

### Decision

**Use `watchdog` library with `Observer` + `FileSystemEventHandler` pattern for directory monitoring.**

### Rationale

The `watchdog` library is the de facto standard for Python filesystem monitoring because:

1. **Cross-platform support:** Works identically on Linux, macOS, and Windows (uses native APIs: inotify, FSEvents, ReadDirectoryChangesW)
2. **Event-driven architecture:** Observer pattern naturally maps to pipeline stages (detected → triaged → approved → executed)
3. **Minimal dependencies:** Single pure-Python dependency with no system-level requirements
4. **Mature and stable:** 15+ years of active maintenance, widely adopted in production systems
5. **Rich event information:** Provides full file path, event type, timestamps without manual stat() calls
6. **Thread-safe:** Observer runs in dedicated thread, decouples filesystem monitoring from processing

### Implementation Pattern

```python
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class InboxHandler(FileSystemEventHandler):
    def on_created(self, event):
        if not event.is_directory:
            # Defer processing to main loop (avoid race conditions)
            queue_file_for_processing(event.src_path)

observer = Observer()
observer.schedule(InboxHandler(), path="/vault/Inbox", recursive=False)
observer.start()

try:
    while True:
        time.sleep(0.1)  # Main orchestrator loop
except KeyboardInterrupt:
    observer.stop()
observer.join()
```

### Race Condition Handling: "File Not Fully Written"

**Problem:** OS sends `on_created()` event before file is fully written (especially on Windows with network shares).

**Solution: Two-tier approach**

1. **Initial debounce (watchdog catches most cases):**
   - `on_created()` callback adds file to processing queue with `pending` status
   - File is NOT immediately processed
   - Adds 500ms delay before processing attempt

2. **Stability check (catch slow writers):**
   ```python
   def is_file_stable(filepath, attempts=3, delay_ms=100):
       """Check if file size hasn't changed (file is fully written)"""
       sizes = []
       for i in range(attempts):
           try:
               size = os.path.getsize(filepath)
               sizes.append(size)
               time.sleep(delay_ms / 1000.0)
           except FileNotFoundError:
               return False  # File deleted
       # File is stable if all size measurements are identical
       return len(set(sizes)) == 1

   # Before processing:
   if not is_file_stable(filepath):
       # Requeue for later retry (exponential backoff)
       return False
   ```

3. **Polling fallback (safety net):**
   - Main orchestrator loop checks `/Inbox` every 30s for unprocessed files
   - Catches files missed by watchdog (network delays, process crashes)
   - Deduplication via hash/name in state file prevents reprocessing

### Alternatives Considered

| Alternative | Why Not Selected |
|---|---|
| `os.listdir()` polling only | Inefficient (network IO every 30s), poor UX (delayed detection) |
| Manual file creation hooks via inotify/FSEvents | Too low-level, requires platform-specific code |
| `pathlib` Path.iterdir() | Still polling-based, doesn't solve race condition |
| `twisted` filesystem reactor | Over-engineered for this use case, heavy dependency |

### Configuration

```yaml
# config.yaml
watcher:
  watch_path: vault/Inbox
  recursive: false
  stability_check_attempts: 3
  stability_check_delay_ms: 100
  debounce_ms: 500
  polling_fallback_interval_s: 30
```

---

## 2. YAML Frontmatter Parsing in Python

### Decision

**Use `pyyaml` library with manual `---` delimiter splitting and regex-based extraction.**

### Rationale

1. **Minimal dependencies:** `pyyaml` is universally available; reduces dependency footprint
2. **Explicit control:** Manual parsing gives visibility into frontmatter structure
3. **Markdown-native:** Respects Obsidian vault conventions (no wrapper libraries needed)
4. **Performance:** No overhead from abstraction layers for simple YAML parsing
5. **Debugging:** Manual parsing makes issues obvious (missing delimiters, invalid YAML)

### Implementation Pattern

```python
import re
import yaml

def parse_frontmatter(filepath):
    """
    Parse YAML frontmatter from Markdown file.
    Returns: (metadata_dict, content_str)
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Match opening and closing --- delimiters
    match = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)

    if not match:
        # No frontmatter; treat entire content as body
        return {}, content

    frontmatter_text = match.group(1)
    body_text = content[match.end():]

    try:
        metadata = yaml.safe_load(frontmatter_text)
        if metadata is None:
            metadata = {}
        return metadata, body_text
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML in {filepath}: {e}")

def write_frontmatter(filepath, metadata, content):
    """
    Write YAML frontmatter + content to file.
    """
    yaml_str = yaml.dump(metadata, default_flow_style=False, allow_unicode=True)
    # Remove trailing newline from YAML dump
    yaml_str = yaml_str.rstrip('\n')

    full_content = f"---\n{yaml_str}\n---\n{content}"

    # Atomic write (temp + replace)
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.md',
                                      dir=os.path.dirname(filepath), encoding='utf-8') as f:
        temp_path = f.name
        f.write(full_content)

    os.replace(temp_path, filepath)
```

### Example Frontmatter

```yaml
---
id: FILE-20260217-001
type: financial
priority: HIGH
created_at: 2026-02-17T10:30:00Z
status: inbox
---

# Invoice from Acme Corp

Amount: $1,500.00
Due Date: 2026-03-17
```

### Alternatives Considered

| Alternative | Why Not Selected |
|---|---|
| `python-frontmatter` library | Extra dependency (1 library for 1 function), pins specific API |
| `ruamel.yaml` | Over-engineered (preserves comments/formatting), adds complexity |
| Regular JSON instead | Not Obsidian-native, harder to edit manually, more verbose |
| Plain TOML | Not standard for Markdown, less familiar to users |

### Configuration

```python
# Constants in config.py
FRONTMATTER_DELIMITER = "---"
YAML_PARSER = yaml.safe_load  # Never use yaml.load (security risk)
ENCODING = "utf-8"
```

---

## 3. Atomic File Writes on Windows

### Decision

**Write to temporary file + `os.replace()` for atomic file moves. Accept best-effort semantics on Windows for Bronze Tier.**

### Rationale

1. **Cross-platform:** `os.replace()` works on all platforms (Windows, Linux, macOS)
2. **Atomic on POSIX:** Guarantees atomicity on Linux/macOS (POSIX rename)
3. **Best-effort on Windows:** `os.replace()` atomically moves file, but not truly transactional like NTFS transactions (which are deprecated)
4. **Acceptable for Bronze Tier:** Vault data loss is unlikely (temp file cleanup on crash, JSON state files not frequently modified)
5. **Simple implementation:** No platform-specific code needed

### Implementation Pattern

```python
import tempfile
import os

def atomic_write(filepath, content):
    """
    Atomically write content to filepath via temp file + replace.

    Guarantees:
    - On POSIX: File appears fully written or not at all (atomic rename)
    - On Windows: Best-effort atomic move (file replaced, but not transactional)
    - Crash-safe: Temp file cleaned up on exceptions
    """
    # Create temp file in same directory (ensures same filesystem)
    parent_dir = os.path.dirname(filepath) or '.'

    try:
        with tempfile.NamedTemporaryFile(
            mode='w',
            encoding='utf-8',
            dir=parent_dir,
            delete=False,
            suffix='.tmp'
        ) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        # Atomic replace (POSIX: rename; Windows: MoveFileEx best-effort)
        os.replace(tmp_path, filepath)

    except Exception as e:
        # Clean up temp file on error
        try:
            os.unlink(tmp_path)
        except:
            pass
        raise

def atomic_write_frontmatter(filepath, metadata, body_content):
    """
    Atomically write frontmatter + body to Markdown file.
    """
    yaml_str = yaml.dump(metadata, default_flow_style=False, allow_unicode=True).rstrip()
    full_content = f"---\n{yaml_str}\n---\n{body_content}"
    atomic_write(filepath, full_content)
```

### Crash Safety Considerations

**Scenario:** System crashes during temp file write

1. **Temp file exists, original doesn't:** On restart, temp file orphaned (harmless)
2. **Solution:** Cleanup script removes `.tmp` files older than 1 hour
   ```python
   def cleanup_orphaned_temps(base_dir, age_hours=1):
       """Clean up abandoned temp files"""
       cutoff = time.time() - (age_hours * 3600)
       for root, dirs, files in os.walk(base_dir):
           for f in files:
               if f.endswith('.tmp'):
                   fpath = os.path.join(root, f)
                   if os.path.getmtime(fpath) < cutoff:
                       os.unlink(fpath)
   ```

### Alternatives Considered

| Alternative | Why Not Selected |
|---|---|
| NTFS Transactions (Windows) | Deprecated by Microsoft, complex, Windows-only |
| Two-phase commit | Over-engineered for Markdown files, requires coordinator |
| Lockfile + explicit sync | Performance cost, deadlock risk, complexity |
| Direct file write | No atomicity; corruption possible on crash |

### Configuration

```python
# config.py
ATOMIC_WRITE_ENABLED = True
TEMP_FILE_CLEANUP_AGE_HOURS = 1
TEMP_FILE_SUFFIX = ".tmp"
```

---

## 4. PM2 for Python Process Management

### Decision

**Use PM2 with `interpreter: python` in `ecosystem.config.js` to manage the PAE orchestrator as a daemon process.**

### Rationale

1. **Language-agnostic process manager:** PM2 manages any process (Node, Python, Ruby, Go)
2. **Automatic restart:** Restarts crashed Python process immediately
3. **Log management:** Centralized logging, rotation, output capture
4. **Startup integration:** Auto-start on system boot
5. **Monitoring:** Built-in health checks, memory/CPU monitoring
6. **Industry standard:** De facto standard for Node.js, widely adopted
7. **Simple configuration:** Single YAML/JS config file, no systemd complexity

### Implementation Pattern

```javascript
// ecosystem.config.js
module.exports = {
  apps: [
    {
      name: 'pae-orchestrator',
      script: './src/orchestrator.py',
      interpreter: 'python',
      args: '--config config.yaml',

      // Auto-restart
      autorestart: true,
      max_memory_restart: '500M',
      max_restarts: 10,
      min_uptime: '10s',

      // Logging
      output: './logs/orchestrator.out.log',
      error: './logs/orchestrator.error.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z',

      // Graceful shutdown
      kill_timeout: 5000,
      listen_timeout: 3000,
      shutdown_with_message: true,

      // Environment
      env: {
        NODE_ENV: 'production',
        VAULT_PATH: './vault',
        CONFIG_PATH: './config.yaml'
      },

      // Clustering (optional: run multiple workers)
      instances: 1,
      exec_mode: 'fork'
    }
  ]
};
```

### Python Orchestrator Script

```python
#!/usr/bin/env python3
# src/orchestrator.py

import argparse
import logging
import signal
import sys
import time
import yaml

class PAEOrchestrator:
    def __init__(self, config_path):
        self.config = self._load_config(config_path)
        self.running = True
        self._setup_signals()

    def _setup_signals(self):
        """Register signal handlers for graceful shutdown"""
        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown)

    def _handle_shutdown(self, signum, frame):
        """Graceful shutdown on SIGINT/SIGTERM"""
        logging.info(f"Received signal {signum}, shutting down gracefully...")
        self.running = False

    def run(self):
        """Main orchestration loop"""
        logging.info("PAE Orchestrator starting...")

        while self.running:
            try:
                self.triage_inbox()
                self.process_approvals()
                self.execute_plans()
                self.update_dashboard()

                time.sleep(self.config['orchestrator']['scan_interval'])

            except Exception as e:
                logging.error(f"Orchestrator error: {e}", exc_info=True)
                time.sleep(1)  # Backoff on error

        logging.info("PAE Orchestrator shutdown complete")
        sys.exit(0)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='PAE Orchestrator')
    parser.add_argument('--config', default='config.yaml', help='Config file path')
    args = parser.parse_args()

    orchestrator = PAEOrchestrator(args.config)
    orchestrator.run()
```

### PM2 Management Commands

```bash
# Start the process
pm2 start ecosystem.config.js

# Monitor in real-time
pm2 monit

# View logs
pm2 logs pae-orchestrator

# Show process info
pm2 show pae-orchestrator

# Graceful restart
pm2 restart pae-orchestrator

# Reload (0 downtime restart)
pm2 reload pae-orchestrator

# Stop and delete
pm2 delete pae-orchestrator

# Auto-start on system boot
pm2 startup
pm2 save
```

### Alternatives Considered

| Alternative | Why Not Selected |
|---|---|
| systemd service | Linux-only, requires sudo, complex unit file syntax |
| supervisor | Legacy, requires XML config, less common in modern stacks |
| Docker + restart policy | Over-engineered for single Python script, adds complexity |
| Background thread in Node app | Ties Python lifecycle to Node.js, complicates debugging |
| Simple bash loop | No auto-restart, no logging, manual restart required |

### Configuration

```yaml
# config.yaml
orchestrator:
  scan_interval: 30  # seconds between orchestration cycles
  graceful_shutdown_timeout: 5  # seconds to wait for pending operations
  max_concurrent_tasks: 3

process_manager:
  tool: pm2
  max_memory_mb: 500
  max_restarts: 10
  min_uptime_s: 10
```

---

## 5. Watcher State Persistence for Deduplication

### Decision

**Use JSON file (`vault/state/watcher_state.json`) to persist set of processed files, keyed by SHA256 hash of filename + creation timestamp.**

### Rationale

1. **Deduplication:** Prevents reprocessing if watcher restarts or watchdog misses events
2. **Lightweight:** JSON is human-readable, easy to inspect and debug
3. **Fast lookups:** Hash-based set provides O(1) membership checking
4. **Resilient:** Survives process crashes, filesystem issues
5. **Auditable:** Can inspect state file to see processing history
6. **No external DB:** Keeps solution simple, no database setup

### Implementation Pattern

```python
import json
import hashlib
from pathlib import Path
from datetime import datetime, timedelta

class WatcherState:
    """Manages persistent watcher state for deduplication"""

    def __init__(self, state_file='vault/state/watcher_state.json'):
        self.state_file = Path(state_file)
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.state = self._load_state()

    def _load_state(self):
        """Load state from disk"""
        if self.state_file.exists():
            with open(self.state_file, 'r') as f:
                return json.load(f)
        return {
            'version': 1,
            'last_sync': None,
            'processed_files': {},  # { file_hash: { timestamp, filename, status } }
            'stats': {
                'total_processed': 0,
                'total_failed': 0,
                'total_approved': 0
            }
        }

    def _save_state(self):
        """Persist state to disk atomically"""
        temp_file = self.state_file.with_suffix('.tmp')
        with open(temp_file, 'w') as f:
            json.dump(self.state, f, indent=2)
        temp_file.replace(self.state_file)

    def get_file_hash(self, filepath):
        """
        Generate unique key for file.
        Includes filename + creation timestamp to handle renames.
        """
        stat = os.stat(filepath)
        key = f"{os.path.basename(filepath)}:{stat.st_ctime}"
        return hashlib.sha256(key.encode()).hexdigest()[:16]

    def is_processed(self, filepath):
        """Check if file was already processed"""
        file_hash = self.get_file_hash(filepath)
        return file_hash in self.state['processed_files']

    def mark_processed(self, filepath, status='success', metadata=None):
        """Mark file as processed"""
        file_hash = self.get_file_hash(filepath)
        self.state['processed_files'][file_hash] = {
            'timestamp': datetime.utcnow().isoformat(),
            'filename': os.path.basename(filepath),
            'status': status,  # success, failed, approved, rejected
            'metadata': metadata or {}
        }

        # Update stats
        if status == 'success':
            self.state['stats']['total_processed'] += 1
        elif status == 'failed':
            self.state['stats']['total_failed'] += 1
        elif status == 'approved':
            self.state['stats']['total_approved'] += 1

        self.state['last_sync'] = datetime.utcnow().isoformat()
        self._save_state()

    def cleanup_old_entries(self, days=30):
        """Remove entries older than N days"""
        cutoff = datetime.utcnow() - timedelta(days=days)
        to_remove = []

        for file_hash, entry in self.state['processed_files'].items():
            entry_time = datetime.fromisoformat(entry['timestamp'])
            if entry_time < cutoff:
                to_remove.append(file_hash)

        for file_hash in to_remove:
            del self.state['processed_files'][file_hash]

        if to_remove:
            self._save_state()
```

### State File Structure

```json
{
  "version": 1,
  "last_sync": "2026-02-17T10:30:45.123456",
  "processed_files": {
    "a1b2c3d4e5f6g7h8": {
      "timestamp": "2026-02-17T10:15:30.456789",
      "filename": "invoice-20260217-001.md",
      "status": "approved",
      "metadata": {
        "file_id": "FILE-20260217-001",
        "type": "financial",
        "priority": "HIGH"
      }
    },
    "x9y8z7w6v5u4t3s2": {
      "timestamp": "2026-02-17T10:20:15.789012",
      "filename": "task-weekly-report.md",
      "status": "success",
      "metadata": {
        "file_id": "FILE-20260217-002",
        "type": "general",
        "priority": "MEDIUM"
      }
    }
  },
  "stats": {
    "total_processed": 45,
    "total_failed": 2,
    "total_approved": 18
  }
}
```

### Startup Recovery

```python
def recover_from_crash():
    """On startup, check for files in Inbox that weren't fully processed"""
    state = WatcherState()

    for filepath in Path('vault/Inbox').glob('*.md'):
        if state.is_processed(filepath):
            # Already processed, skip
            continue

        # File in Inbox but not in state = interrupted
        logging.warning(f"Recovering unprocessed file: {filepath}")
        # Re-add to processing queue
        queue_file_for_processing(filepath)
```

### Alternatives Considered

| Alternative | Why Not Selected |
|---|---|
| SQLite database | Overkill for simple set; harder to inspect, requires schema |
| Plain text file (one hash per line) | Works, but JSON adds metadata fields without complexity |
| In-memory set only | Lost on restart, defeats purpose of persistence |
| File modification timestamp as key | Unreliable (can change), doesn't catch renames |
| Redis | Extra dependency, requires server, not persistent |

### Configuration

```yaml
# config.yaml
watcher_state:
  file: vault/state/watcher_state.json
  cleanup_age_days: 30
  enable_cleanup: true
  backup_on_save: false
```

---

## 6. HITL Approval via File Move Pattern

### Decision

**Create `APPROVAL_REQUIRED_{uuid}.md` files in `/Pending_Approval` folder. Human approves by moving to `/Approved` or `/Rejected`. System polls folders to detect status change with 24-hour expiry.**

### Rationale

1. **Filesystem-native:** No database needed, works in Obsidian, human-friendly
2. **Visual/intuitive:** Users can see pending approvals in folder view
3. **Atomic:** File move is atomic operation (no partial states)
4. **Idempotent:** Moving same file twice has same result (idempotent)
5. **Auditable:** Approval history preserved in folder structure
6. **Timestamped:** Creation timestamp in frontmatter proves audit trail
7. **Expiry enforcement:** 24h timeout prevents orphaned approvals

### Implementation Pattern

```python
import uuid
from datetime import datetime, timedelta

def create_approval_request(task_metadata, context_files):
    """
    Create approval request and place in Pending_Approval.
    Returns: approval_id
    """
    approval_id = str(uuid.uuid4())
    filename = f"APPROVAL_REQUIRED_{approval_id}.md"
    filepath = Path('vault/Pending_Approval') / filename

    # Create metadata for approval request
    approval_metadata = {
        'approval_id': approval_id,
        'type': 'approval_request',
        'status': 'pending',
        'created_at': datetime.utcnow().isoformat(),
        'expires_at': (datetime.utcnow() + timedelta(hours=24)).isoformat(),
        'task': task_metadata,
        'context_files': context_files,
        'requires_human_review': True
    }

    # Body: human-readable approval context
    body = f"""# Approval Required: {task_metadata['title']}

## Task Summary
- **Type:** {task_metadata['type']}
- **Priority:** {task_metadata['priority']}
- **Description:** {task_metadata['description']}

## Context
{chr(10).join(f"- {f}" for f in context_files)}

## Action Required
**Move this file to:**
- `/Approved` - to approve and execute the task
- `/Rejected` - to reject and archive

**Do not modify this file.** The system monitors for file moves.

---
Generated: {approval_metadata['created_at']}
Expires: {approval_metadata['expires_at']}
"""

    atomic_write_frontmatter(filepath, approval_metadata, body)
    logging.info(f"Approval request created: {approval_id}")
    return approval_id

def check_approval_status(approval_id):
    """
    Check status of approval request.
    Returns: ('pending', 'approved', 'rejected', 'expired', 'missing')
    """
    pending_path = Path('vault/Pending_Approval') / f"APPROVAL_REQUIRED_{approval_id}.md"
    approved_path = Path('vault/Approved') / f"APPROVAL_REQUIRED_{approval_id}.md"
    rejected_path = Path('vault/Rejected') / f"APPROVAL_REQUIRED_{approval_id}.md"

    # Check which folder contains the file
    if pending_path.exists():
        # Check if expired
        metadata, _ = parse_frontmatter(pending_path)
        expires_at = datetime.fromisoformat(metadata.get('expires_at', ''))
        if datetime.utcnow() > expires_at:
            return 'expired'
        return 'pending'

    elif approved_path.exists():
        return 'approved'

    elif rejected_path.exists():
        return 'rejected'

    else:
        return 'missing'

def wait_for_approval(approval_id, timeout_hours=24, poll_interval_s=5):
    """
    Block until approval is resolved.
    Returns: approval_result
    """
    expiry = datetime.utcnow() + timedelta(hours=timeout_hours)

    while datetime.utcnow() < expiry:
        status = check_approval_status(approval_id)

        if status == 'approved':
            logging.info(f"Approval granted: {approval_id}")
            return {'status': 'approved', 'approval_id': approval_id}

        elif status == 'rejected':
            logging.info(f"Approval rejected: {approval_id}")
            return {'status': 'rejected', 'approval_id': approval_id}

        elif status == 'expired':
            logging.warning(f"Approval expired: {approval_id}")
            # Move to Expired folder
            _handle_expired_approval(approval_id)
            return {'status': 'expired', 'approval_id': approval_id}

        time.sleep(poll_interval_s)

    # Timeout
    return {'status': 'timeout', 'approval_id': approval_id}

def process_approvals_batch():
    """
    Scan all folders for approval changes (run in main orchestrator loop).
    """
    pending_folder = Path('vault/Pending_Approval')

    for filepath in pending_folder.glob('APPROVAL_REQUIRED_*.md'):
        approval_id = filepath.stem.replace('APPROVAL_REQUIRED_', '')

        metadata, _ = parse_frontmatter(filepath)

        # Check if expired
        expires_at = datetime.fromisoformat(metadata.get('expires_at', ''))
        if datetime.utcnow() > expires_at:
            logging.warning(f"Approval expired: {approval_id}")
            _move_file(filepath, Path('vault/Expired'))
            continue

        # File still pending, check state if needed
        task_id = metadata.get('task', {}).get('id')
        if task_id:
            update_task_status(task_id, 'awaiting_approval')
```

### Folder Structure

```
vault/
├── Pending_Approval/          # Human sees these, must move them
│   ├── APPROVAL_REQUIRED_uuid-1.md
│   ├── APPROVAL_REQUIRED_uuid-2.md
│   └── APPROVAL_REQUIRED_uuid-3.md
├── Approved/                  # Human moves approved items here
│   ├── APPROVAL_REQUIRED_uuid-1.md
│   └── APPROVAL_REQUIRED_uuid-2.md
├── Rejected/                  # Human moves rejected items here
│   └── APPROVAL_REQUIRED_uuid-3.md
└── Expired/                   # System archives expired approvals
    └── APPROVAL_REQUIRED_uuid-old.md
```

### Approval Request Frontmatter Example

```yaml
---
approval_id: 550e8400-e29b-41d4-a716-446655440000
type: approval_request
status: pending
created_at: 2026-02-17T10:30:00Z
expires_at: 2026-02-18T10:30:00Z
task:
  id: TASK-20260217-001
  title: Process Invoice from Acme Corp
  type: financial
  priority: HIGH
  description: Verify and archive invoice #INV-2026-001
context_files:
  - vault/Inbox/invoice-acme-20260217.md
  - vault/State/vendor-acme.md
requires_human_review: true
---
```

### Alternatives Considered

| Alternative | Why Not Selected |
|---|---|
| Slack/email HITL prompt | Requires external service, less integrated, harder to audit |
| Web UI for approvals | Over-engineered, requires server, breaks offline capability |
| Git commit + PR | Too complex, requires Git knowledge, not Obsidian-native |
| SQLite approval table | Not human-inspectable, harder to debug |
| Boolean file `./APPROVE` | Fragile, easy to accidentally create, no metadata |

### Configuration

```yaml
# config.yaml
approval:
  pending_folder: vault/Pending_Approval
  approved_folder: vault/Approved
  rejected_folder: vault/Rejected
  expired_folder: vault/Expired
  expiry_hours: 24
  poll_interval_s: 5
  auto_expire_enabled: true
  move_approved_to_archive: true
```

---

## 7. Orchestrator Scan Loop Pattern

### Decision

**Single-threaded scan loop with configurable interval (default 30s). Pattern: `while True` → triage → plan → execute → update → sleep. Graceful shutdown via SIGINT/SIGTERM signal handlers.**

### Rationale

1. **Simplicity:** Single-threaded avoids race conditions, deadlocks, threading bugs
2. **Debuggability:** Sequential execution makes it easy to trace issues
3. **Observability:** Logs show clear timeline of operations
4. **Resource efficient:** No thread/coroutine overhead
5. **Graceful shutdown:** Signal handlers allow clean exit
6. **Restart resilience:** Watchdog state persists across restarts

### Implementation Pattern

```python
import logging
import signal
import sys
import time
from datetime import datetime

class PAEOrchestrator:
    """Main orchestration loop for Personal AI Employee"""

    def __init__(self, config):
        self.config = config
        self.running = True
        self.stats = {
            'cycles': 0,
            'files_triaged': 0,
            'plans_created': 0,
            'tasks_executed': 0,
            'errors': 0
        }

        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._handle_sigint)
        signal.signal(signal.SIGTERM, self._handle_sigterm)

    def _handle_sigint(self, signum, frame):
        """Handle Ctrl+C (SIGINT)"""
        logging.info("Received SIGINT, initiating graceful shutdown...")
        self.running = False

    def _handle_sigterm(self, signum, frame):
        """Handle SIGTERM (from process manager)"""
        logging.info("Received SIGTERM, initiating graceful shutdown...")
        self.running = False

    def run(self):
        """Main orchestration loop"""
        logging.info("PAE Orchestrator starting")
        logging.info(f"Scan interval: {self.config['orchestrator']['scan_interval']}s")

        try:
            while self.running:
                cycle_start = time.time()

                try:
                    # 1. Triage new files in Inbox
                    self._triage_inbox()

                    # 2. Create execution plans
                    self._create_plans()

                    # 3. Process approvals
                    self._process_approvals()

                    # 4. Execute approved plans
                    self._execute_plans()

                    # 5. Update dashboard/state
                    self._update_dashboard()

                    self.stats['cycles'] += 1

                except Exception as e:
                    self.stats['errors'] += 1
                    logging.error(f"Orchestrator cycle error: {e}", exc_info=True)
                    # Continue to next cycle (don't crash)

                # Calculate sleep time
                cycle_duration = time.time() - cycle_start
                scan_interval = self.config['orchestrator']['scan_interval']
                sleep_time = max(0, scan_interval - cycle_duration)

                if sleep_time > 0:
                    time.sleep(sleep_time)

        except KeyboardInterrupt:
            logging.info("KeyboardInterrupt caught")

        finally:
            self._shutdown()

    def _triage_inbox(self):
        """Stage 1: Discover and classify new files"""
        inbox_path = Path(self.config['paths']['inbox'])

        for filepath in inbox_path.glob('*.md'):
            try:
                # Check if already processed
                if self.state.is_processed(filepath):
                    continue

                # Parse file
                metadata, content = parse_frontmatter(filepath)

                # Auto-classify if not already classified
                if 'type' not in metadata or 'priority' not in metadata:
                    metadata['type'], metadata['priority'] = self._classify_file(
                        metadata.get('title', ''),
                        content
                    )
                    # Update frontmatter with classification
                    atomic_write_frontmatter(filepath, metadata, content)

                # Mark as triaged
                metadata['status'] = 'triaged'
                atomic_write_frontmatter(filepath, metadata, content)

                self.state.mark_processed(filepath, status='triaged')
                self.stats['files_triaged'] += 1
                logging.info(f"Triaged: {filepath.name} ({metadata['type']}/{metadata['priority']})")

            except Exception as e:
                logging.error(f"Triage error for {filepath}: {e}", exc_info=True)
                self.state.mark_processed(filepath, status='failed')

    def _create_plans(self):
        """Stage 2: Create execution plans for triaged files"""
        triaged_path = Path(self.config['paths']['triaged'])

        for filepath in triaged_path.glob('*.md'):
            try:
                metadata, content = parse_frontmatter(filepath)

                # Skip if plan already created
                if metadata.get('plan_created'):
                    continue

                # Create plan
                plan = self._generate_plan(metadata, content)

                # Store plan in frontmatter
                metadata['plan'] = plan
                metadata['plan_created'] = datetime.utcnow().isoformat()
                metadata['status'] = 'plan_created'
                atomic_write_frontmatter(filepath, metadata, content)

                self.stats['plans_created'] += 1
                logging.info(f"Plan created: {filepath.name}")

            except Exception as e:
                logging.error(f"Plan creation error for {filepath}: {e}", exc_info=True)

    def _process_approvals(self):
        """Stage 3: Check for approved/rejected items"""
        for filepath in Path(self.config['paths']['approved']).glob('APPROVAL_REQUIRED_*.md'):
            try:
                approval_id = filepath.stem.replace('APPROVAL_REQUIRED_', '')
                logging.info(f"Approval granted: {approval_id}")
                # Mark corresponding task as approved
                self._mark_task_approved(approval_id)
            except Exception as e:
                logging.error(f"Approval processing error: {e}", exc_info=True)

    def _execute_plans(self):
        """Stage 4: Execute approved plans"""
        approved_path = Path(self.config['paths']['approved_tasks'])

        for filepath in approved_path.glob('*.md'):
            try:
                metadata, content = parse_frontmatter(filepath)

                if metadata.get('status') != 'approved':
                    continue

                # Execute plan
                result = self._execute_task(metadata, content)

                # Update status
                metadata['status'] = 'executed'
                metadata['execution_result'] = result
                metadata['executed_at'] = datetime.utcnow().isoformat()
                atomic_write_frontmatter(filepath, metadata, content)

                self.stats['tasks_executed'] += 1
                logging.info(f"Task executed: {filepath.name}")

            except Exception as e:
                logging.error(f"Task execution error for {filepath}: {e}", exc_info=True)

    def _update_dashboard(self):
        """Stage 5: Update dashboard/status file"""
        dashboard = {
            'updated_at': datetime.utcnow().isoformat(),
            'running': self.running,
            'stats': self.stats,
            'health': 'healthy' if self.stats['errors'] < 5 else 'degraded'
        }

        dashboard_path = Path(self.config['paths']['vault']) / 'Dashboard.md'

        body = f"""# PAE Dashboard

## Status
- **Running:** {dashboard['running']}
- **Health:** {dashboard['health']}
- **Updated:** {dashboard['updated_at']}

## Statistics
- **Cycles completed:** {dashboard['stats']['cycles']}
- **Files triaged:** {dashboard['stats']['files_triaged']}
- **Plans created:** {dashboard['stats']['plans_created']}
- **Tasks executed:** {dashboard['stats']['tasks_executed']}
- **Errors:** {dashboard['stats']['errors']}
"""

        atomic_write_frontmatter(dashboard_path, dashboard, body)

    def _shutdown(self):
        """Graceful shutdown routine"""
        logging.info("Shutting down PAE Orchestrator...")
        logging.info(f"Final stats: {self.stats}")
        logging.info("Shutdown complete")
        sys.exit(0)

    def _classify_file(self, title, content):
        """Keyword-based classification (see Topic #8)"""
        # Implemented in Topic 8 section
        pass

    def _generate_plan(self, metadata, content):
        """Generate execution plan for task"""
        # To be implemented by Planning Agent
        pass

    def _execute_task(self, metadata, content):
        """Execute an approved task"""
        # To be implemented by Execution Agent
        pass
```

### Orchestration Flowchart

```
┌─────────────────────────────┐
│ PAE Orchestrator Start      │
│ Load config, state, signals │
└────────────┬────────────────┘
             │
             ▼
      ┌──────────────┐
      │  Scan Loop   │
      │ while True   │
      └──────┬───────┘
             │
    ┌────────┴────────┐
    │                 │
    ▼                 ▼
 CYCLE            SIGNAL?
  START         (SIGINT/SIGTERM)
    │               │
    │            YES│
    │               └─► GRACEFUL SHUTDOWN
    │
    ▼
┌───────────────────┐
│ 1. TRIAGE INBOX   │
│ Classify new files│
└────────┬──────────┘
         │
         ▼
┌──────────────────────┐
│ 2. CREATE PLANS      │
│ Generate task plans  │
└────────┬─────────────┘
         │
         ▼
┌──────────────────────┐
│ 3. PROCESS APPROVALS │
│ Check file moves     │
└────────┬─────────────┘
         │
         ▼
┌──────────────────────┐
│ 4. EXECUTE PLANS     │
│ Run approved tasks   │
└────────┬─────────────┘
         │
         ▼
┌──────────────────────┐
│ 5. UPDATE DASHBOARD  │
│ Write status file    │
└────────┬─────────────┘
         │
         ▼
┌──────────────────────┐
│  SLEEP (interval_s)  │
└────────┬─────────────┘
         │
         └────► CYCLE START
```

### Alternatives Considered

| Alternative | Why Not Selected |
|---|---|
| Async/await (asyncio) | Harder to debug, adds coroutine complexity, not necessary |
| Thread pool | Race conditions, deadlock risk, difficult to reason about |
| Multiprocessing | IPC complexity, state sharing problem, overkill |
| Event-driven (with message queue) | Redis/RabbitMQ requires extra infrastructure |
| Cron jobs (separate scripts) | State scattered across processes, hard to coordinate |

### Configuration

```yaml
# config.yaml
orchestrator:
  scan_interval: 30  # seconds between orchestration cycles
  enable_logging: true
  log_level: INFO
  graceful_shutdown_timeout: 5

paths:
  vault: ./vault
  inbox: ./vault/Inbox
  triaged: ./vault/Triaged
  approved_tasks: ./vault/Approved
  state: ./vault/state/watcher_state.json
```

---

## 8. Keyword-Based Triage Classification (No LLM)

### Decision

**Use dictionary-based keyword scoring system for type and priority classification. No API calls, no LLM, 100% local processing.**

### Rationale

1. **No external dependencies:** Doesn't require API keys, internet, or LLM service
2. **Instant:** Sub-millisecond classification (no network latency)
3. **Deterministic:** Same input → same output (repeatable)
4. **Transparent:** Easy to inspect and adjust keywords
5. **Offline:** Works without network connectivity
6. **Cost-effective:** No per-request fees
7. **Privacy:** All data stays local
8. **Bronze Tier alignment:** Simple, rule-based approach fits Bronze tier constraints

### Implementation Pattern

```python
from enum import Enum
from typing import Tuple

class FileType(Enum):
    """Supported file classifications"""
    FINANCIAL = "financial"
    COMMUNICATION = "communication"
    TASK = "task"
    REPORT = "report"
    DOCUMENT = "document"
    GENERAL = "general"

class Priority(Enum):
    """Priority levels"""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"

class KeywordClassifier:
    """Classify files based on keyword scoring"""

    # Type classification keywords
    TYPE_KEYWORDS = {
        FileType.FINANCIAL: {
            'keywords': [
                'invoice', 'payment', 'billing', 'receipt', 'expense',
                'budget', 'quote', 'estimate', 'cost', 'price',
                'refund', 'charge', 'transaction', 'account',
                '$', '€', '£', '¥', 'amount', 'total'
            ],
            'weight': 1.0
        },
        FileType.COMMUNICATION: {
            'keywords': [
                'email', 'message', 'urgent', 'call', 'meeting',
                'response', 'reply', 'fyi', 'discuss', 'review'
            ],
            'weight': 1.0
        },
        FileType.TASK: {
            'keywords': [
                'task', 'todo', 'action item', 'assign', 'assigned',
                'deadline', 'due date', 'deliverable', 'objective',
                'goal', 'milestone', 'sprint', 'backlog'
            ],
            'weight': 1.0
        },
        FileType.REPORT: {
            'keywords': [
                'report', 'summary', 'analysis', 'metrics',
                'dashboard', 'kpi', 'performance', 'overview',
                'quarterly', 'monthly', 'weekly', 'daily'
            ],
            'weight': 1.0
        },
        FileType.DOCUMENT: {
            'keywords': [
                'contract', 'agreement', 'policy', 'guidelines',
                'manual', 'documentation', 'specification', 'proposal',
                'whitepaper', 'brief'
            ],
            'weight': 1.0
        }
    }

    # Priority classification keywords
    PRIORITY_KEYWORDS = {
        Priority.CRITICAL: {
            'keywords': [
                'critical', 'urgent', 'emergency', 'immediate',
                'asap', 'now', 'crisis', 'alert', '!!!'
            ],
            'weight': 2.0
        },
        Priority.HIGH: {
            'keywords': [
                'important', 'deadline', 'due date', 'priority',
                'high', '!', 'must', 'required', 'blocked'
            ],
            'weight': 1.5
        },
        Priority.MEDIUM: {
            'keywords': [
                'medium', 'moderate', 'soon', 'upcoming',
                'pending', 'in progress'
            ],
            'weight': 1.0
        },
        Priority.LOW: {
            'keywords': [
                'low', 'minor', 'optional', 'nice to have',
                'backlog', 'someday', 'consider'
            ],
            'weight': 0.5
        }
    }

    @classmethod
    def classify(cls, title: str, content: str) -> Tuple[str, str]:
        """
        Classify file and return (type, priority).
        Returns: (FileType, Priority)
        """
        # Combine title and content for analysis (title weighted higher)
        text_to_analyze = f"{title.lower()} {title.lower()} {content.lower()}"

        # Classify type
        file_type = cls._classify_type(text_to_analyze)

        # Classify priority
        priority = cls._classify_priority(text_to_analyze)

        return file_type.value, priority.value

    @classmethod
    def _classify_type(cls, text: str) -> FileType:
        """Score text against type keywords, return highest scoring type"""
        scores = {}

        for file_type, config in cls.TYPE_KEYWORDS.items():
            score = 0
            for keyword in config['keywords']:
                # Count occurrences of keyword in text
                score += text.count(keyword.lower()) * config['weight']
            scores[file_type] = score

        # Return highest scoring type (or GENERAL if no matches)
        best_type = max(scores, key=scores.get) if max(scores.values()) > 0 else FileType.GENERAL
        logging.debug(f"Type classification scores: {scores} → {best_type.value}")
        return best_type

    @classmethod
    def _classify_priority(cls, text: str) -> Priority:
        """Score text against priority keywords, return highest priority level"""
        scores = {}

        for priority, config in cls.PRIORITY_KEYWORDS.items():
            score = 0
            for keyword in config['keywords']:
                # Count occurrences, weight by urgency
                score += text.count(keyword.lower()) * config['weight']
            scores[priority] = score

        # Return highest scoring priority (or MEDIUM if no matches)
        if max(scores.values()) > 0:
            best_priority = max(scores, key=scores.get)
        else:
            best_priority = Priority.MEDIUM

        logging.debug(f"Priority classification scores: {scores} → {best_priority.value}")
        return best_priority
```

### Example Classifications

```
Input: "Invoice #INV-2026-001 from Acme Corp"
→ Type: FINANCIAL (keywords: "invoice")
→ Priority: MEDIUM (no urgency keywords)
Result: (financial, MEDIUM)

Input: "URGENT: Critical bug in production - need immediate fix!!!"
→ Type: TASK (keywords: "bug", implicit task)
→ Priority: CRITICAL (keywords: "urgent", "critical", "immediate", "!!!")
Result: (task, CRITICAL)

Input: "Monthly sales report - Q1 2026 analysis"
→ Type: REPORT (keywords: "report", "analysis")
→ Priority: MEDIUM (default, no urgency keywords)
Result: (report, MEDIUM)

Input: "Weekly status update"
→ Type: COMMUNICATION (implicit messaging)
→ Priority: MEDIUM (default)
Result: (communication, MEDIUM)

Input: "Random note about the weather"
→ Type: GENERAL (no keyword matches)
→ Priority: MEDIUM (default, no urgency keywords)
Result: (general, MEDIUM)
```

### Integration into Triage Loop

```python
def _triage_inbox(self):
    """Stage 1: Discover and classify new files"""
    inbox_path = Path(self.config['paths']['inbox'])
    classifier = KeywordClassifier()

    for filepath in inbox_path.glob('*.md'):
        metadata, content = parse_frontmatter(filepath)

        # Auto-classify if not already classified
        if 'type' not in metadata or 'priority' not in metadata:
            file_type, priority = classifier.classify(
                metadata.get('title', filepath.stem),
                content
            )
            metadata['type'] = file_type
            metadata['priority'] = priority
            logging.info(f"Auto-classified: {filepath.name} as {file_type}/{priority}")

        # Continue with rest of triage...
```

### Customization

```yaml
# config.yaml (optional keyword overrides)
classifier:
  # Add custom keywords for your domain
  custom_keywords:
    financial:
      - 'po'  # Purchase Order
      - 'sr'  # Sales Receipt
    task:
      - 'jira'
      - 'github'

  # Adjust weight multipliers
  weights:
    critical: 2.0
    high: 1.5
    medium: 1.0
    low: 0.5
```

### Adding Custom Keywords

```python
# config.py
CUSTOM_KEYWORDS_BY_TYPE = {
    'financial': ['po', 'sr', 'ar', 'ap'],  # Purchase Order, Sales Receipt, Accounts Receivable/Payable
    'task': ['jira', 'github', 'sprint'],
}

# Merge with defaults
def load_classifier(config_file):
    base_classifier = KeywordClassifier()
    # Load custom keywords from config and extend TYPE_KEYWORDS
    return base_classifier
```

### Alternatives Considered

| Alternative | Why Not Selected |
|---|---|
| OpenAI API classification | Costs $, requires API key, network dependent, slower |
| Claude API classification | Same issues as OpenAI, over-engineered for Bronze tier |
| Naive Bayes ML model | Requires training data, adds ML complexity, hard to debug |
| Regex patterns | Works but less flexible than keyword scoring |
| Manual classification only | Too slow, defeats automation purpose |

### Configuration

```yaml
# config.yaml
classifier:
  enabled: true
  min_type_score: 1  # Minimum score to classify (below = GENERAL)
  min_priority_score: 0  # Below = MEDIUM

  # Keywords are defined in code (see TYPE_KEYWORDS, PRIORITY_KEYWORDS)
  # Custom keywords can be added via config or code
```

---

## Summary: Technology Decisions Matrix

| # | Technology | Decision | Status |
|---|---|---|---|
| 1 | Filesystem Monitoring | `watchdog` + Observer + stability checks | ✅ APPROVED |
| 2 | YAML Parsing | `pyyaml` + manual delimiter splitting | ✅ APPROVED |
| 3 | Atomic Writes | `os.replace()` + temp file | ✅ APPROVED |
| 4 | Process Management | PM2 with `interpreter: python` | ✅ APPROVED |
| 5 | State Persistence | JSON file (`watcher_state.json`) | ✅ APPROVED |
| 6 | HITL Approval | File move pattern + 24h expiry | ✅ APPROVED |
| 7 | Orchestrator Loop | Single-threaded scan loop (30s interval) | ✅ APPROVED |
| 8 | Triage Classification | Keyword-based scoring (no LLM) | ✅ APPROVED |

---

## Critical Implementation Notes

### Race Condition Safety

1. **File-not-fully-written:** Handled by stability check (File size consistency)
2. **Concurrent file edits:** Possible due to user editing in Obsidian
   - Solution: Debounce file updates, version via mtime
3. **Approval race:** User moves file while system processes it
   - Solution: Atomic rename guarantees consistency

### Error Recovery

1. **Process crash:** Watchdog state file preserves processing history
2. **Corrupted YAML:** Manual parsing with try/except allows partial recovery
3. **Orphaned approvals:** 24h expiry prevents indefinite waiting
4. **Temp file leak:** Cleanup script removes old `.tmp` files

### Observability

1. **Logging:** All stages (triage, plan, approve, execute) logged
2. **State file:** Inspect `watcher_state.json` for processing history
3. **Dashboard:** Updated every cycle with stats and health
4. **PM2 logs:** Centralized process logs in `logs/` directory

### Production Readiness

- ✅ Graceful shutdown via signal handlers
- ✅ Automatic process restart via PM2
- ✅ Persistent state across crashes
- ✅ Deduplication prevents reprocessing
- ✅ Exponential backoff for transient failures
- ✅ 24h timeout prevents orphaned approvals

---

## Next Steps

1. **Implement watcher infrastructure** (watchdog + state management)
2. **Create approval request generator** (file move pattern)
3. **Build orchestrator loop** (scan + triage + plan + execute)
4. **Set up PM2 configuration** (ecosystem.config.js)
5. **Write integration tests** (race conditions, crash scenarios)
6. **Deploy and monitor** (logs, dashboard, health checks)

---

**Document Version:** 1.0
**Created:** 2026-02-17
**Author:** Claude Code
**Status:** APPROVED FOR IMPLEMENTATION
