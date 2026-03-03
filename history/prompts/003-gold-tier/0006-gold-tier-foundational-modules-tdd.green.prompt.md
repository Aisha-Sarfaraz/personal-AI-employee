---
id: "0006"
title: Gold Tier foundational modules TDD implementation
stage: green
date: 2026-02-25
surface: agent
model: claude-sonnet-4-6
feature: 003-gold-tier
branch: 003-gold-tier
user: USER
command: implement T011-T018 retry_handler audit_logger odoo_mcp
labels: ["gold-tier","tdd","retry","audit","odoo","mcp","tests"]
links:
  spec: specs/003-gold-tier/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - src/core/retry_handler.py
  - src/core/audit_logger.py
  - src/mcp_servers/odoo_mcp/client.py
  - src/mcp_servers/odoo_mcp/server.py
  - tests/test_retry_handler.py
  - tests/test_audit_logger_gold.py
  - tests/test_odoo_mcp_client.py
  - tests/test_odoo_mcp_server.py
tests:
  - tests/test_retry_handler.py (8 tests PASS)
  - tests/test_audit_logger_gold.py (10 tests PASS)
  - tests/test_odoo_mcp_client.py (14 tests PASS)
  - tests/test_odoo_mcp_server.py (6 tests PASS)
---

## Prompt

You are implementing the Gold Tier foundational modules for an AI business assistant.

Task T011+T012: Write tests then implement src/core/retry_handler.py
Task T013+T014: Write tests then implement audit_logger.py patch
Task T015+T016: Write tests then implement src/mcp_servers/odoo_mcp/client.py
Task T017+T018: Write tests then implement src/mcp_servers/odoo_mcp/server.py

[Full task prompt with all test and implementation code provided by user]

## Response snapshot

Implemented all 4 modules following TDD (Red-Green) cycle:

1. retry_handler.py: ErrorCategory enum (TRANSIENT/AUTH/LOGIC/DATA/SYSTEM),
   @with_retry decorator with exponential back-off + jitter, _compute_delay(),
   categorise_http_error(). AUTH/LOGIC/DATA errors bypass retry immediately.

2. audit_logger.py: Patched with new log() function writing Gold JSON-Lines schema
   (9 mandatory fields) to vault/Logs/YYYY-MM-DD.json, archive_old_logs() for
   retention, and backward-compatible log_action() now also writes JSON-Lines entry.

3. odoo_mcp/client.py: OdooMCPClient with 6 operations -- create_invoice,
   list_invoices, record_expense, get_account_balance, post_invoice,
   list_transactions. Write ops create HITL approval files; read ops return mocks
   in dev_mode. Uses @with_retry for resilience.

4. odoo_mcp/server.py: MCP stdio server with _list_tools_handler() and
   _call_tool_handler() as standalone async functions (testable without subprocess).
   Graceful fallback stubs when mcp package unavailable.

Test results:
- test_retry_handler.py: 8/8 PASS
- test_audit_logger_gold.py: 10/10 PASS
- test_odoo_mcp_client.py: 14/14 PASS
- test_odoo_mcp_server.py: 6/6 PASS
- Full suite (569 tests): 569 PASS, 4 skipped (no regressions)

## Outcome

- Impact: Gold Tier foundational modules complete -- retry resilience, structured audit logging, and Odoo MCP integration all implemented and verified
- Tests: 569 passed, 4 skipped (38 new Gold tests + 531 existing Silver/Bronze unchanged)
- Files: 4 new/patched implementation files, 4 new test files
- Next prompts: T019+ social media watcher, finance watcher, monitoring agent
- Reflection: file-writing via bash heredoc blocked by quote parsing on Windows; used plain-text chunk files + Python combine step as workaround

## Evaluation notes (flywheel)

- Failure modes observed: heredoc quoting issues on Windows (single-quoted heredoc << 'EOF' failed when body contained Python single-quoted strings at large line counts; workaround: write chunks as separate files then combine with Python)
- Graders run and results (PASS/FAIL): pytest 569/569 PASS
- Prompt variant (if applicable): null
- Next experiment (smallest change to try): use Write tool instead of Bash heredoc for large Python files
