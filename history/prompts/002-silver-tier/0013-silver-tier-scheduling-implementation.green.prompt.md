---
id: "0013"
title: Silver Tier Scheduling Implementation
stage: green
date: 2026-02-21
surface: agent
model: claude-sonnet-4-6
feature: 002-silver-tier
branch: 001-bronze-tier
user: USER-PC
command: "manual: fulfill Basic scheduling (cron/Task Scheduler) requirement"
labels: ["scheduling", "silver-tier", "tdd", "install_schedule", "uninstall_schedule", "schtasks", "crontab", "fr-h"]
links:
  spec: specs/002-silver-tier/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - tests/test_install_schedule.py
  - src/skills/install_schedule.py
  - src/skills/uninstall_schedule.py
  - config/settings.yaml
tests:
  - "tests/test_install_schedule.py — 7 new tests (4 POSIX skipped on Windows) — all PASS"
  - "Full suite: 423 passed, 4 skipped (was 416)"
---

## Prompt

this Requirement: Basic scheduling (cron/Task Scheduler) Status: ❌ Missing Notes: No install_schedule.py or equivalent. fulfill

## Response snapshot

Implemented Silver Tier FR-H01–FR-H05 (Basic Scheduling) following TDD Red→Green cycle:

**Red phase**: wrote `tests/test_install_schedule.py` with 11 test cases (7 Windows, 4 POSIX).
All 7 Windows tests confirmed FAIL (ModuleNotFoundError) before implementation.

**Green phase**: implemented two skills:

`src/skills/install_schedule.py`:
- Platform detection via `sys.platform`
- **Windows**: `schtasks /delete /tn <name> /f` (idempotent) → `schtasks /create` for `FTE-Orchestrator` (ONSTART) + `FTE-WeeklyBriefing` (Mon 08:00 weekly)
- **POSIX**: `crontab -l` → strip all `# FTE` lines → append `@reboot ... # FTE` + `0 8 * * 1 ... # FTE` → `crontab -`
- Prints confirmation; writes LOW audit entry via `log_action()`
- Returns `{processed, platform, tasks_created, tasks_updated, errors, skipped}`

`src/skills/uninstall_schedule.py`:
- Windows: `schtasks /delete /tn FTE-Orchestrator /f` + `/tn FTE-WeeklyBriefing /f`
- POSIX: strip all `# FTE` lines from crontab, preserve all other entries
- Writes LOW audit entry; returns same result shape

`config/settings.yaml` updates (FR-H05):
- `orchestrator.scan_interval: 30 → 120`
- `approval.expiry_hours: 24 → 48`

**Test results**: 7 passed, 4 skipped (POSIX tests correctly skip on win32).
Full suite: **423 passed, 4 skipped** — Bronze invariant (416) intact.

## Outcome

- ✅ Impact: FR-H01–FR-H05 fully implemented. Basic scheduling requirement fulfilled. install_schedule.py + uninstall_schedule.py both created with Windows schtasks + POSIX crontab support. Idempotency: delete+recreate on Windows; strip+append on POSIX.
- 🧪 Tests: 7 new tests pass. Full suite 423 passed / 4 skipped. Bronze invariant maintained.
- 📁 Files: tests/test_install_schedule.py (new), src/skills/install_schedule.py (new), src/skills/uninstall_schedule.py (new), config/settings.yaml (scan_interval + expiry_hours updated)
- 🔁 Next prompts: T001 (install Silver dependencies) → T002 (extend settings.yaml with Gmail/LinkedIn/WhatsApp stanzas) → T007 (rate_limiter tests) → T008 (idempotency tests) → T009 (opt_out tests)
- 🧠 Reflection: TDD cycle clean — red phase confirmed via ImportError before any implementation. Platform detection via sys.platform is the correct approach; POSIX tests skip cleanly on Windows via pytest.mark.skipif. The idempotency strategy differs per platform (delete+recreate vs strip+append) which is the correct OS-native approach.

## Evaluation notes (flywheel)

- Failure modes observed: None. Clean red→green cycle.
- Graders run and results (PASS/FAIL): pytest tests/test_install_schedule.py — 7 PASS / 4 SKIP. Full suite 423 PASS / 4 SKIP.
- Prompt variant (if applicable): Direct implementation request after gap analysis
- Next experiment: Implement Phase 2 foundational safety modules (rate_limiter, idempotency, opt_out) before proceeding to watcher implementations
