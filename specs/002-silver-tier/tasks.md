# Tasks: Silver Tier — AI Business Assistant Upgrade

**Feature**: `002-silver-tier`
**Input**: `specs/002-silver-tier/` (spec.md, plan.md, data-model.md, contracts/, research.md)
**Branch**: `002-silver-tier`
**TDD Mandate**: Write failing test → implement minimum code → refactor. Tests MUST fail before implementation.
**Bronze Invariant**: All 385 Bronze tests must pass at every checkpoint.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no shared state dependencies)
- **[Story]**: Maps to user story from spec.md (US-01 through US-15)
- All task descriptions include exact file paths

---

## Phase 1: Setup (Vault Structure + Config + Dependencies)

**Purpose**: Create all new vault folders, mock files, config additions, and install dependencies.
No code yet — foundation for every other phase.

- [X] T001 Install Silver dependencies: `pip install google-auth google-auth-oauthlib google-api-python-client anthropic mcp playwright requests` and update `requirements.txt` with Silver additions from spec Section 7
- [X] T002 [P] Extend `config/settings.yaml` with Silver stanzas: watchers.gmail, watchers.whatsapp, watchers.linkedin, approval.expiry_hours=48, orchestrator.scan_interval=120, skills.detect_lead, skills.generate_linkedin_post, skills.generate_plan, skills.weekly_briefing, rate_limits, idempotency
- [X] T003 [P] Update `.env.example` with Silver env vars: GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET, ANTHROPIC_API_KEY, ANTHROPIC_PLAN_MODEL, DRY_RUN
- [X] T004 [P] Create vault folder structure: `vault/Briefings/.gitkeep`, `vault/Quarantine/.gitkeep`, `vault/Templates/linkedin_post_prompt.md` (default prompt), `vault/Opt_Out_List.md` (empty header). REPLACE `vault/Business_Goals.md` with Documents.md template: YAML frontmatter must include `last_updated` + `review_frequency: weekly`; body must have all 5 sections — `## Q1 2026 Objectives` > `### Revenue Target` (monthly goal: $10,000 / MTD: $0 placeholder) > `### Key Metrics to Track` table (Client response time / Invoice payment rate / Software costs) > `### Active Projects` (placeholder entry) > `### Subscription Audit Rules` (3 flag conditions: no-login-30d / cost-increase-20% / duplicate-tool)
- [X] T005 [P] Create mock data files: `vault/Watch/gmail_mock/sample_email.json` (flat schema), `vault/Watch/whatsapp_mock/sample_message.json` (verify exists), `vault/Watch/linkedin_mock/sample_post.json`
- [X] T006 Run `playwright install chromium` to install browser binary; verify with `python -c "from playwright.sync_api import sync_playwright; print('OK')"`

**Checkpoint**: `python -m pytest tests/ -v` → 385/385 Bronze tests pass. `python -c "import yaml; yaml.safe_load(open('config/settings.yaml'))"` → no errors.

---

## Phase 2: Foundational (Core Safety Infrastructure + BaseWatcher)

**Purpose**: Safety modules required by ALL Silver features. Must complete before any user story.

**⚠️ CRITICAL**: No user story implementation until this phase is complete.

### Tests — rate_limiter (write first, verify they FAIL)

- [X] T007 [P] Write `tests/test_rate_limiter.py`: `test_allows_within_limit`, `test_blocks_at_limit`, `test_resets_after_hour` (mock `time.time`), `test_different_action_types_independent`, `test_prunes_old_keys`, `test_creates_state_file_if_absent`. Run: `pytest tests/test_rate_limiter.py -v` → all FAIL (ImportError or assertion failures).

### Tests — idempotency (write first, verify they FAIL)

- [X] T008 [P] Write `tests/test_idempotency.py`: `test_generate_key_format`, `test_generate_key_deterministic`, `test_new_key_stored`, `test_existing_key_returns_cached`, `test_expired_key_treated_as_new`, `test_prunes_expired_entries`. Run: `pytest tests/test_idempotency.py -v` → all FAIL.

### Tests — opt_out (write first, verify they FAIL)

- [X] T009 [P] Write `tests/test_opt_out.py`: `test_opted_out_email_blocked`, `test_not_opted_out_allowed`, `test_case_insensitive`, `test_missing_file_returns_false`, `test_ignores_headings_and_blanks`, `test_multiple_entries`. Run: `pytest tests/test_opt_out.py -v` → all FAIL.

### Tests — BaseWatcher extension (write first, verify they FAIL)

- [X] T010 Write additional test cases in `tests/test_watcher.py` (or new `tests/test_base_watcher.py`): `test_dry_run_false_by_default`, `test_dry_run_true_from_env`, `test_load_mock_items_reads_json_files`, `test_load_mock_items_skips_malformed`, `test_load_mock_items_empty_folder`, `test_load_mock_items_missing_folder`. Run: `pytest tests/test_watcher.py -v` → new tests FAIL; existing tests pass.

### Implementation — core safety modules

