# Silver Tier Implementation Plan

**Feature**: 002-silver-tier — AI Business Assistant Upgrade
**Date**: 2026-02-20
**Status**: COMPLETE (531 tests passing, 73.36% coverage, SC-010–SC-020 verified)
**Branch**: 002-silver-tier (implement from here)
**Predecessor**: 001-bronze-tier (385 tests, SC-001–SC-009 verified)
**Constitution**: `.specify/memory/constitution.md` §2.2 [SILVER]

---

## Plan Metadata

| Field | Value |
|-------|-------|
| Spec | `specs/002-silver-tier/spec.md` |
| Data Model | `specs/002-silver-tier/data-model.md` |
| Research | `specs/002-silver-tier/research.md` |
| Contracts | `specs/002-silver-tier/contracts/` |
| Target test count | 385 (Bronze) + ~120 new = ~505 total |
| Coverage target | ≥ 70% line coverage on `src/` |
| Success criteria | SC-010 through SC-020 all pass |

---

## Scope

### In Scope
1. Core safety infrastructure: `idempotency.py`, `rate_limiter.py`, `opt_out.py`
2. Gmail watcher: OAuth2 polling, flat-mock dry-run, `_parse_message()` normaliser
3. WhatsApp watcher: already done (31 tests) — verify base_watcher.py extension compatibility
4. LinkedIn watcher: Playwright engagement reader, session management, mock dry-run
5. Email-mcp integration: real send via MCP Python SDK, opt-out, AI footer, idempotency
6. New skills: `detect_lead`, `generate_plan`, `generate_linkedin_post`, `weekly_briefing`
7. Scheduling: `install_schedule.py` + `uninstall_schedule.py` (Windows + POSIX)
8. Plan templates: 3 new entries in `plan_task.py` PLAN_TEMPLATES
9. Orchestrator wiring: 4 daemon threads, health dict, detect_lead + generate_plan in scan cycle
10. `execute_plan.py` extensions: queue drain + quarantine move
11. `update_dashboard.py` extensions: watcher health rows + quarantine/briefings counts
12. `base_watcher.py` extensions: `dry_run` property + `_load_mock_items()` helper
13. Config extensions: `settings.yaml` + `.env.example` + `requirements.txt`
14. Vault structure: new folders, mock files, template files, Business_Goals.md, Opt_Out_List.md
15. Tests: ~120 new tests covering all new modules + Silver E2E

### Out of Scope
- Finance watcher / Odoo (Gold)
- Facebook / Instagram / Twitter/X (Gold)
- Circuit breakers (Gold)
- Ralph Wiggum Stop hook (Gold)
- Structured JSON audit logging (Gold)
- Cloud deployment (Platinum)

### Non-Goals
- Modifying any existing Bronze test
- Refactoring Bronze core modules (`vault.py`, `frontmatter.py`, `approval.py`, `audit_logger.py`)
- Refactoring `plan_task.py` (extended additively only)
- Removing any existing Bronze functionality

### Bronze Invariant
All 385 Bronze tests must pass throughout Silver implementation. Run `pytest tests/ -k "not silver"`
at the start of each phase to verify Bronze baseline is intact.

---

## Implementation Phases

---

### Phase 1: Core Safety Infrastructure

**Goal**: Foundation modules that all other Silver components depend on. No Bronze code touched.

**Tasks**:

#### T01 — `src/core/rate_limiter.py`
- Implement `check_and_increment(vault_root, action_type, limit_per_hour) -> bool`
- JSON state at `vault/state/rate_limits.json`; epoch-hour window keys
- Prune keys older than 2 hours on each read/write
- Thread-safe: protect file I/O with `threading.Lock` (module-level lock)

**Acceptance**: `pytest tests/test_rate_limiter.py -v` — all tests pass.
**Tests (write first — TDD)**:
- `test_allows_within_limit` — first N calls return True
- `test_blocks_at_limit` — call N+1 returns False
- `test_resets_after_hour` — mock clock advance 1h; call returns True again
- `test_different_action_types_independent` — email and post_social independent counters
- `test_prunes_old_keys` — old hour keys removed
- `test_creates_state_file_if_absent` — auto-creates `vault/state/rate_limits.json`

#### T02 — `src/core/idempotency.py`
- Implement `generate_key(agent, action, details) -> str`
- Implement `check_and_store(vault_root, key, result, ttl_hours) -> tuple[bool, dict|None]`
- JSON state at `vault/state/idempotency_keys.json`; TTL pruning on every call
- Thread-safe file I/O

