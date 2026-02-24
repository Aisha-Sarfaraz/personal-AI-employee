---
id: "0015"
title: WatchdogMonitor Auto-Restart Implementation
stage: green
date: 2026-02-22
surface: agent
model: claude-sonnet-4-6
feature: 002-silver-tier
branch: 001-bronze-tier
user: USER-PC
command: "yes (approve WatchdogMonitor auto-restart gap fix)"
labels: ["watchdog", "auto-restart", "bronze-gap-fix", "tdd", "documents.md", "section-7.4"]
links:
  spec: specs/001-bronze-tier/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - src/watchdog_monitor.py
  - tests/test_watcher.py
tests:
  - "tests/test_watcher.py::TestWatchdogMonitorAutoRestart — 5 new tests — all PASS"
  - "Full suite: 428 passed, 4 skipped (was 423)"
---

## Prompt

yes

(Approving: add auto-restart capability to WatchdogMonitor per Documents.md §7.4 gap finding)

## Response snapshot

Implemented auto-restart capability for WatchdogMonitor following TDD Red→Green cycle.

**Gap identified**: Documents.md §7.4 shows watchdog pattern that restarts dead processes via factories. Previous WatchdogMonitor only detected failures and logged HIGH audit entries — no restart.

**Red phase**: Added 5 tests to `TestWatchdogMonitorAutoRestart` class in `tests/test_watcher.py`:
- `test_detects_dead_thread_and_calls_factory`
- `test_updates_thread_dict_after_restart`
- `test_no_factory_still_logs_failure`
- `test_alive_thread_not_restarted`
- `test_restart_writes_audit_log`
All 5 confirmed FAIL (TypeError: unexpected keyword argument 'watcher_factories').

**Green phase** — `src/watchdog_monitor.py` changes:
1. Added `watcher_factories: dict[str, Any] | None = None` parameter to `__init__`
2. Rewrote `check_watcher_health()`:
   - On dead thread + factory present: calls factory() → updates `watcher_threads[name]` → writes HIGH audit log "restarted watcher thread: {name}"
   - On dead thread + no factory: writes HIGH audit log "watcher {name} is not alive. No factory registered."
   - On alive thread: does nothing (factory NOT called)
3. Removed duplicate `log_action` calls from `run()` loop (now handled inside `check_watcher_health`)

**Test results**: 5 new tests pass. Full suite: **428 passed, 4 skipped**.

## Outcome

- ✅ Impact: Documents.md §7.4 Watchdog auto-restart gap closed. WatchdogMonitor now restarts dead watcher threads via configurable factory callbacks, writes audit trail for every restart. Bronze Tier now fully conformant with Documents.md.
- 🧪 Tests: 5 new passing. Full suite 428/428.
- 📁 Files: src/watchdog_monitor.py (watcher_factories param + restart logic in check_watcher_health), tests/test_watcher.py (5 new tests)
- 🔁 Next prompts: Proceed with Silver Tier /sp.implement — Phase 1 setup tasks (T001-T006)
- 🧠 Reflection: Thread-based restart (vs subprocess-based in Documents.md §7.4) is the correct approach for our architecture since watchers are daemon threads not subprocesses. Factory pattern is clean and testable.

## Evaluation notes (flywheel)

- Failure modes observed: None. Clean red→green cycle.
- Graders run and results (PASS/FAIL): pytest tests/test_watcher.py::TestWatchdogMonitorAutoRestart — 5 PASS. Full suite 428 PASS / 4 SKIP.
- Prompt variant (if applicable): Gap fix — user approval then implementation
- Next experiment: Wire watcher_factories in orchestrator.py so real orchestrator benefits from restart capability