- [X] T011 [P] Implement `src/core/rate_limiter.py`: `check_and_increment(vault_root, action_type, limit_per_hour) -> bool`. JSON state at `vault/state/rate_limits.json`; epoch-hour window keys; prune keys > 2h; thread-safe with `threading.Lock`. Run: `pytest tests/test_rate_limiter.py -v` → all PASS.
- [X] T012 [P] Implement `src/core/idempotency.py`: `generate_key(agent, action, details) -> str` (format: `{agent}:{action}:{sha256[:8]}:{epoch_day}`); `check_and_store(vault_root, key, result, ttl_hours) -> tuple[bool, dict|None]`; prune expired on every call; thread-safe. Run: `pytest tests/test_idempotency.py -v` → all PASS.
- [X] T013 [P] Implement `src/core/opt_out.py`: `is_opted_out(vault_root, email_address) -> bool`; parse `vault/Opt_Out_List.md`; lines starting with `- ` are entries; case-insensitive; return False if file absent. Run: `pytest tests/test_opt_out.py -v` → all PASS.

### Implementation — BaseWatcher extension

- [X] T014 Extend `src/watchers/base_watcher.py` with `dry_run: bool` property (checks `DRY_RUN` env var, case-insensitive) and `_load_mock_items(mock_folder: str) -> list[dict]` helper (reads `*.json`, skips malformed, returns `[]` if folder absent). Run: `pytest tests/test_watcher.py tests/test_whatsapp_watcher.py -v` → all PASS (existing + new tests).

**Checkpoint**: `pytest tests/test_rate_limiter.py tests/test_idempotency.py tests/test_opt_out.py tests/test_watcher.py -v` → all PASS. `pytest tests/ -v` → all 385 Bronze tests still pass.

---

## Phase 3: US-01 — Gmail Inbox Monitoring (P1) 🎯 MVP

**Goal**: Gmail messages detected every 2 minutes → appear in `vault/Inbox/` with correct item dict.
**Independent Test**: `pytest tests/test_gmail_watcher.py -v` all pass. With `DRY_RUN=true`, `vault/Watch/gmail_mock/sample_email.json` flows to `vault/Inbox/GMAIL_*.md` within one scan.

### Tests (write first, verify FAIL)

- [X] T015 [P] [US01] Write `tests/test_gmail_watcher.py`: `test_dry_run_returns_mock_items`, `test_parse_message_flat_mock_schema`, `test_parse_message_real_api_schema` (mock nested payload), `test_dedup_skips_processed_ids`, `test_marks_message_as_read`, `test_oauth_failure_returns_empty_list`, `test_token_refresh_on_expiry`, `test_uses_base_watcher_load_mock_items`. Run: `pytest tests/test_gmail_watcher.py -v` → all FAIL.

### Implementation

- [X] T016 [US01] Implement `src/watchers/gmail_auth.py`: one-time OAuth2 flow using `InstalledAppFlow`; reads `GMAIL_CLIENT_ID` + `GMAIL_CLIENT_SECRET` from `.env`; scopes: `["https://www.googleapis.com/auth/gmail.modify"]`; writes `vault/.gmail_token.json`; prints auth URL for headless environments.
- [X] T017 [US01] Implement `src/watchers/gmail_watcher.py` — `GmailWatcher(BaseWatcher)`:
  - `check_for_updates()`: dry-run path → `self._load_mock_items(gmail_mock_dir)`; live path → load `vault/.gmail_token.json` → refresh if expired → `messages.list` → `messages.get` → `_parse_message()` → mark read → dedup via state file
  - `_parse_message(raw: dict) -> dict`: detect flat mock (no `"payload"` key) vs real API; return normalized InboxItem dict (`id`, `source:gmail`, `subject`, `from_address`, `to_address`, `message_id`, `received_at`, `thread_id`, `body`, `type`, `priority`, `filename`, `tags`)
  - On OAuth failure: MEDIUM audit entry, return `[]`; max 100 Gmail API calls/hour enforced internally
  Run: `pytest tests/test_gmail_watcher.py -v` → all PASS.
- [X] T018 [US01] Verify `vault/state/gmail_watcher_state.json` created on first run; processed IDs persisted across restarts; restarting watcher does not re-process same messages.

**Checkpoint (SC-010)**: `pytest tests/test_gmail_watcher.py -v` all pass. Mock mode: `GmailWatcher.check_for_updates()` returns items from `gmail_mock/sample_email.json`. All 385 Bronze tests still pass.

---

## Phase 4: US-02 — WhatsApp Message Capture (P2) ✓ DONE

**Status**: `src/watchers/whatsapp_watcher.py` already implemented (31 tests, 416 total passing).
**Goal**: Verify `WhatsAppWatcher` uses `base_watcher._load_mock_items()` after Phase 2 extension.

- [X] T019 [US02] Verify `WhatsAppWatcher` dry-run path delegates to `self._load_mock_items()` from `BaseWatcher` (not its own re-implementation). If it has its own implementation, refactor to delegate to base class method. Run: `pytest tests/test_whatsapp_watcher.py -v` → all 31 tests pass.
- [X] T020 [US02] Verify `vault/Watch/whatsapp_mock/sample_message.json` exists and has correct schema `{MessageSid, From, Body, To}`; create if missing.

**Checkpoint (SC-011)**: `pytest tests/test_whatsapp_watcher.py -v` → 31 tests pass. WhatsApp dry-run reads from mock folder.

---

## Phase 5: US-03 / US-12 / US-13 / US-14 / US-15 — Safe External Actions (P3)

**Goal**: Real email sends via email-mcp with all safety guardrails: opt-out check, AI footer, rate limiting, idempotency keys, queue on rate-limit.
**Independent Test**: With `dev_mode=false` and mocked email-mcp: `audit_log` contains `simulated:false`; opted-out recipient produces `skipped:opted_out` entry; 21st email in same hour returns `{queued:true}`.