**Acceptance**: `pytest tests/test_idempotency.py -v` — all tests pass.
**Tests (TDD)**:
- `test_generate_key_format` — key matches pattern `{str}:{str}:{8hex}:{int}`
- `test_generate_key_deterministic` — same inputs → same key
- `test_new_key_stored` — `check_and_store` returns `(False, None)` for new key
- `test_existing_key_returns_cached` — second call returns `(True, cached_result)`
- `test_expired_key_treated_as_new` — TTL=0 forces expiry; key regenerated
- `test_prunes_expired_entries` — expired entries removed from file

#### T03 — `src/core/opt_out.py`
- Implement `is_opted_out(vault_root, email_address) -> bool`
- Parse `vault/Opt_Out_List.md`; lines starting with `- ` are email entries
- Case-insensitive; returns False if file absent

**Acceptance**: `pytest tests/test_opt_out.py -v` — all tests pass.
**Tests (TDD)**:
- `test_opted_out_email_blocked` — email in list returns True
- `test_not_opted_out_allowed` — email not in list returns False
- `test_case_insensitive` — `ALICE@EXAMPLE.COM` matches `alice@example.com`
- `test_missing_file_returns_false` — no Opt_Out_List.md → False
- `test_ignores_headings_and_blanks` — heading lines not parsed as emails
- `test_multiple_entries` — list with 5 entries works correctly

**Phase 1 exit gate**: All T01–T03 tests pass. 385 Bronze tests still pass.

---

### Phase 2: BaseWatcher Extension + Gmail Watcher

**Goal**: Extend base class with shared dry-run infrastructure; implement Gmail watcher.

**Tasks**:

#### T04 — `src/watchers/base_watcher.py` extension
- Add `dry_run: bool` property — checks `DRY_RUN` env var (case-insensitive `"true"`) or constructor flag
- Add `_load_mock_items(mock_folder: str) -> list[dict]` — reads `*.json` from folder; skips malformed files; returns `[]` if folder absent
- WhatsAppWatcher already uses this pattern — ensure backward compatibility

**Acceptance**: `pytest tests/test_watcher.py -v` — all existing tests still pass + new dry_run tests.
**Tests (TDD — add to existing test_watcher.py or new test_base_watcher.py)**:
- `test_dry_run_false_by_default` — env not set → `dry_run == False`
- `test_dry_run_true_from_env` — `DRY_RUN=true` in env → `dry_run == True`
- `test_load_mock_items_reads_json_files` — folder with 2 JSON files → 2 items returned
- `test_load_mock_items_skips_malformed` — 1 valid + 1 invalid JSON → 1 item returned
- `test_load_mock_items_empty_folder` — empty folder → `[]`
- `test_load_mock_items_missing_folder` — non-existent path → `[]`

#### T05 — `src/watchers/gmail_auth.py`
- One-time OAuth2 flow using `google_auth_oauthlib.flow.InstalledAppFlow`
- Reads `GMAIL_CLIENT_ID`, `GMAIL_CLIENT_SECRET` from `.env`
- Scopes: `["https://www.googleapis.com/auth/gmail.modify"]`
- Writes `vault/.gmail_token.json` on success
- Prints clear instructions for headless environments (prints auth URL if no browser)

**Acceptance**: Script runs without error in dry-run/test environment; token file written.
**Tests**: Minimal — mock OAuth flow; verify token file written. (Integration test only in real mode.)

#### T06 — `src/watchers/gmail_watcher.py`
- Implement `GmailWatcher(BaseWatcher)` with `check_for_updates()` and `_parse_message()`
- Dry-run path: `self._load_mock_items(gmail_mock_dir)` when `GMAIL_CLIENT_ID` absent or `DRY_RUN=true`
- Live path: load credentials → refresh if expired → `messages.list` → `messages.get` → `_parse_message` → mark read
- `_parse_message`: detect flat mock (no `"payload"` key) vs real API response; return normalized item dict
- State: `vault/state/gmail_watcher_state.json` for processed ID dedup
- On OAuth failure: MEDIUM audit entry; return `[]` (no crash)

**Acceptance**: `pytest tests/test_gmail_watcher.py -v` — all tests pass; SC-010 verified.
**Tests (TDD)**:
- `test_dry_run_returns_mock_items` — mock folder with sample_email.json → items returned
- `test_parse_message_flat_mock_schema` — flat dict → correct normalized item
- `test_parse_message_real_api_schema` — nested `payload.headers` dict → correct normalized item
- `test_dedup_skips_processed_ids` — ID in state file → skipped
- `test_marks_message_as_read` — `messages.modify` called with UNREAD removal
- `test_oauth_failure_returns_empty` — credential error → `[]` + MEDIUM audit entry
- `test_token_refresh_on_expiry` — expired token triggers refresh call
- `test_rate_limit_100_per_hour` — 101st call raises/skips without crashing

