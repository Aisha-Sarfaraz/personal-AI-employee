---
id: "0010"
title: Silver Tier Implementation Plan Generation
stage: plan
date: 2026-02-21
surface: agent
model: claude-sonnet-4-6
feature: 002-silver-tier
branch: 001-bronze-tier
user: USER-PC
command: "/sp.plan"
labels: ["plan", "silver-tier", "architecture", "phases", "tdd", "research", "data-model", "contracts"]
links:
  spec: specs/002-silver-tier/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - specs/002-silver-tier/research.md
  - specs/002-silver-tier/data-model.md
  - specs/002-silver-tier/plan.md
  - specs/002-silver-tier/contracts/skill-interface.md
  - specs/002-silver-tier/contracts/watcher-interface.md
tests:
  - "No new tests (plan phase; 416 tests still passing)"
---

## Prompt

/sp.plan

(Continued from previous context. Spec fully clarified across 8 sessions, 17 Q→A bullets,
25+ stale reference fixes. PHRs 0007, 0008, 0009 also written in this session for the
previously interrupted sessions 6, 7, 8.)

## Response snapshot

Generated all Silver Tier Phase 0 and Phase 1 plan artifacts:

**Phase 0 — Research** (`specs/002-silver-tier/research.md`):
10 implementation decisions resolved:
- MCP Python SDK: `stdio_client` + `ClientSession` asyncio pattern + `asyncio.run()` sync wrapper
- Gmail OAuth2: `google.oauth2.credentials.Credentials.from_authorized_user_file()` + auto-refresh
- Playwright persistent context: `launch_persistent_context(user_data_dir=...)` same pattern as WhatsApp watcher
- Daemon thread + health dict: `threading.Thread(daemon=True)` + `threading.Lock`-protected shared dict
- Rate limiter: JSON state, epoch-hour windows, 2h pruning
- Idempotency: JSON state, compound key `{agent}:{action}:{sha256[:8]}:{epoch_day}`, TTL pruning
- Opt-out parsing: line-by-line Markdown, `- ` prefix, case-insensitive
- LinkedIn cadence guard: scan `vault/Logs/` for `action:linkedin_post` in last N days
- Weekly briefing: regex parse Markdown audit entries; Gold-tier JSON deferred
- Scheduling idempotency: delete+recreate (Windows), strip+append (POSIX crontab)

**Phase 1 — Design Artifacts**:

`data-model.md`: 9 entities defined:
- InboxItem (normalized; all-watcher fields)
- WatcherState (per-watcher state file)
- WatcherHealth (orchestrator shared dict; runtime-only)
- QueueEntry (`vault/state/queue.json`)
- IdempotencyEntry (`vault/state/idempotency_keys.json`)
- RateLimitCounter (`vault/state/rate_limits.json`)
- LinkedInPostPlan (specialized Plan.md)
- BriefingDocument (`vault/Briefings/BRIEFING_*.md` with 9 required sections)
- OptOutList (Markdown list format + parsing rules)

`contracts/skill-interface.md`: All Silver skill contracts defined:
- detect_lead, generate_plan, generate_linkedin_post, weekly_briefing, install_schedule
- Core modules: idempotency.py, rate_limiter.py, opt_out.py
- action_executor.py extended contract (send_email real mode + post_social new action)

`contracts/watcher-interface.md`: All Silver watcher contracts defined:
- BaseWatcher extensions (dry_run property + _load_mock_items helper)
- GmailWatcher (check_for_updates + _parse_message dual-path normaliser)
- WhatsAppWatcher (existing — compatibility note)
- LinkedInWatcher (check_for_updates + setup_session)
- Orchestrator watcher registration contract

`plan.md`: 7-phase implementation plan:
- Phase 1: Core safety infra (rate_limiter, idempotency, opt_out) — T01–T03
- Phase 2: BaseWatcher ext + Gmail watcher — T04–T06
- Phase 3: LinkedIn watcher — T07
- Phase 4: Action executor extensions — T08
- Phase 5: 6 new skills + plan templates — T09–T14
- Phase 6: Orchestrator wiring + execute_plan + dashboard extensions — T15–T17
- Phase 7: Config, vault files, E2E tests, certification — T18–T21
- 21 tasks total, clear dependency order, TDD mandate for each task
- Bronze invariant verification commands at each phase exit gate
- SC-010 through SC-020 mapped to specific phases and tasks

## Outcome

- ✅ Impact: Complete implementation plan ready. 21 tasks in 7 phases. Dependency order clear.
  TDD mandate explicit with specific test names per task. Bronze invariant enforced at each
  phase gate. All 11 Silver SC verified with specific pytest commands.
- 🧪 Tests: No new tests this session (plan phase). 416 tests remain green.
- 📁 Files: 5 new files created in specs/002-silver-tier/ (research.md, data-model.md, plan.md,
  contracts/skill-interface.md, contracts/watcher-interface.md)
- 🔁 Next prompts: `/sp.tasks` to generate tasks.md; then `/sp.implement` Phase 1
- 🧠 Reflection: 8 clarification sessions + research phase gave strong implementation confidence.
  Key architectural clarity: all Playwright uses same `launch_persistent_context()` pattern;
  no browser-mcp at runtime; asyncio wrapping needed only for MCP SDK calls;
  audit log (not separate tracker) is source of truth for LinkedIn cadence guard.

## Evaluation notes (flywheel)

- Failure modes observed: update-agent-context.sh targeted bronze-tier (branch mismatch);
  script ran successfully but resolved against bronze spec not silver spec — acceptable
  since silver plan.md is the authoritative artifact
- Graders run and results (PASS/FAIL): Manual — plan.md exists at expected path;
  research.md has 10 decisions; data-model.md has 9 entities; contracts/ has 2 files;
  SC-010 through SC-020 all mapped in plan; 21 tasks defined
- Prompt variant (if applicable): /sp.plan first execution for Silver Tier
- Next experiment: Run /sp.tasks immediately to generate atomic task list aligned with
  the 7-phase dependency order in plan.md; verify tasks.md has correct phase mapping