### Tests (write first, verify FAIL)

- [X] T021 [P] [US03] Write additional tests in `tests/test_action_executor.py`:
  - `test_send_email_appends_ai_disclosure_footer` [US14]
  - `test_send_email_skips_opted_out_recipient` [US13]
  - `test_send_email_queues_when_rate_limited` [US15]
  - `test_send_email_uses_cached_idempotency_result` [US12]
  - `test_send_email_retries_with_exponential_backoff`
  - `test_send_email_real_mode_returns_simulated_false` [US03]
  - `test_send_email_dev_mode_unchanged` (simulated:true still works) [US03]
  - `test_post_social_simulation_mode`
  - `test_post_social_queues_when_rate_limited` [US15]
  Run: `pytest tests/test_action_executor.py -v -k "new"` → new tests FAIL; existing 385 pass.

### Implementation

- [X] T022 [US15] Extend `src/actions/action_executor.py` — add `_check_rate_limit(action_type)` helper using `rate_limiter.check_and_increment()`; add `_queue_action(action_type, details, plan_id)` helper writing to `vault/state/queue.json`. No existing code paths changed.
- [X] T023 [US13] Extend `src/actions/action_executor.py` — add opt-out check in `_send_email` real path: call `opt_out.is_opted_out()`; if True: log `skipped:opted_out` MEDIUM audit entry; return `{success:False, reason:"opted_out"}`.
- [X] T024 [US14] Extend `src/actions/action_executor.py` — append AI disclosure footer `"\n\nThis message was drafted with AI assistance."` to email body before sending (real mode only; simulation unchanged).
- [X] T025 [US12] Extend `src/actions/action_executor.py` — add idempotency check before MCP call: `idempotency.check_and_store(key)`; if key exists return cached result; if new: call MCP → store result.
- [X] T026 [US03] Extend `src/actions/action_executor.py` — wire real `_send_email` handler:
  - When `dev_mode=false`: call `email-mcp` via MCP Python SDK (`mcp.ClientSession` + `stdio_client`; wrap in `asyncio.run()`)
  - Exponential backoff: 1s → 2s → 4s (3 attempts); on 3 failures increment `fail_count`
  - `simulated:false` in return dict and audit log
  - Simulation path (`dev_mode=true`) completely unchanged
  Run: `pytest tests/test_action_executor.py -v` → ALL tests pass (existing 385 + new Silver tests).
- [X] T027 [US03] Implement `post_social` action type in `src/actions/action_executor.py`:
  - Real mode (`dev_mode=false`, LinkedIn session present): rate-limit check → idempotency check → Playwright `launch_persistent_context(vault/state/linkedin_session/)` → compose + submit post → log `action:linkedin_post`; return `{success:True, simulated:False}`
  - Simulation mode: return `{success:True, simulated:True}`

**Checkpoint (SC-014 mock, SC-015 mock)**: `pytest tests/test_action_executor.py -v` → all pass. Audit log contains `simulated:false` in real-mode mock test. Opted-out email produces `skipped:opted_out`. Rate-limited action appended to `queue.json`.

---

## Phase 6: US-04 — Lead Detection (P4)

**Goal**: Items in `vault/Needs_Action/` with ≥2 lead keywords upgraded to `type:lead`, `priority:CRITICAL`, `lead_score:<int>` in-place.
**Independent Test**: Drop file with "I'm interested in your pricing" → after `detect_lead.run()`: item has `type:lead`, `priority:CRITICAL`, `lead_score >= 2`.

### Tests (write first, verify FAIL)

- [X] T028 [US04] Write `tests/test_detect_lead.py`:
  - `test_detects_lead_with_two_keywords`
  - `test_does_not_detect_lead_with_one_keyword`
  - `test_upgrades_type_to_lead`
  - `test_upgrades_priority_to_critical`
  - `test_calculates_lead_score_correctly`
  - `test_gmail_source_adds_two_points`
  - `test_skips_items_already_lead`
  - `test_returns_correct_result_dict`
  Run: `pytest tests/test_detect_lead.py -v` → all FAIL.

### Implementation

- [X] T029 [US04] Extend `src/skills/plan_task.py` — add three new entries to `PLAN_TEMPLATES` dict (additive, no existing templates modified): `lead` (4 steps: review → draft response → send_email HIGH → tag), `linkedin_post` (3 steps: review → post_social HIGH → record), `social_media_engagement` (2 steps: summarise → update tracker). Run: `pytest tests/test_plan_task.py -v` → all pass + template existence verified.
- [X] T030 [US04] Implement `src/skills/detect_lead.py`:
  - `run(vault_root: str) -> dict`: scan `vault/Needs_Action/`; skip `type:lead` items; keyword match against `settings.yaml skills.detect_lead.keywords`
  - Lead score: 1 per keyword (cap 10) + 2 if `source:gmail` + 1 if already `priority:CRITICAL`
  - On ≥2 matches: update frontmatter in-place (`type:lead`, `priority:CRITICAL`, `lead_score`)
  - Write HIGH audit entry per lead detected
  - Return `{processed, leads_detected, errors, skipped}`
  Run: `pytest tests/test_detect_lead.py -v` → all PASS.

**Checkpoint (SC-013 partial)**: `pytest tests/test_detect_lead.py tests/test_plan_task.py -v` → all pass. Lead detection verified on fixture item with 2 keywords.

---