**Phase 2 exit gate**: T04–T06 tests pass. 385 Bronze tests still pass. Watcher health dict updated by GmailWatcher in mock mode.

---

### Phase 3: LinkedIn Watcher

**Goal**: Playwright-based LinkedIn engagement reader with session management.

**Tasks**:

#### T07 — `src/watchers/linkedin_watcher.py`
- Implement `LinkedInWatcher(BaseWatcher)` with `check_for_updates()` and `setup_session()`
- Dry-run path: session absent or `DRY_RUN=true` → `self._load_mock_items(linkedin_mock_dir)`
- Live path: `launch_persistent_context(vault/state/linkedin_session/)` → navigate to activity page → extract 5 posts
- Fields: `reactions` (from `aria-label`), `comments`, `post_preview` (first 200 chars), `post_url`, `id` (SHA256 of post_url[:12])
- Item type: `social_media_engagement`, source: `linkedin`, platform: `linkedin`
- Session expiry: if URL contains `/login` → LOW audit + return `[]`
- All Playwright calls in try/except; on exception: LOW audit + return `[]`

**Acceptance**: `pytest tests/test_linkedin_watcher.py -v` — all tests pass; SC-012 (LinkedIn thread) verified.
**Tests (TDD)**:
- `test_dry_run_returns_mock_items` — mock folder with sample_post.json → items returned
- `test_item_type_is_social_media_engagement` — items have correct type/source/platform
- `test_id_is_sha256_of_post_url` — id format verified
- `test_session_expired_returns_empty` — mock Playwright returning /login URL → `[]`
- `test_playwright_exception_returns_empty` — exception during page navigation → `[]`
- `test_setup_session_opens_headful_browser` — headless=False called for setup

**Phase 3 exit gate**: T07 tests pass. All Bronze tests pass. All 4 watcher classes importable.

---

### Phase 4: Email MCP Integration + Action Executor Extension

**Goal**: Wire real `send_email` via email-mcp (MCP SDK) and add `post_social` via Playwright.

**Tasks**:

#### T08 — `src/actions/action_executor.py` extensions
Extend existing `action_executor.py` WITHOUT modifying existing Bronze `_send_email` simulation path:

- `_send_email` (real mode, `dev_mode=false`):
  1. `opt_out.is_opted_out()` check — skip + log if opted out
  2. Append AI disclosure footer
  3. `rate_limiter.check_and_increment("send_email", 20)` — queue + return if limited
  4. `idempotency.check_and_store()` — return cached if exists
  5. Call `email-mcp` via MCP Python SDK (asyncio.run wrapper)
  6. Exponential backoff: 1s → 2s → 4s (3 attempts)
  7. On 3 failures: increment `fail_count`; return failure result

- `_post_social` (new action type, `post_social`):
  1. `rate_limiter.check_and_increment("post_social", 10)` — queue if limited
  2. `idempotency.check_and_store()` — return cached if exists
  3. Playwright with LinkedIn session; log `action:linkedin_post`
  4. Simulation: `{success:true, simulated:true}` when `dev_mode=true`

- Queue write: append to `vault/state/queue.json` when rate-limited

**Acceptance**: `pytest tests/test_action_executor.py -v` — all existing Bronze tests pass + new Silver tests.
**New tests (TDD)**:
- `test_send_email_appends_disclosure_footer`
- `test_send_email_skips_opted_out_recipient`
- `test_send_email_queues_when_rate_limited`
- `test_send_email_uses_cached_idempotency_result`
- `test_send_email_retries_with_backoff`
- `test_send_email_simulation_unchanged` — `dev_mode=true` still returns `simulated:true`
- `test_post_social_simulation` — `dev_mode=true` returns `simulated:true`
- `test_post_social_queues_when_rate_limited`

**Phase 4 exit gate**: T08 tests pass. All existing test_action_executor.py tests (Bronze) still pass.

---

### Phase 5: New Skills

**Goal**: Implement 4 new skills + 2 plan templates additions. All follow TDD.

**Tasks**:

#### T09 — `src/skills/plan_task.py` extension (3 new PLAN_TEMPLATES)
Add `lead`, `linkedin_post`, `social_media_engagement` templates to `PLAN_TEMPLATES` dict.
**No other changes to plan_task.py.**

**Acceptance**: `pytest tests/test_plan_task.py -v` — all Bronze tests pass + template existence verified.

