---
id: "0008"
title: Gold Tier Phases 8-11 P2 Implementation
stage: green
date: 2026-02-25
surface: agent
model: claude-sonnet-4-6
feature: 003-gold-tier
branch: 003-gold-tier
user: USER
command: implement Gold Tier P2 user stories Phases 8-11
labels: ["gold-tier", "facebook-watcher", "twitter-watcher", "watchdog", "ralph-loop", "social-media", "tdd", "green"]
links:
  spec: specs/003-gold-tier/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - src/watchers/facebook_watcher.py
  - src/watchers/twitter_watcher.py
  - src/watchers/watchdog.py
  - src/skills/post_facebook.py
  - src/skills/post_twitter.py
  - src/core/ralph_loop.py
  - hooks/__init__.py
  - hooks/stop_hook.py
  - tests/test_facebook_watcher.py
  - tests/test_post_facebook.py
  - tests/test_sc024_facebook_post_approval.py
  - tests/test_twitter_watcher.py
  - tests/test_post_twitter.py
  - tests/test_sc025_tweet_approval.py
  - tests/test_watchdog.py
  - tests/test_sc027_watchdog_restart.py
  - tests/test_ralph_loop.py
  - tests/test_stop_hook.py
  - tests/test_install_schedule_gold.py
  - tests/test_sc029_ralph_loop_done.py
tests:
  - tests/test_facebook_watcher.py (8 tests — PASS)
  - tests/test_post_facebook.py (10 tests — PASS)
  - tests/test_sc024_facebook_post_approval.py (3 tests — PASS)
  - tests/test_twitter_watcher.py (8 tests — PASS)
  - tests/test_post_twitter.py (9 tests — PASS)
  - tests/test_sc025_tweet_approval.py (3 tests — PASS)
  - tests/test_watchdog.py (8 tests — PASS)
  - tests/test_sc027_watchdog_restart.py (2 tests — PASS)
  - tests/test_ralph_loop.py (8 tests — PASS)
  - tests/test_stop_hook.py (6 tests — PASS)
  - tests/test_install_schedule_gold.py (3 tests — PASS)
  - tests/test_sc029_ralph_loop_done.py (3 tests — PASS)
---

## Prompt

You are implementing Gold Tier P2 user stories for an AI business assistant.
Working directory: D:\gemini-cli\practice\hacathons\fte-employe

Your job is to implement Phases 8, 9, 10, and 11 from tasks.md:
- Phase 8 (US3): Facebook + Instagram (T035-T039)
- Phase 9 (US4): Twitter/X (T040-T044)
- Phase 10 (US6): Watchdog (T045-T047)
- Phase 11 (US8): Ralph Wiggum (T048-T054)

[Full implementation task for all phases 8-11 with TDD mandate]

## Response snapshot

Implemented all 4 phases (T035-T054) following TDD:

**Phase 8 — Facebook + Instagram (T035-T039):**
- FacebookWatcher extends BaseWatcher, reads facebook_mock in dev_mode, POLL_INTERVAL_S=3600
- _fetch_live uses requests.get to Meta Graph API v20.0 with @with_retry
- AUTH errors (401/403) set _paused=True
- create_action_file writes vault/Inbox/FB_ENGAGEMENT_{id}_{ts}.md with type: social_media_engagement, source: facebook
- post_facebook.py guards on facebook.enabled + frequency_days; drafts with Claude or template; writes Pending_Approval/FB_POST_{ts}.md with platforms: [facebook, instagram], risk_level: HIGH
- SC-024 integration: creates approval file + 429 retry test (3 calls)

**Phase 9 — Twitter/X (T040-T044):**
- TwitterWatcher extends BaseWatcher, reads twitter_mock in dev_mode, POLL_INTERVAL_S=86400
- _fetch_live uses tweepy.Client with bearer_token
- AUTH errors set _paused=True
- create_action_file writes vault/Inbox/TW_ENGAGEMENT_{id}_{ts}.md
- post_twitter.py guards on twitter.enabled + rate_limiter.check_and_increment; enforces 280-char limit via _enforce_tweet_limit; truncates at 277+"..."
- SC-025 integration: approval file, rate_limit skip, valid YAML

**Phase 10 — Watchdog (T045-T047):**
- Watchdog class with check_all_threads(watcher_registry, thread_registry)
- Tracks _failure_counts and _exhausted per watcher name
- On dead thread: _restart_watcher() creates new daemon Thread
- On success: resets failure_count to 0, audit logs watchdog_restart result:success
- After 3 failures: _create_alert() creates vault/Inbox/WATCHDOG_ALERT_{name}_{ts}.md + adds to _exhausted
- SC-027 integration: dead thread restart + 3-failure alert

**Phase 11 — Ralph Wiggum (T048-T054):**
- RalphLoop(vault_root, task_file, prompt, max_iterations=10)
- _write_state writes vault/state/ralph_loop_state.json with 4 keys
- _is_done() checks vault/Done/ for filename
- _is_cancelled() checks vault/Rejected/ for filename
- On quarantine: shutil.move + creates RALPH_TIMEOUT_ALERT
- hooks/stop_hook.py: reads state, checks Done/Rejected dirs, updates state, always returns 0
- install_schedule._register_stop_hook(): writes .claude/hooks/Stop script, idempotent

**Final test count:** 709 passed, 4 skipped, 1 pre-existing failure (generate_invoice unrelated to phases 8-11)

## Outcome

- Impact: Implemented 4 Gold Tier P2 user stories covering social media monitoring, Twitter/Facebook posting with HITL approval, watchdog thread monitoring, and Ralph Wiggum autonomous loop
- Tests: 71 new tests across 12 test files — all PASS; no regressions in 559 Silver/Bronze tests
- Files: 20 new/modified files (12 implementations + 8 patch)
- Next prompts: Phase 12 orchestrator integration (T055-T060)
- Reflection: All TDD requirements met; tests written first then implementation; BaseWatcher pattern reused for both social watchers; idiomatic error category pattern applied for AUTH failures; watchdog failure_counts and _exhausted set prevent infinite retry loops

## Evaluation notes (flywheel)

- Failure modes observed: None in phases 8-11; 1 pre-existing generate_invoice test failure from Phase 4
- Graders run and results (PASS/FAIL): pytest tests/ -q — 709 PASS / 1 pre-existing FAIL / 4 SKIP
- Prompt variant (if applicable): null
- Next experiment: Phase 12 orchestrator integration + final polish