## Phase 7: US-06 — Claude-Powered Plan Generation (P5)

**Goal**: `generate_plan.py` wraps `plan_task.py` (unchanged) and prepends `## Reasoning` section from Claude API when API key present.
**Independent Test**: With `ANTHROPIC_API_KEY` mocked: `PLAN_*.md` in `vault/Plans/` contains `## Reasoning` section. With no API key: plan generated from template without error.

### Tests (write first, verify FAIL)

- [X] T031 [US06] Write `tests/test_generate_plan.py`:
  - `test_calls_plan_task_run` (verifies plan_task is called)
  - `test_skips_items_with_existing_plan`
  - `test_dev_mode_returns_template_plan_no_claude_call`
  - `test_no_api_key_returns_template_plan`
  - `test_claude_enrichment_prepends_reasoning_section` (mock API; verify `## Reasoning` in file)
  - `test_returns_claude_enriched_true_when_api_used`
  - `test_returns_template_fallback_true_in_dev_mode`
  - `test_does_not_modify_plan_task_py` (import check)
  Run: `pytest tests/test_generate_plan.py -v` → all FAIL.

### Implementation

- [X] T032 [US06] Implement `src/skills/generate_plan.py`:
  - `run(vault_root: str) -> dict`: call `plan_task.run(vault_root)` → get plan path(s) written
  - If `ANTHROPIC_API_KEY` set and `dev_mode:false`: read PLAN_*.md → call Claude (`claude-haiku-4-5` or `ANTHROPIC_PLAN_MODEL`) → generate `## Reasoning` section → insert after YAML frontmatter block, before first `##` heading
  - If no API key or `dev_mode:true`: return plan as-is (no error; `template_fallback:true`)
  - Skip items already having plan in `vault/Plans/`
  - Return `{processed, claude_enriched, template_fallback, errors, skipped}`
  - `plan_task.py` NOT modified
  Run: `pytest tests/test_generate_plan.py -v` → all PASS.

**Checkpoint (SC-016)**: `pytest tests/test_generate_plan.py -v` → all pass. Mock API test verifies `## Reasoning` section. Template fallback works without error.

---

## Phase 8: US-05 — LinkedIn Watcher + Post Generation (P6)

**Goal**: LinkedIn engagement data polled hourly; LinkedIn posts drafted by Claude, approved via HITL, published via Playwright.
**Independent Test**: `pytest tests/test_linkedin_watcher.py tests/test_linkedin_post.py -v` → all pass. Mock mode returns `type:social_media_engagement` items. Post draft written to `vault/Plans/LINKEDIN_POST_*.md` with `#AIAssisted`.

### Tests (write first, verify FAIL)

- [X] T033 [P] [US05] Write `tests/test_linkedin_watcher.py`:
  - `test_dry_run_returns_mock_items`
  - `test_item_type_is_social_media_engagement`
  - `test_item_source_is_linkedin`
  - `test_id_is_sha256_of_post_url`
  - `test_session_expired_returns_empty_list`
  - `test_playwright_exception_returns_empty_list`
  - `test_setup_session_uses_headful_mode`
  - `test_uses_base_watcher_load_mock_items`
  Run: `pytest tests/test_linkedin_watcher.py -v` → all FAIL.
- [X] T034 [P] [US05] Write `tests/test_linkedin_post.py`:
  - `test_skips_when_disabled_in_settings`
  - `test_skips_when_posted_recently` (mock log with recent linkedin_post entry)
  - `test_creates_post_file_when_guards_pass`
  - `test_post_file_has_type_linkedin_post`
  - `test_post_file_has_risk_level_high`
  - `test_post_includes_hashtag_aiassisted`
  - `test_dev_mode_uses_template_no_claude_call`
  - `test_returns_skipped_1_when_cadence_guard_triggered`
  Run: `pytest tests/test_linkedin_post.py -v` → all FAIL.

### Implementation

- [X] T035 [US05] Implement `src/watchers/linkedin_watcher.py` — `LinkedInWatcher(BaseWatcher)`:
  - `check_for_updates()`: dry-run path → `self._load_mock_items(linkedin_mock_dir)`; live path → `launch_persistent_context(vault/state/linkedin_session/, headless=True)` → navigate to `https://www.linkedin.com/in/{username}/detail/recent-activity/` → extract 5 posts (reactions, comments, post_preview[:200], post_url, id=SHA256(post_url[:12])) → return items with `type:social_media_engagement`, `source:linkedin`, `platform:linkedin`
  - Session expiry: URL contains `/login` → LOW audit + return `[]`
  - All Playwright in try/except → LOW audit + return `[]` on exception
  - `setup_session()`: `headless=False` for manual login; persist to `vault/state/linkedin_session/`
  - Username from `settings.yaml watchers.linkedin.username`
  Run: `pytest tests/test_linkedin_watcher.py -v` → all PASS.
- [X] T036 [US05] Implement `src/skills/generate_linkedin_post.py`:
  - `run(vault_root: str) -> dict`
  - Self-guard 1: check `settings.skills.generate_linkedin_post.enabled`; return `{skipped:1}` if false
  - Self-guard 2: scan `vault/Logs/` for any audit entry with `action:linkedin_post` in last `frequency_days` days (default: 3); return `{skipped:1}` if found
  - Load prompt from `vault/Templates/linkedin_post_prompt.md` if exists; else hardcoded default
  - Read `vault/Business_Goals.md` as raw text; read last 7 days of `vault/Logs/` activity
  - Call Claude API (`ANTHROPIC_API_KEY`); draft ≤ 3,000 char post; must include `#AIAssisted`
  - Fallback to configurable template when `dev_mode:true` or no API key
  - Write `vault/Plans/LINKEDIN_POST_{timestamp}.md` with `type:linkedin_post`, `risk_level:HIGH`, `requires_approval:true`
  - Return `{processed, post_files_created, skipped_rate_limit, errors, skipped}`
  Run: `pytest tests/test_linkedin_post.py -v` → all PASS.