#### T10 — `src/skills/detect_lead.py`
- Scan `vault/Needs_Action/` for items not already `type:lead`
- Keyword match (configurable; default list from spec FR-E02)
- Lead score: 1 per keyword (cap 10) + 2 if `source:gmail` + 1 if `priority:CRITICAL`
- On ≥2 keywords: update frontmatter in-place (`type:lead`, `priority:CRITICAL`, `lead_score`)
- Return `{processed, leads_detected, errors, skipped}`

**Acceptance**: `pytest tests/test_detect_lead.py -v` — all tests pass; SC-013 pipeline verified.
**Tests (TDD)**:
- `test_detects_lead_with_2_keywords`
- `test_does_not_detect_lead_with_1_keyword`
- `test_upgrades_type_to_lead`
- `test_upgrades_priority_to_critical`
- `test_calculates_lead_score_correctly`
- `test_skips_items_already_lead`
- `test_gmail_source_bonus`
- `test_returns_correct_result_dict`

#### T11 — `src/skills/generate_plan.py`
- Post-process wrapper around `plan_task.run()`: call → read written file → prepend `## Reasoning`
- If `ANTHROPIC_API_KEY` set and `dev_mode:false`: call `claude-haiku-4-5` to generate reasoning
- If no API key or `dev_mode:true`: return plan as-is (no error)
- Skip items that already have a plan in `vault/Plans/`
- Return `{processed, claude_enriched, template_fallback, errors, skipped}`

**Acceptance**: `pytest tests/test_generate_plan.py -v` — all tests pass; SC-016 verified in mock.
**Tests (TDD)**:
- `test_calls_plan_task_run`
- `test_skips_items_with_existing_plan`
- `test_dev_mode_returns_template_plan` — no Claude call
- `test_no_api_key_returns_template_plan`
- `test_claude_enrichment_prepends_reasoning_section` — mock API; verify `## Reasoning` in file
- `test_returns_claude_enriched_true_when_api_used`
- `test_returns_template_fallback_true_in_dev_mode`

#### T12 — `src/skills/generate_linkedin_post.py`
- Self-guard (1): `skills.generate_linkedin_post.enabled` in settings.yaml
- Self-guard (2): scan `vault/Logs/` for `action:linkedin_post` in last `frequency_days` days
- Call Claude API to draft post (max 3,000 chars; includes `#AIAssisted`)
- Fallback to hardcoded template when `dev_mode:true` or no API key
- Write `vault/Plans/LINKEDIN_POST_{timestamp}.md` with `type:linkedin_post`, `risk_level:HIGH`
- Return `{processed, post_files_created, skipped_rate_limit, errors, skipped}`

**Acceptance**: `pytest tests/test_linkedin_post.py -v` — all tests pass.
**Tests (TDD)**:
- `test_skips_when_disabled`
- `test_skips_when_posted_recently` — mock log with recent linkedin_post entry
- `test_creates_post_file_when_guards_pass`
- `test_post_file_has_correct_frontmatter`
- `test_post_includes_hashtag_aiassisted`
- `test_dev_mode_uses_template` — no Claude call
- `test_returns_skipped_1_when_cadence_guard`

#### T13 — `src/skills/weekly_briefing.py`
- Self-guard: Monday check + briefing-exists check
- Aggregate audit logs from `vault/Logs/` (previous Monday–Sunday)
- Parse Markdown log entries with regex; aggregate by channel, action type, outcome
- Generate briefing with Claude (if API key) or template text
- Output: `vault/Briefings/BRIEFING_{YYYY-MM-DD}.md`
- Return `{processed, briefing_file, week_start, errors, skipped}`

**Acceptance**: `pytest tests/test_weekly_briefing.py -v` — all tests pass; SC-017 verified.
**Tests (TDD)**:
- `test_skips_on_non_monday` — Tuesday → `{skipped:1, briefing_file:None}`
- `test_skips_if_briefing_exists` — file already exists → `{skipped:1}`
- `test_creates_briefing_on_monday`
- `test_briefing_has_required_sections` — grep for all 9 section headers
- `test_aggregates_items_by_channel`
- `test_template_fallback_when_no_api_key`

#### T14 — `src/skills/install_schedule.py` + `uninstall_schedule.py`
- Platform detection via `sys.platform`
- Windows: `schtasks.exe` for `FTE-Orchestrator` (ONSTART) + `FTE-WeeklyBriefing` (Mon 08:00)
- POSIX: crontab edit (read → strip FTE lines → append → write)
- Idempotent: delete+recreate (Windows); strip+append (POSIX)
- Return `{processed, platform, tasks_created, tasks_updated, errors, skipped}`
- `uninstall_schedule.py`: removes all FTE tasks/crontab entries

