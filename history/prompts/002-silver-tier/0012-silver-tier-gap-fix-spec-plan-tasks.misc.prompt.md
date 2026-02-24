---
id: "0012"
title: Silver Tier Gap Fix — Spec Plan Tasks
stage: misc
date: 2026-02-21
surface: agent
model: claude-sonnet-4-6
feature: 002-silver-tier
branch: 001-bronze-tier
user: USER-PC
command: "manual: gap analysis + spec/plan/tasks correction"
labels: ["gap-analysis", "silver-tier", "spec-correction", "plan-correction", "tasks-correction", "bronze-gap-fix", "vault-documents"]
links:
  spec: specs/002-silver-tier/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - specs/002-silver-tier/spec.md
  - specs/002-silver-tier/plan.md
  - specs/002-silver-tier/tasks.md
  - vault/Business_Goals.md
  - vault/Dashboard.md
  - vault/Company_Handbook.md
tests:
  - "No new tests (spec/plan/tasks correction + vault doc fixes). 416 tests still passing."
---

## Prompt

Read Documents.md carefully and deeply. Check whether all Silver Tier requirements are fulfilled according to the spec. Also build the MCP server according to the document. Additionally, review everything in depth to ensure that: WhatsApp, Gmail, LinkedIn, and Filesystem Watchers are structured exactly as defined in the document; the Dashboard.md is implemented according to the document; business_goal.md is aligned with the document; company_handbook.md is created according to the document; make sure everything matches the document's defined structure and specifications.

(Follow-up constraint): To fix this gap, correct the Silver Tier spec, plan, and tasks, and also resolve the gaps that were analyzed in the Bronze Tier. Only: Document spec: Simple run() loop / Current code: run(vault_root) with state persistence, dedup, error isolation / Gap: Current is a superset — more capable — not change.

## Response snapshot

**Gap analysis performed across 9 files** (Documents.md vs current codebase):

### Gaps found and corrective actions taken:

**Silver Tier SDD Artifacts — 3 files corrected:**

`specs/002-silver-tier/spec.md`:
- Updated `vault/Business_Goals.md` row in "New Files" table — now specifies Documents.md template schema exactly (YAML `review_frequency: weekly`, 5 required body sections with Revenue Target, Key Metrics table, Active Projects, Subscription Audit Rules)
- Added `vault/Dashboard.md` to "Files to Modify" table — documents bank balance section addition + "Recent Actions" → "Recent Activity" rename (Documents.md §1 + §5)
- Added `vault/Company_Handbook.md` to "Files to Modify" table — documents `review_frequency: weekly` frontmatter addition
- Added [UPDATE] entries to Section 12 Project Structure for all three vault files

`specs/002-silver-tier/plan.md`:
- Expanded T19 specification — added explicit content requirements for `vault/Business_Goals.md` (full template with all 5 sections), `vault/Dashboard.md` (bank balance section + section rename), `vault/Company_Handbook.md` (frontmatter addition)
- Added 3 rows to "Modified Files" table: Business_Goals.md / Dashboard.md / Company_Handbook.md with phase and change reason

`specs/002-silver-tier/tasks.md`:
- Updated T004 — now specifies Business_Goals.md must match Documents.md template exactly (review_frequency + all 5 sections with specific content)
- Updated T061 — now has 5 verifiable acceptance criteria for Business_Goals.md template compliance
- Added T064 — update Dashboard.md: bank balance + section rename [Bronze gap fix]
- Added T065 — update Company_Handbook.md: review_frequency frontmatter [Bronze gap fix]
- Updated Task Count Summary: 63 → 65 tasks

**Bronze Tier Gap Fixes — 3 vault files updated:**

`vault/Business_Goals.md`: Replaced Bronze placeholder with full Documents.md template — YAML `review_frequency: weekly`, Q1 2026 Objectives, Revenue Target ($10,000/month), Key Metrics table (3 rows), Active Projects (placeholders), Subscription Audit Rules (3 conditions)

`vault/Dashboard.md`: Added `## 💰 Bank Balance` placeholder table section after page header (2 rows: Business Account + Savings); renamed `## 📝 Recent Actions` → `## 📝 Recent Activity`

`vault/Company_Handbook.md`: Added `review_frequency: weekly` to YAML frontmatter

**Explicitly NOT changed (user constraint):**
- `src/watchers/base_watcher.py` — `run(vault_root)` with state persistence + dedup + error isolation is a superset of Document's simple `run()` loop; no change needed
- `src/watchers/filesystem_watcher.py` — more advanced than Document's `DropFolderHandler` template; no change needed
- `src/watchers/whatsapp_watcher.py` — fully compatible with Document spec; no change
- `.claude/settings.local.json` — email-mcp already configured via `npx @anthropic/email-mcp`; no build needed

**MCP Server status:** Already configured in `.claude/settings.local.json` with email-mcp, browser-mcp, filesystem, calendar-mcp, slack-mcp, odoo-mcp. No build required.

## Outcome

- ✅ Impact: Silver spec/plan/tasks now accurately reflect all Documents.md gaps as explicit tasks (T064, T065) and updated task descriptions (T004, T061). Bronze vault documents now match Documents.md templates. 65 total tasks (was 63).
- 🧪 Tests: No new tests. 416 tests still passing. Vault doc changes are non-code.
- 📁 Files: specs/002-silver-tier/spec.md, plan.md, tasks.md (corrected) + vault/Business_Goals.md, Dashboard.md, Company_Handbook.md (Bronze gap fixes)
- 🔁 Next prompts: `/sp.implement` Phase 1 (T001–T006 Setup including T064/T065 Bronze gap fixes already done)
- 🧠 Reflection: The BaseWatcher superset distinction was the key constraint — current implementation is richer than the Document template in all the right ways (state persistence, dedup, dry_run). The Documents.md template is the minimum viable blueprint; our architecture is a deliberate improvement. Vault documents were the most actionable Bronze gaps since they're content-only, no tests affected.

## Evaluation notes (flywheel)

- Failure modes observed: check-prerequisites.sh still returns bronze-tier paths; worked around by directly targeting 002-silver-tier/ paths
- Graders run and results (PASS/FAIL): Manual — spec.md has both vault docs in Files to Modify table; plan.md T19 has explicit template content; tasks.md has T064+T065; vault files verified against Documents.md template
- Prompt variant (if applicable): Gap analysis + targeted spec/plan/tasks correction (no implementation)
- Next experiment: Begin /sp.implement from Phase 1 T001 (T064+T065 Bronze gap fixes now pre-completed in vault docs)