**Checkpoint (SC-015 mock)**: `pytest tests/test_linkedin_watcher.py tests/test_linkedin_post.py -v` → all pass. Post draft file contains `#AIAssisted`.

---

## Phase 9: US-07 — Weekly CEO Briefing (P7)

**Goal**: Every Monday, `vault/Briefings/BRIEFING_{date}.md` generated with all 9 required sections.
**Independent Test**: `python -c "from src.skills.weekly_briefing import run; import json; print(json.dumps(run('vault')))"` creates briefing with all section headers; repeated call returns `{skipped:1}`.

### Tests (write first, verify FAIL)

- [X] T037 [US07] Write `tests/test_weekly_briefing.py`:
  - `test_skips_on_non_monday`
  - `test_skips_if_briefing_already_exists`
  - `test_creates_briefing_on_monday` (mock date)
  - `test_briefing_has_all_nine_required_sections`
  - `test_aggregates_items_by_channel`
  - `test_returns_correct_result_dict`
  - `test_template_fallback_when_no_api_key`
  - `test_does_not_reprocess_vault_items` (reads Logs/ only)
  Run: `pytest tests/test_weekly_briefing.py -v` → all FAIL.

### Implementation

- [X] T038 [US07] Implement `src/skills/weekly_briefing.py`:
  - `run(vault_root: str) -> dict`
  - Self-guard: check `datetime.now().weekday() == 0` (Monday) AND `BRIEFING_{this-monday}.md` does not exist; return `{processed:0, briefing_file:None, week_start:None, errors:[], skipped:1}` if either fails
  - Read `vault/Logs/` for previous Monday–Sunday; parse Markdown audit entries via regex `r"\*\*(\w+)\*\*: (.+)"`
  - Aggregate by channel, action type, outcome
  - Generate all 9 sections (see spec FR-G02): date range, items by channel, leads, emails sent, LinkedIn posts, plans summary, approvals, quarantine, next-week recommendations
  - If `ANTHROPIC_API_KEY`: Claude drafts next-week recommendations; else use template text
  - Write `vault/Briefings/BRIEFING_{YYYY-MM-DD}.md`; LOW audit entry
  - Return `{processed, briefing_file, week_start, errors, skipped}`
  Run: `pytest tests/test_weekly_briefing.py -v` → all PASS.

**Checkpoint (SC-017)**: `pytest tests/test_weekly_briefing.py -v` → all pass. Briefing file created with all 9 section headers verified.

---

## Phase 10: US-08 — Scheduling Setup (P8)

**Goal**: `install_schedule.py` registers OS-level tasks idempotently; `uninstall_schedule.py` removes them cleanly.
**Independent Test**: On Windows, `schtasks /query /tn FTE-Orchestrator` shows 1 task after 2 installer runs. On POSIX, `crontab -l | grep FTE` shows exactly 2 entries after 2 installer runs.

### Tests (write first, verify FAIL)

- [X] T039 [US08] Write `tests/test_install_schedule.py`:
  - `test_windows_creates_orchestrator_task` (mock subprocess)
  - `test_windows_creates_briefing_task`
  - `test_windows_idempotent_no_duplicates`
  - `test_posix_adds_two_crontab_entries` (mock subprocess for crontab)
  - `test_posix_idempotent_still_two_entries`
  - `test_uninstall_removes_all_fte_tasks`
  - `test_returns_correct_platform_in_result`
  Run: `pytest tests/test_install_schedule.py -v` → all FAIL.

### Implementation

- [X] T040 [US08] Implement `src/skills/install_schedule.py`:
  - Detect platform via `sys.platform`
  - Windows: `schtasks /delete /tn FTE-Orchestrator /f` then `schtasks /create` (ONSTART); same for `FTE-WeeklyBriefing` (Mon 08:00 `/sc weekly /d MON /st 08:00`)
  - POSIX: read crontab via `crontab -l`; strip all `# FTE` tagged lines; append `@reboot python orchestrator.py # FTE` and `0 8 * * 1 python weekly_briefing.py # FTE`; write via `crontab -`
  - Print confirmation; write LOW audit entry
  - Return `{processed, platform, tasks_created, tasks_updated, errors, skipped}`
- [X] T041 [US08] Implement `src/skills/uninstall_schedule.py`:
  - Windows: `schtasks /delete /tn FTE-Orchestrator /f`, `schtasks /delete /tn FTE-WeeklyBriefing /f`
  - POSIX: read crontab; remove all `# FTE` lines; write back
  - Print confirmation; write LOW audit entry
  Run: `pytest tests/test_install_schedule.py -v` → all PASS.

**Checkpoint (SC-018)**: `pytest tests/test_install_schedule.py -v` → all pass. Idempotency verified.

---

## Phase 11: US-09 / US-10 — Quarantine + Enhanced Dashboard (P9)