**Acceptance**: SC-018 (idempotency test) verified; `pytest tests/test_install_schedule.py -v` passes.
**Tests (TDD)**:
- `test_windows_creates_tasks` — mock subprocess; verify schtasks called
- `test_windows_idempotent` — run twice; no duplicates
- `test_posix_adds_crontab_entries` — mock crontab; verify 2 FTE entries
- `test_posix_idempotent` — run twice; still 2 entries
- `test_uninstall_removes_tasks`

**Phase 5 exit gate**: T09–T14 tests pass. All 385 Bronze tests pass.

---

### Phase 6: Orchestrator Wiring + Execute Plan + Dashboard Extensions

**Goal**: Wire all new components into the running system. Minimal changes to existing files.

**Tasks**:

#### T15 — `src/skills/execute_plan.py` extension
- Prepend queue drain at entry (FR-D06):
  - Load `vault/state/queue.json`
  - For each entry: re-check rate limiter; if reset → re-attempt; if still limited → MEDIUM audit
  - Purge entries older than 24h
- Append quarantine move after fail_count increment (FR-J04):
  - When `fail_count >= 3`: move item from `vault/Needs_Action/` to `vault/Quarantine/`; MEDIUM audit

**Acceptance**: `pytest tests/test_execute_plan.py -v` — all Bronze tests pass + new Silver tests.
**New tests (TDD)**:
- `test_drains_queue_at_start`
- `test_queue_entry_reattempted_when_limit_reset`
- `test_queue_entry_left_when_still_limited`
- `test_queue_entry_purged_after_24h`
- `test_item_moved_to_quarantine_after_3_failures`
- `test_quarantine_audit_entry_written`

#### T16 — `src/skills/update_dashboard.py` extension
- Add per-watcher health rows: `last_poll`, `items_this_cycle`, `status` (OK/ERROR)
- Add Quarantine folder count row
- Add Briefings folder count row
- Accept `watcher_health: dict` parameter (passed from orchestrator)

**Acceptance**: `pytest tests/test_dashboard.py -v` — all Bronze tests pass + new rows verified.
**New tests (TDD)**:
- `test_dashboard_shows_watcher_health_rows`
- `test_dashboard_shows_quarantine_count`
- `test_dashboard_shows_briefings_count`

#### T17 — `src/orchestrator.py` extensions
- Replace single-watcher setup with 4 daemon threads (`_init_watchers()`)
- Add `_watcher_health` shared dict + `_health_lock` for thread-safe health tracking
- Add `detect_lead.run()` to `_scan_cycle()` (after `triage_inbox`, before `generate_plan`)
- Replace `plan_task.run()` with `generate_plan.run()` in `_scan_cycle()`
- Add `generate_linkedin_post.run()` to `_scan_cycle()` (self-guarded; always called)
- Add `weekly_briefing.run()` to `_scan_cycle()` (self-guarded; always called)
- Add new vault folders to `_ensure_vault_structure()`
- Pass `_watcher_health` to `update_dashboard.run()`

**Acceptance**: SC-012 (4 concurrent watcher threads logged). All Bronze E2E tests pass.
**Tests (TDD)**:
- `test_four_watcher_threads_started` — verify 4 daemon threads launched
- `test_health_dict_updated_after_poll`
- `test_detect_lead_called_in_scan_cycle`
- `test_generate_plan_replaces_plan_task`
- `test_self_guarded_skills_called_every_cycle`

**Phase 6 exit gate**: SC-012 verified (4 threads logged). All 385 Bronze tests + all Silver tests pass. `pytest tests/ --cov=src --cov-fail-under=70` passes.

---

### Phase 7: Config, Vault, and End-to-End Tests

**Goal**: Apply all config changes; create vault files; verify E2E; certify all success criteria.

**Tasks**:

#### T18 — Config extensions
- `config/settings.yaml`: add all Silver stanzas (watchers, skills, rate_limits, idempotency)
  - `scan_interval: 120` (changed from 30)
  - `approval.expiry_hours: 48` (changed from 24)
  - All new stanza blocks from spec Section 7
- `requirements.txt`: add all Silver packages (google-auth, google-auth-oauthlib,
  google-api-python-client, requests, anthropic, mcp, playwright)
- `.env.example`: add all Silver env var keys (GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET,
  ANTHROPIC_API_KEY, ANTHROPIC_PLAN_MODEL, DRY_RUN)

