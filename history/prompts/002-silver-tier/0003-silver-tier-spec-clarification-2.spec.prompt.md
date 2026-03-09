---
id: "0003"
title: Silver Tier Spec Clarification Round 2
stage: spec
date: 2026-02-20
surface: agent
model: claude-sonnet-4-6
feature: 002-silver-tier
branch: 001-bronze-tier
user: USER-PC
command: "/sp.clarify (second session, post WhatsApp Playwright change)"
labels: ["clarification", "silver-tier", "linkedin", "playwright", "generate-plan", "gmail-auth"]
links:
  spec: specs/002-silver-tier/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - specs/002-silver-tier/spec.md
  - specs/002-silver-tier/quickstart.md
tests:
  - "No new tests (clarification-only session; 416 tests still passing)"
---

## Prompt

/sp.clarify (second clarification session — triggered after WhatsApp watcher switched to
Playwright-based implementation in 416-test commit, which exposed new architectural ambiguities)

## Response snapshot

Ambiguity scan identified 3 remaining critical gaps after WhatsApp Playwright change:

1. **LinkedIn/browser-mcp Python runtime conflict** (CRITICAL) — browser-mcp is a Claude Code
   MCP server; standalone Python orchestrator cannot call it at runtime.
2. **generate_plan.py / plan_task.py integration** (HIGH) — FR-I02 referenced non-existent
   `plan_task._generate_steps()` function.
3. **gmail_auth.py location** (MEDIUM) — file referenced in FR-A01 but absent from components map.

**Q1**: How does runtime Python orchestrator call LinkedIn? → **A: Playwright directly**
- FR-C01 updated: Playwright direct, same pattern as WhatsApp
- FR-C04 updated: `post_social` uses Playwright, not browser-mcp
- Architecture diagram updated: `browser-mcp → Playwright direct`
- Files to Modify table: action_executor now "MCP SDK (email) + Playwright (post_social)"
- Pre-spec clarifications table corrected
- quickstart.md Step 5 rewritten for Playwright setup_session() pattern

**Q2**: How does generate_plan.py integrate with plan_task.py? → **A: Post-process approach**
- FR-I02 rewritten: call plan_task.run() → prepend ## Reasoning to written Plan.md file
- plan_task.py remains completely unchanged (Bronze invariant preserved)
- generate_plan interface contract updated with post-process docstring
- Returns extended dict: plan_task result + {claude_enriched: bool}

**Q3**: Where does gmail_auth.py live? → **A: src/watchers/gmail_auth.py**
- Added to New Files table in Section 5
- Project structure tree updated with [NEW] tag
- quickstart.md troubleshooting table corrected (removed Twilio row, added WhatsApp/LinkedIn)
- FR-A01 already correct (references gmail_auth.py)

## Outcome

- ✅ Impact: 3 critical implementation blockers resolved. All browser-mcp runtime references
  replaced with Playwright-direct. generate_plan.py now has a clear, non-destructive hook into
  plan_task.py. gmail_auth.py has an explicit file location.
- 🧪 Tests: No new tests (clarification session). 416 tests remain green.
- 📁 Files: specs/002-silver-tier/spec.md (8 edits), specs/002-silver-tier/quickstart.md (3 edits)
- 🔁 Next prompts: `/sp.plan` to generate specs/002-silver-tier/plan.md
- 🧠 Reflection: The browser-mcp issue is a common architectural trap — MCP servers configured
  in `.claude/settings.local.json` are only available inside Claude Code sessions, not to
  standalone Python processes running as background services. The WhatsApp Playwright implementation
  revealed this pattern, making the LinkedIn correction natural.

## Evaluation notes (flywheel)

- Failure modes observed: None in this session; all 3 questions answered in first attempt each
- Graders run and results (PASS/FAIL): Manual check — grep for "browser-mcp" in FR-C shows 0
  remaining incorrect references; _generate_steps() removed from FR-I02; gmail_auth.py in table
- Prompt variant (if applicable): Second /sp.clarify session in same feature sprint
- Next experiment: Run /sp.clarify automatically after any watcher implementation (spec drift risk)