**Goal**: Items failing 3+ times moved to `vault/Quarantine/`; Dashboard.md shows watcher health rows, quarantine count, briefings count.
**Independent Test**: Force 3 failures on one item → item in `vault/Quarantine/` + MEDIUM audit + `Dashboard.md` shows `Quarantine | 1`.

### Tests (write first, verify FAIL)

- [X] T042 [P] [US09] Write new tests in `tests/test_execute_plan.py`:
  - `test_drains_queue_at_start_of_execution`
  - `test_queue_entry_reattempted_when_rate_limit_reset`
  - `test_queue_entry_left_when_still_limited`
  - `test_queue_entry_purged_after_24_hours`
  - `test_item_moved_to_quarantine_after_3_failures`
  - `test_quarantine_audit_entry_written_with_medium_severity`
  Run: `pytest tests/test_execute_plan.py -v` → new tests FAIL; existing tests pass.
- [X] T043 [P] [US10] Write new tests in `tests/test_dashboard.py`:
  - `test_dashboard_shows_gmail_watcher_health_row`
  - `test_dashboard_shows_whatsapp_watcher_health_row`
  - `test_dashboard_shows_linkedin_watcher_health_row`
  - `test_dashboard_shows_filesystem_watcher_health_row`
  - `test_dashboard_shows_quarantine_count`
  - `test_dashboard_shows_briefings_count`
  Run: `pytest tests/test_dashboard.py -v` → new tests FAIL; existing tests pass.

### Implementation

- [X] T044 [US09] Extend `src/skills/execute_plan.py` — prepend queue drain at function entry (FR-D06):
  - Load `vault/state/queue.json` at start
  - For each entry: re-check `rate_limiter.check_and_increment()`; if allowed → re-attempt via `action_executor` → remove from queue; if still limited → write MEDIUM audit entry (no log flood)
  - Purge entries with `queued_at` older than 24h without retry
  Core plan-execution logic untouched. Run: existing tests still pass.
- [X] T045 [US09] Extend `src/skills/execute_plan.py` — append quarantine move after `fail_count` increment (FR-J04):
  - After incrementing `fail_count` in frontmatter: check if `fail_count >= 3`
  - If yes: move file from `vault/Needs_Action/` to `vault/Quarantine/`; write MEDIUM audit entry
  - Quarantine is agent-irreversible (no auto-recovery)
  Run: `pytest tests/test_execute_plan.py -v` → ALL tests pass.
- [X] T046 [US10] Extend `src/skills/update_dashboard.py` — add watcher health section and folder counts:
  - Accept `watcher_health: dict` parameter (passed from orchestrator)
  - Render per-watcher row: `| {name} | {last_poll} | {items_this_cycle} | {status} |`
  - Add `Quarantine` folder count row (count `*.md` files in `vault/Quarantine/`)
  - Add `Briefings` folder count row (count `*.md` files in `vault/Briefings/`)
  Run: `pytest tests/test_dashboard.py -v` → ALL tests pass (existing + new).

**Checkpoint (SC-019)**: `pytest tests/test_execute_plan.py tests/test_dashboard.py -v` → all pass. Quarantine pipeline verified by fixture test.

---

## Phase 12: US-11 — Orchestrator Wiring (All Watchers Concurrent)

**Goal**: All 4 watchers run as daemon threads; `generate_plan`, `detect_lead`, `generate_linkedin_post`, `weekly_briefing` wired into scan cycle.
**Independent Test**: Orchestrator logs show 4 thread names `[watcher-gmail_watcher]`, `[watcher-whatsapp_watcher]`, `[watcher-linkedin_watcher]`, `[watcher-filesystem_watcher]`. SC-012 verified.

### Tests (write first, verify FAIL)

- [X] T047 [US11] Write new tests in `tests/test_e2e.py` (or `tests/test_orchestrator.py` if exists):
  - `test_four_watcher_daemon_threads_started` (mock watcher constructors; verify 4 threads)
  - `test_health_dict_updated_after_each_poll`
  - `test_detect_lead_called_in_scan_cycle`
  - `test_generate_plan_replaces_plan_task_in_scan_cycle`
  - `test_generate_linkedin_post_called_every_cycle`
  - `test_weekly_briefing_called_every_cycle`
  Run: → new tests FAIL; existing tests pass.

### Implementation

- [X] T048 [US11] Extend `src/orchestrator.py` — replace single-watcher setup with 4 daemon threads:
  - Add `_watcher_health: dict` + `_health_lock: threading.Lock` as instance attributes
  - Implement `_init_watchers()`: create `GmailWatcher`, `WhatsAppWatcher`, `LinkedInWatcher`, `FilesystemWatcher`; start each as `threading.Thread(daemon=True, name=f"watcher-{name}")`
  - Implement `_watcher_loop(watcher, name)`: call `watcher.check_for_updates()`; update `_watcher_health[name]` with `{last_poll, items_this_cycle, status}`; sleep `watcher.poll_interval`; on exception: update status `"ERROR"`
- [X] T049 [US11] Extend `src/orchestrator.py` — update `_scan_cycle()`:
  - Call `detect_lead.run(self.vault_root)` after `triage_inbox.run()`, before `generate_plan.run()`
  - Replace `plan_task.run()` with `generate_plan.run(self.vault_root)`
  - Call `generate_linkedin_post.run(self.vault_root)` (self-guarded)
  - Call `weekly_briefing.run(self.vault_root)` (self-guarded)
  - Pass `self._watcher_health` to `update_dashboard.run()`