**Acceptance**: `python -c "import yaml; yaml.safe_load(open('config/settings.yaml'))"` — no errors.

#### T19 — Vault structure additions and Bronze gap fixes

New files to create:
- `vault/Briefings/.gitkeep`
- `vault/Quarantine/.gitkeep`
- `vault/Templates/linkedin_post_prompt.md` (default prompt text)
- `vault/Opt_Out_List.md` (empty list with header comment)
- `vault/Watch/gmail_mock/sample_email.json` (flat mock schema: `{id, subject, from, to, body, received_at, thread_id}`)
- `vault/Watch/whatsapp_mock/sample_message.json` (already exists — verify schema `{MessageSid, From, Body, To}`)
- `vault/Watch/linkedin_mock/sample_post.json` (engagement mock: `{post_url, reactions, comments, post_preview}`)

Files to replace/update (Bronze gap fixes, Documents.md template compliance):
- `vault/Business_Goals.md` — REPLACE Bronze placeholder with Documents.md template:
  ```
  ---
  last_updated: <YYYY-MM-DD>
  review_frequency: weekly
  ---
  ## Q1 2026 Objectives
  ### Revenue Target
  - Monthly goal: $10,000
  - Current MTD: $0 (update manually)
  ### Key Metrics to Track
  | Metric | Target | Alert Threshold |
  |--------|--------|-----------------|
  | Client response time | < 24 hours | > 48 hours |
  | Invoice payment rate | > 90% | < 80% |
  | Software costs | < $500/month | > $600/month |
  ### Active Projects
  1. [Project Name] — Due [Date] — Budget $[Amount]
  ### Subscription Audit Rules
  Flag for review if: No login in 30 days / Cost increased > 20% / Duplicate functionality
  ```
- `vault/Dashboard.md` — ADD bank balance placeholder section after page title:
  ```markdown
  ## 💰 Bank Balance
  | Account | Balance | Last Updated |
  |---------|---------|--------------|
  | Business Account | Connecting... | — |
  ```
  RENAME section: `## 📝 Recent Actions` → `## 📝 Recent Activity` (Documents.md §5 naming).
- `vault/Company_Handbook.md` — ADD `review_frequency: weekly` to YAML frontmatter.

**Acceptance**: All files committed; `orchestrator._ensure_vault_structure()` creates all new folders without error. `vault/Business_Goals.md` grep shows `review_frequency: weekly` + all 5 required sections. `vault/Dashboard.md` contains `Bank Balance` section + `Recent Activity` heading.

#### T20 — End-to-end Silver test (`tests/test_e2e_silver.py`)
SC-013 pipeline: file drop → triage → detect_lead → generate_plan (template) → execute_plan →
quarantine on 3 failures. All steps verified in mock mode (no live credentials).

**Tests**:
- `test_lead_detection_pipeline` — SC-013
- `test_quarantine_after_3_failures` — SC-019
- `test_queue_drain_pipeline` — rate-limited action queued → drained on next cycle
- `test_dry_run_full_pipeline` — all 4 watchers in dry-run → items in Inbox → triaged

**Acceptance**: `pytest tests/test_e2e_silver.py -v` — all tests pass.

#### T21 — Final coverage and certification
```bash
# Verify Bronze invariant
python -m pytest tests/ --ignore=tests/test_e2e_silver.py -k "not silver" -v

# Verify all tests pass
python -m pytest tests/ -v --tb=short

# Verify coverage
python -m pytest tests/ --cov=src --cov-report=term-missing --cov-fail-under=70
```

**Acceptance**: SC-020 (all tests pass; ≥70% coverage). All SC-010 through SC-019 verified.

---

## Dependency Order

```
Phase 1 (T01–T03: core safety infra)
    │
    ├─→ Phase 2 (T04–T06: base_watcher ext + Gmail watcher)
    │       │
    │       ├─→ Phase 3 (T07: LinkedIn watcher)
    │       │
    │       └─→ Phase 4 (T08: action_executor ext)
    │               │
    │               └─→ Phase 5 (T09–T14: new skills)
    │                       │
    │                       └─→ Phase 6 (T15–T17: orchestrator wiring)
    │                               │
    │                               └─→ Phase 7 (T18–T21: config + E2E + cert)
    └─────────────────────────────────────────────────────────────────────────┘
```

Phase 2 and Phase 3 can begin as soon as Phase 1 is complete.
Phase 4 (action_executor) requires Phase 1 (rate_limiter, idempotency, opt_out).
Phase 5 (skills) requires Phase 4 (action_executor) and Phase 1 (core).
Phase 6 (wiring) requires all of Phase 5 to be importable.
Phase 7 (E2E) requires Phase 6 (orchestrator) to be complete.

