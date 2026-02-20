---
id: "0005"
title: "Watcher Module Tests Red Phase"
stage: red
date: 2026-02-17
surface: agent
model: claude-sonnet-4-5-20250929
feature: 001-bronze-tier
branch: master
user: USER-PC
command: write tests/test_watcher.py
labels: ["red", "tdd", "watcher", "filesystem", "base-watcher", "tests", "bronze-tier"]
links:
  spec: specs/001-bronze-tier/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - tests/test_watcher.py
tests:
  - tests/test_watcher.py
---

## Prompt

Write the file `D:/gemini-cli/practice/hacathons/fte-employe/tests/test_watcher.py` with comprehensive tests for the watcher modules.

## base_watcher.py (src/watchers/base_watcher.py)
Abstract base class with:
- `check_for_updates() -> list[dict]` — abstract, returns list of new items
- `create_action_file(vault_root: str, item: dict) -> str` — creates frontmatter .md in Inbox/
- `_processed_ids: set` — tracks processed items
- `_state_file: str` — path to JSON state file
- `save_state()` / `load_state()` — JSON persistence of processed IDs
- `poll_interval: int` — configurable
- `run(vault_root: str)` — loop calling check_for_updates + create_action_file

## filesystem_watcher.py (src/watchers/filesystem_watcher.py)
Extends BaseWatcher:
- Uses watchdog Observer + FileSystemEventHandler on vault/Watch/
- on_created handler queues files
- check_for_updates returns queued files + directory scan
- Creates FILE_{timestamp}_{name}.md in /Inbox with content
- Binary/empty files get type:unknown, body "[Binary file — cannot display]"
- Dedup via processed IDs across restarts

### BaseWatcher tests:
1. ABC cannot be instantiated directly
2. create_action_file creates .md in Inbox/ with frontmatter (id, type, source, timestamp, priority, status)
3. save_state persists processed_ids to JSON file
4. load_state restores processed_ids from JSON file
5. Dedup: same item ID not processed twice
6. State persistence: save, new instance, load, verify IDs still tracked

### FilesystemWatcher tests:
1. Detects new text file in Watch/ via check_for_updates
2. Creates correct Inbox .md file with content from Watch/ file
3. Inbox file has correct frontmatter fields (source: filesystem_watcher)
4. Binary file detected → creates Inbox item with type:unknown, body "[Binary file — cannot display]"
5. Empty file → type:unknown
6. Dedup: same file not processed twice across check_for_updates calls

Use pytest with tmp_path. Create vault structure (Watch/, Inbox/, state/) in fixtures. For filesystem_watcher, you can test by placing files directly in Watch/ and calling check_for_updates without needing the actual watchdog Observer (test the processing logic).

Import from `src.watchers.base_watcher` and `src.watchers.filesystem_watcher`.

## Response snapshot

Created `tests/test_watcher.py` with 54 test cases organized in 13 test classes:

**BaseWatcher tests (30 tests across 8 classes):**
- `TestBaseWatcherCannotBeInstantiated` (1 test): ABC raises TypeError on direct instantiation.
- `TestBaseWatcherCreateActionFile` (9 tests): creates .md in Inbox/; all required frontmatter keys present (id, type, source, timestamp, priority, status); id matches item dict; source matches item dict; type is non-empty string; timestamp is non-empty; priority/status present; body content in file body; returns absolute path string.
- `TestBaseWatcherSaveState` (3 tests): creates JSON file; persists _processed_ids; overwrites previous state on second save.
- `TestBaseWatcherLoadState` (4 tests): restores processed_ids; missing file does not raise; merges/replaces IDs; empty list yields empty set.
- `TestBaseWatcherDedup` (4 tests): _processed_ids starts as set; no duplicates in set; create_action_file marks ID as processed; second call for same ID does not create additional Inbox file.
- `TestBaseWatcherStatePersistence` (2 tests): save/new instance/load roundtrip; create_action_file IDs survive save/load cycle.
- `TestBaseWatcherPollInterval` (3 tests): is int; is positive; can be set.
- `TestBaseWatcherStateFileAttribute` (3 tests): attribute exists; is str; can be overridden.

**FilesystemWatcher tests (24 tests across 5 classes):**
- `TestFilesystemWatcherCheckForUpdates` (5 tests): detects text file; returns list of dicts; empty Watch/ returns []; multiple files all detected; each item has path or name key.
- `TestFilesystemWatcherCreateInboxFile` (5 tests): creates Inbox .md; contains source text content; source frontmatter contains 'filesystem'; all required frontmatter keys present; filename contains source file name.
- `TestFilesystemWatcherBinaryFile` (3 tests): type=unknown; body contains 'Binary file'/'cannot display'; source still contains 'filesystem'.
- `TestFilesystemWatcherEmptyFile` (2 tests): type=unknown; all required frontmatter keys present.
- `TestFilesystemWatcherDedup` (4 tests): same file not returned twice across calls; only 1 Inbox file after 2 cycles; new file detected after first processed; dedup persists across save/load.
- `TestFilesystemWatcherAttributes` (5 tests): instantiates with vault_root; is BaseWatcher subclass; has _processed_ids set; has _state_file str; has poll_interval positive int.

A `_ConcreteWatcher` helper subclass is defined for testing non-abstract BaseWatcher behaviour. Helper functions `_make_vault`, `_parse_frontmatter`, `_list_inbox_files`, `_seed_text_file`, `_seed_binary_file` support all tests. sys.path insert ensures importability from any working directory.

All 54 tests collected successfully by pytest with no syntax errors (verified with `--collect-only`).

## Outcome

- Impact: Red phase complete — 54 contract-specifying tests written before src/watchers/base_watcher.py and src/watchers/filesystem_watcher.py exist; drives the Green phase implementation of both watcher modules.
- Tests: tests/test_watcher.py (54 test cases, expected to fail until implementation exists)
- Files: tests/test_watcher.py created
- Next prompts: Implement src/watchers/base_watcher.py and src/watchers/filesystem_watcher.py (Green phase)
- Reflection: Tests cover all 12 specified scenarios plus significant edge cases. Binary/empty file detection, state persistence roundtrip, cross-instance dedup, and ABC enforcement are all exercised. The _ConcreteWatcher pattern avoids needing a full implementation to test BaseWatcher behaviour. FilesystemWatcher tests bypass watchdog Observer entirely, testing pure processing logic via direct file seeding in Watch/.

## Evaluation notes (flywheel)

- Failure modes observed: None — all 54 tests collected cleanly
- Graders run and results (PASS/FAIL): N/A (Red phase — no implementation yet)
- Prompt variant (if applicable): N/A
- Next experiment (smallest change to try): Implement src/watchers/base_watcher.py (ABC with save_state/load_state/create_action_file) then src/watchers/filesystem_watcher.py (directory scan + binary detection) and run pytest to confirm all 54 tests pass (Green phase).