- [X] T050 [US11] Extend `src/orchestrator.py` — update `_ensure_vault_structure()`:
  - Add new folders: `Briefings`, `Quarantine`, `Templates`, `Watch/gmail_mock`, `Watch/whatsapp_mock`, `Watch/linkedin_mock`
  Run: `pytest tests/test_e2e.py -v` → new orchestrator tests pass; all Bronze E2E tests pass.

**Checkpoint (SC-012)**: Start orchestrator in mock mode; logs show all 4 watcher thread names. `pytest tests/ -v` → all tests pass (385 Bronze + all Silver = ~505+).

---

## Phase 13: End-to-End Silver Tests + Certification

**Purpose**: Full SC-010 through SC-020 certification in mock/CI mode.

### Silver E2E Tests

- [X] T051 Write `tests/test_e2e_silver.py`:
  - `test_lead_detection_pipeline` (SC-013): drop file with "interested in pricing" → `detect_lead` upgrades → lead plan template → approval request for `send_email` step in `vault/Pending_Approval/`
  - `test_quarantine_after_3_failures` (SC-019): fixture forces 3 consecutive executor failures → item in `vault/Quarantine/` → MEDIUM audit → `Dashboard.md` shows `Quarantine | 1`
  - `test_queue_drain_pipeline` (SC-015 mock): rate-limited action queued → `execute_plan` drains on next call → action re-attempted
  - `test_dry_run_full_pipeline` (SC-011): `DRY_RUN=true` → all 4 watchers return mock items → items triaged → plans generated → dashboard updated
  Run: `pytest tests/test_e2e_silver.py -v` → all FAIL initially.
- [X] T052 Implement any missing integration glue to make `test_e2e_silver.py` pass. Run: `pytest tests/test_e2e_silver.py -v` → all PASS.

### Final Certification

- [X] T053 Run full Bronze invariant check: `pytest tests/test_vault.py tests/test_frontmatter.py tests/test_approval.py tests/test_audit_logger.py tests/test_triage.py tests/test_handbook.py tests/test_execute_plan.py tests/test_plan_task.py tests/test_action_executor.py tests/test_dashboard.py tests/test_e2e.py tests/test_watcher.py -v` → all 385 pass.
- [X] T054 Run complete Silver test suite: `pytest tests/ -v --tb=short` → all tests pass.
- [X] T055 [P] Run coverage check: `pytest tests/ --cov=src --cov-report=term-missing --cov-fail-under=70` → ≥ 70% line coverage on `src/` (SC-020).
- [X] T056 [P] Verify SC-012: start orchestrator with `DRY_RUN=true`; confirm log output contains all 4 thread names within 5 seconds.
- [X] T057 [P] Verify SC-017: run `python -c "from src.skills.weekly_briefing import run; import json; print(json.dumps(run('vault')))"` (on a mocked Monday); briefing file created with all 9 section headers.
- [X] T058 [P] Verify SC-018: run `python src/skills/install_schedule.py` twice; confirm no duplicate tasks; run `python src/skills/uninstall_schedule.py`; confirm tasks removed.

---

## Phase 14: Polish & Cross-Cutting Concerns

- [X] T059 [P] Update `specs/002-silver-tier/plan.md` — mark all Silver SC checkboxes as complete
- [X] T060 [P] Update `specs/002-silver-tier/quickstart.md` — add Silver setup steps (install deps, `playwright install chromium`, `gmail_auth.py`, LinkedIn `setup_session()`, `.env` configuration)
- [X] T061 Verify `vault/Business_Goals.md` matches Documents.md template exactly: (1) YAML has `review_frequency: weekly`; (2) has `## Q1 2026 Objectives` section; (3) has `### Revenue Target` with monthly goal; (4) has `### Key Metrics to Track` table with all 3 rows; (5) has `### Subscription Audit Rules` with all 3 flag conditions. Verify `vault/Templates/linkedin_post_prompt.md` has a usable default prompt.
- [X] T064 [P] Update `vault/Dashboard.md` — add `## 💰 Bank Balance` placeholder table section after the page header (Documents.md §1 specifies bank balance as required Dashboard element); rename `## 📝 Recent Actions` → `## 📝 Recent Activity` (Documents.md §5 naming convention) [Bronze gap fix]
- [X] T065 [P] Update `vault/Company_Handbook.md` — add `review_frequency: weekly` to YAML frontmatter block between `version` and `status` fields (Documents.md describes handbook as weekly-reviewed "Rules of Engagement") [Bronze gap fix]
- [X] T062 [P] Run linting/type-check on all new Silver source files: `python -m flake8 src/core/ src/watchers/gmail_watcher.py src/watchers/linkedin_watcher.py src/skills/detect_lead.py src/skills/generate_plan.py src/skills/generate_linkedin_post.py src/skills/weekly_briefing.py` → no critical errors
- [X] T063 [P] Confirm all new files are gitignored correctly: `vault/state/linkedin_session/`, `vault/state/whatsapp_session/`, `vault/.gmail_token.json`, `vault/state/*.json`; check `.gitignore`

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1 (Setup)
    ↓