---

## TDD Mandate

Every implementation task follows Red → Green → Refactor:

1. **Red**: Write failing test(s) for the function signature. `pytest` shows expected failures.
2. **Green**: Implement minimum code to pass tests. No extra features.
3. **Refactor**: Clean up code while tests stay green.

**Bronze invariant check** (run before each commit):
```bash
python -m pytest tests/test_vault.py tests/test_frontmatter.py tests/test_approval.py \
  tests/test_audit_logger.py tests/test_triage.py tests/test_handbook.py \
  tests/test_execute_plan.py tests/test_plan_task.py tests/test_action_executor.py \
  tests/test_dashboard.py tests/test_e2e.py tests/test_watcher.py -v
```

---

## Risk Mitigations

**Risk 1**: Gmail OAuth2 setup complexity blocks development
**Mitigation**: All Gmail tests run in mock mode (`DRY_RUN=true`). Real OAuth tested only in
manual Silver certification step (SC-014). OAuth failure returns `[]`, not a crash.

**Risk 2**: Playwright LinkedIn selector changes break watcher
**Mitigation**: All Playwright calls wrapped in try/except → return `[]` on exception. Tests
use mocked Playwright (no real browser). SC-015 is manual certification only.

**Risk 3**: MCP Python SDK `asyncio.run()` conflicts with test event loop
**Mitigation**: Use `anyio` (already a transitive dep) for test loop isolation. Action executor
wraps async MCP call in `asyncio.run()` with loop creation. Tests mock the entire MCP client.

**Risk 4**: 4 daemon threads cause race conditions in tests
**Mitigation**: Orchestrator tests mock thread starts. Integration tests use single-threaded
watcher calls. `threading.Lock` protects all shared state writes.

**Risk 5**: Claude API latency (2–5s) slows scan cycle in dev
**Mitigation**: `use_claude: false` flag disables Claude enrichment without code changes.
Default model is `claude-haiku-4-5` (fastest). Tests always mock the API call.

---

## Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| MCP transport | `stdio_client` (MCP Python SDK) | email-mcp is stdio-based; no HTTP |
| Gmail token storage | `vault/.gmail_token.json` | Simpler than env var; auto-refresh built-in |
| Playwright session | `launch_persistent_context(user_data_dir)` | Survives process restarts |
| Thread model | `threading.Thread(daemon=True)` | Simple; proven in Bronze; Playwright sync_api compatible |
| Rate limiter storage | JSON in `vault/state/` | No external deps; epoch-hour windows sufficient |
| Lead cadence guard | Scan `vault/Logs/` for audit entries | Audit log is single source of truth (constitution S10) |
| LinkedIn post cadence | `frequency_days` (not max_posts_per_day) | Eliminates daily-vs-interval ambiguity |
| Claude enrichment | Post-process (wrap plan_task) | plan_task.py stays unchanged; Bronze tests unaffected |

---

## Files Created / Modified

### New Files
| File | Phase |
|------|-------|
| `src/core/rate_limiter.py` | P1/T01 |
| `src/core/idempotency.py` | P1/T02 |
| `src/core/opt_out.py` | P1/T03 |
| `src/watchers/gmail_auth.py` | P2/T05 |
| `src/watchers/gmail_watcher.py` | P2/T06 |
| `src/watchers/linkedin_watcher.py` | P3/T07 |
| `src/skills/detect_lead.py` | P5/T10 |
| `src/skills/generate_plan.py` | P5/T11 |
| `src/skills/generate_linkedin_post.py` | P5/T12 |
| `src/skills/weekly_briefing.py` | P5/T13 |
| `src/skills/install_schedule.py` | P5/T14 |
| `src/skills/uninstall_schedule.py` | P5/T14 |
| `tests/test_rate_limiter.py` | P1/T01 |
| `tests/test_idempotency.py` | P1/T02 |
| `tests/test_opt_out.py` | P1/T03 |
| `tests/test_gmail_watcher.py` | P2/T06 |
| `tests/test_linkedin_watcher.py` | P3/T07 |
| `tests/test_detect_lead.py` | P5/T10 |
| `tests/test_generate_plan.py` | P5/T11 |
| `tests/test_linkedin_post.py` | P5/T12 |
| `tests/test_weekly_briefing.py` | P5/T13 |
| `tests/test_install_schedule.py` | P5/T14 |
| `tests/test_e2e_silver.py` | P7/T20 |
| `vault/Briefings/.gitkeep` | P7/T19 |
| `vault/Quarantine/.gitkeep` | P7/T19 |
| `vault/Templates/linkedin_post_prompt.md` | P7/T19 |
| `vault/Business_Goals.md` | P7/T19 |
| `vault/Opt_Out_List.md` | P7/T19 |
| `vault/Watch/gmail_mock/sample_email.json` | P7/T19 |
| `vault/Watch/linkedin_mock/sample_post.json` | P7/T19 |

