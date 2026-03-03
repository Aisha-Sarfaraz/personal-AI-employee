---
id: "0005"
title: Gold Tier Tasks Generation
stage: tasks
date: 2026-02-25
surface: agent
model: claude-sonnet-4-6
feature: 003-gold-tier
branch: 003-gold-tier
user: USER-PC
command: /sp.tasks
labels: ["gold-tier","tasks","tdd","odoo","meta-api","twitter","mcp","ralph-loop","watchdog"]
links:
  spec: specs/003-gold-tier/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - specs/003-gold-tier/tasks.md
tests:
  - tests/unit/test_retry_handler.py (T011 — 8 tests)
  - tests/unit/test_audit_logger_gold.py (T013 — 10 tests)
  - tests/unit/test_odoo_mcp_client.py (T015 — 14 tests)
  - tests/unit/test_odoo_mcp_server.py (T017 — 6 async tests)
  - tests/unit/test_finance_watcher.py (T019 — 15 tests)
  - tests/unit/test_generate_invoice.py (T024 — 8 tests)
  - tests/unit/test_accounting_audit.py (T027 — 8 tests)
  - tests/unit/test_weekly_briefing_gold.py (T029 — 10 tests)
  - tests/unit/test_facebook_watcher.py (T035 — 8 tests)
  - tests/unit/test_post_facebook.py (T037 — 10 tests)
  - tests/unit/test_twitter_watcher.py (T040 — 8 tests)
  - tests/unit/test_post_twitter.py (T042 — 9 tests)
  - tests/unit/test_watchdog.py (T045 — 8 tests)
  - tests/unit/test_ralph_loop.py (T048 — 8 tests)
  - tests/unit/test_stop_hook.py (T050 — 6 tests)
  - tests/unit/test_install_schedule_gold.py (T052 — 3 tests)
  - tests/integration/test_sc021_finance_mock_ingestion.py
  - tests/integration/test_sc022_csv_fallback.py
  - tests/integration/test_sc023_invoice_approval_flow.py
  - tests/integration/test_sc024_facebook_post_approval.py
  - tests/integration/test_sc025_tweet_approval.py
  - tests/integration/test_sc026_retry_handler.py
  - tests/integration/test_sc027_watchdog_restart.py
  - tests/integration/test_sc028_ceo_briefing_with_finance.py
  - tests/integration/test_sc029_ralph_loop_done.py
  - tests/integration/test_sc030_audit_log_schema.py
  - tests/integration/test_sc031_audit_backward_compat.py
  - tests/integration/test_sc032_month_rollover.py
  - tests/integration/test_orchestrator_gold.py
  - tests/integration/test_sc021_to_sc032_full_suite.py
---

## Prompt

/sp.tasks

## Response snapshot

Generated `specs/003-gold-tier/tasks.md` — 60 atomic TDD tasks across 12 phases covering all 9 user stories (US1–US9) from spec.md.

**Structure**:
- Phase 1 (Setup, T001–T010): vault folders, mock fixtures, docker-compose, config YAMLs, .env
- Phase 2 (Foundational, T011–T018): `retry_handler.py` (RED+GREEN), `audit_logger.py` patch (RED+GREEN), `OdooMCPClient` (RED+GREEN), `odoo-mcp` MCP server (RED+GREEN)
- Phase 3 (US1 Finance Transactions, T019–T023): `finance_watcher.py` full implementation + SC-021/SC-022/SC-032
- Phase 4 (US2 Invoice Creation, T024–T026): `generate_invoice.py` + SC-023
- Phase 5 (US7 CEO Briefing, T027–T031): `accounting_audit.py` + `weekly_briefing.py` patch + SC-028
- Phase 6 (US5 Error Recovery, T032): SC-026 integration
- Phase 7 (US9 Audit Schema, T033–T034): SC-030 + SC-031 integration
- Phase 8 (US3 Facebook+Instagram, T035–T039): `facebook_watcher.py` + `post_facebook.py` + SC-024
- Phase 9 (US4 Twitter, T040–T044): `twitter_watcher.py` + `post_twitter.py` + SC-025
- Phase 10 (US6 Watchdog, T045–T047): `watchdog.py` + SC-027
- Phase 11 (US8 Ralph Wiggum, T048–T054): `ralph_loop.py` + `stop_hook.py` + `install_schedule.py` patch + SC-029
- Phase 12 (Polish+E2E, T055–T060): orchestrator patch, full SC sweep, coverage check, security scan

**Key decisions**:
- TDD mandate: every implementation task preceded by RED test task
- [P] marks parallelizable tasks (Phases 8-11 can run simultaneously)
- MVP = Phases 1+2+3 (US1 Finance Transactions)
- P1 stories (US1, US2, US7, US5, US9) complete before P2 stories begin
- SC-021 through SC-032 all mapped to specific task numbers

## Outcome

- ✅ Impact: 60 atomic, immediately executable TDD tasks covering all 9 Gold Tier user stories; SC-021–SC-032 acceptance criteria each mapped to specific integration test task; MVP path identified (T001–T023)
- 🧪 Tests: ~120 new test functions across 30 test files (16 unit, 14 integration); all test tasks specify exact test function names and expected failure/pass counts
- 📁 Files: 1 file created — `specs/003-gold-tier/tasks.md`
- 🔁 Next prompts: `/sp.implement` to execute T001 through T060 sequentially; or implement MVP first: T001–T023 (Finance Transactions)
- 🧠 Reflection: Tasks organized by user story priority (P1 before P2); foundational phase enforces SDD+TDD invariants; parallel opportunities in Phases 8–11 allow fastest P2 delivery if needed; each task has exact file paths and test counts for autonomous execution

## Evaluation notes (flywheel)

- Failure modes observed: None — tasks.md generated cleanly from plan.md + spec.md + contracts/
- Graders run and results (PASS/FAIL): N/A (tasks stage)
- Prompt variant (if applicable): N/A
- Next experiment (smallest change to try): Run T001–T010 (Setup phase) to validate vault structure; then begin T011 (retry_handler RED test) as first TDD cycle