Phase 2 (Foundational: rate_limiter, idempotency, opt_out, base_watcher)
    ↓ BLOCKS ALL
    ├─→ Phase 3 (US-01 Gmail) ──────────────────┐
    ├─→ Phase 4 (US-02 WhatsApp verify) ────────┤
    ├─→ Phase 5 (US-03/12/13/14/15 Actions) ────┤
    ├─→ Phase 6 (US-04 Lead Detection) ─────────┤
    ├─→ Phase 7 (US-06 Claude Planning) ─────────┤
    ├─→ Phase 8 (US-05 LinkedIn Posts) ─────────┤
    ├─→ Phase 9 (US-07 Briefing) ───────────────┤
    ├─→ Phase 10 (US-08 Scheduling) ────────────┤
    └─→ Phase 11 (US-09/10 Quarantine/Dashboard)┘
            ↓
    Phase 12 (Orchestrator Wiring — all skills must be importable)
            ↓
    Phase 13 (E2E Tests + Certification)
            ↓
    Phase 14 (Polish)
```

### User Story Dependencies

| User Story | Depends On | Can Parallel With |
|-----------|-----------|------------------|
| US-01 Gmail | Phase 2 | US-02, US-04, US-06, US-07, US-08 |
| US-02 WhatsApp | Phase 2 | US-01, US-04 |
| US-03 Email Sends | Phase 2 (rate_limiter, idempotency, opt_out) | US-04, US-06 |
| US-04 Lead Detection | Phase 2 | US-01, US-03, US-06 |
| US-05 LinkedIn Posts | Phase 2 (rate_limiter) | US-07, US-08 |
| US-06 Claude Planning | Phase 2; plan_task.py (T029) | US-04, US-05 |
| US-07 Weekly Briefing | Phase 2 | US-08, US-09 |
| US-08 Scheduling | Phase 2 | US-07, US-09 |
| US-09 Quarantine | Phase 2 | US-10 |
| US-10 Dashboard | Phase 2; US-01,02,05 watchers | US-09 |
| US-11 Dry-Run | Phase 2 (base_watcher) | All others |
| US-12/13/14/15 | Phase 2 | US-01, US-04 |

---

## Parallel Execution Examples

### Phase 2 (all tasks can run in parallel — different files)

```bash
# Simultaneously:
Task T007 — Write tests/test_rate_limiter.py
Task T008 — Write tests/test_idempotency.py
Task T009 — Write tests/test_opt_out.py
Task T010 — Write tests/test_watcher.py extensions
# Then:
Task T011 — Implement src/core/rate_limiter.py
Task T012 — Implement src/core/idempotency.py
Task T013 — Implement src/core/opt_out.py
Task T014 — Extend src/watchers/base_watcher.py
```

### After Phase 2 completes — parallel user story tracks

```bash
# Track A:
Task T015, T016, T017, T018 (US-01 Gmail)

# Track B (simultaneously):
Task T019, T020 (US-02 WhatsApp verify)

# Track C (simultaneously):
Task T021, T022, T023, T024, T025, T026, T027 (US-03+ Actions)
```

### Phase 8 (LinkedIn watcher + post generator — parallel tests)

```bash
Task T033 — Write tests/test_linkedin_watcher.py
Task T034 — Write tests/test_linkedin_post.py
# (both can be written simultaneously)
```

---

## Implementation Strategy

### MVP Scope (Phases 1–3)

1. Phase 1: Setup + dependencies
2. Phase 2: Core safety infra + base_watcher extension
3. Phase 3: Gmail watcher (US-01)
4. **STOP and VALIDATE**: `pytest tests/test_gmail_watcher.py -v` → all pass; mock email → `vault/Inbox/`

### Incremental Delivery Order

1. Setup + Foundational → Safety infrastructure ready
2. US-01 (Gmail) → First new perception channel working
3. US-03/12/13/14/15 (Safe Actions) → Real email sends wired with all guardrails
4. US-04 (Lead Detection) → Lead pipeline complete
5. US-06 (Claude Planning) → AI reasoning loop active
6. US-05 (LinkedIn Posts) → Full LinkedIn sales funnel working
7. US-07/08 (Briefing + Scheduling) → Autonomous operation ready
8. US-09/10 (Quarantine + Dashboard) → Safety net + observability complete
9. Orchestrator wiring → Full system integrated
10. E2E + Certification → Silver Tier certified

---

## Task Count Summary

| Phase | Story | Tasks | Notes |
|-------|-------|-------|-------|
| Phase 1 Setup | — | 6 | T001–T006 |
| Phase 2 Foundational | — | 8 | T007–T014 |
| Phase 3 | US-01 | 4 | T015–T018 |
| Phase 4 | US-02 | 2 | T019–T020 |
| Phase 5 | US-03/12/13/14/15 | 7 | T021–T027 |
| Phase 6 | US-04 | 3 | T028–T030 |
| Phase 7 | US-06 | 2 | T031–T032 |
| Phase 8 | US-05 | 4 | T033–T036 |
| Phase 9 | US-07 | 2 | T037–T038 |
| Phase 10 | US-08 | 3 | T039–T041 |
| Phase 11 | US-09/10 | 5 | T042–T046 |
| Phase 12 | US-11 | 4 | T047–T050 |
| Phase 13 E2E | — | 8 | T051–T058 |
| Phase 14 Polish | — | 7 | T059–T065 (incl. 2 Bronze gap fixes) |
| **TOTAL** | | **65** | |

**Parallel opportunities**: 24 tasks marked [P] (38%)
**TDD tasks**: Every Phase 2–12 user story phase has test tasks (write-fail first)
**MVP**: Phases 1–3 (T001–T018) = complete Gmail monitoring with dry-run