### Modified Files (additive only)
| File | Phase | Change |
|------|-------|--------|
| `vault/Business_Goals.md` | P7/T19 | Replace Bronze placeholder with Documents.md full template (Bronze gap fix) |
| `vault/Dashboard.md` | P7/T19 | Add bank balance section; rename "Recent Actions" → "Recent Activity" (Bronze gap fix) |
| `vault/Company_Handbook.md` | P7/T19 | Add `review_frequency: weekly` to YAML frontmatter (Bronze gap fix) |
| `src/watchers/base_watcher.py` | P2/T04 | `dry_run` property + `_load_mock_items()` |
| `src/actions/action_executor.py` | P4/T08 | Real email-mcp + post_social + safety checks |
| `src/skills/plan_task.py` | P5/T09 | 3 new PLAN_TEMPLATES entries |
| `src/skills/execute_plan.py` | P6/T15 | Queue drain (prepend) + quarantine (append) |
| `src/skills/update_dashboard.py` | P6/T16 | Watcher health rows + quarantine/briefings counts |
| `src/orchestrator.py` | P6/T17 | 4 daemon threads + scan cycle additions |
| `config/settings.yaml` | P7/T18 | All Silver stanzas |
| `requirements.txt` | P7/T18 | 7 new packages |
| `.env.example` | P7/T18 | Silver env vars |

### Existing Bronze Files — Unchanged
| File |
|------|
| `src/core/vault.py` |
| `src/core/frontmatter.py` |
| `src/core/approval.py` |
| `src/core/audit_logger.py` |
| `src/skills/triage_inbox.py` |
| `src/skills/check_handbook.py` |
| `src/watchers/filesystem_watcher.py` |

---

## Success Criteria Mapping

| SC | Phase | Task | Verification Method |
|----|-------|------|---------------------|
| SC-010 | P2 | T06 | `pytest tests/test_gmail_watcher.py` |
| SC-011 | — | — | Already done (whatsapp_watcher.py + 31 tests) |
| SC-012 | P6 | T17 | Orchestrator logs show 4 watcher thread names |
| SC-013 | P5+P6 | T10+T20 | `pytest tests/test_e2e_silver.py::test_lead_detection_pipeline` |
| SC-014 | P4 | T08 | Manual real-mode test (mock acceptable for CI) |
| SC-015 | P5 | T12 | Manual real-mode test (mock acceptable for CI) |
| SC-016 | P5 | T11 | `pytest tests/test_generate_plan.py` |
| SC-017 | P5 | T13 | `pytest tests/test_weekly_briefing.py` |
| SC-018 | P5 | T14 | `pytest tests/test_install_schedule.py` |
| SC-019 | P6 | T15+T20 | `pytest tests/test_e2e_silver.py::test_quarantine_after_3_failures` |
| SC-020 | P7 | T21 | `pytest tests/ --cov=src --cov-fail-under=70` |

---

## Constitution Compliance Gates

Before closing Silver Tier:

- [X] `[SILVER §2.2.1]` Two or more concurrent watchers verified (SC-012)
- [X] `[SILVER §2.2.2]` 4-tier HITL model active for all new action types
- [X] `[SILVER §2.2.3]` email-mcp MCP server wired and tested
- [X] `[SILVER §2.2.4]` `generate_plan.py` creates Plan.md with reasoning loop
- [X] `[SILVER §2.2.5]` `install_schedule.py` registers OS-level tasks
- [X] `[SILVER §2.2.6]` LinkedIn post generation with HITL approval gate
- [X] `[SILVER §2.2.7]` All AI implemented as Agent Skills (no ad-hoc AI)
- [X] `[BRONZE §2.1]` All 385 Bronze tests still passing (531 total pass)
- [X] `[SILVER §2.2]` ≥70% line coverage on `src/` (73.36% achieved)
- [X] `[S8]` No secrets hardcoded; all in `.env` with `.env.example` documentation
- [X] `[S10]` All actions logged in `vault/Logs/` with appropriate severity
- [X] `[S13]` `#AIAssisted` on all LinkedIn posts; AI disclosure footer on all emails
