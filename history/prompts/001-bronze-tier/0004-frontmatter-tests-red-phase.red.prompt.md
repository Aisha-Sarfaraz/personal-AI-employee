---
id: "0004"
title: "Frontmatter Module Tests Red Phase"
stage: red
date: 2026-02-17
surface: agent
model: claude-sonnet-4-5-20250929
feature: 001-bronze-tier
branch: 001-bronze-tier
user: USER-PC
command: write tests/test_frontmatter.py
labels: ["red", "tdd", "frontmatter", "tests", "bronze-tier"]
links:
  spec: specs/001-bronze-tier/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - tests/test_frontmatter.py
tests:
  - tests/test_frontmatter.py
---

## Prompt

Write the file `D:/gemini-cli/practice/hacathons/fte-employe/tests/test_frontmatter.py` with comprehensive tests for the frontmatter module.

The module `src/core/frontmatter.py` will provide:
- `parse_frontmatter(content: str) -> tuple[dict, str]` — splits on `---`, yaml.safe_load the YAML block, returns (metadata_dict, body_string)
- `write_frontmatter(metadata: dict, body: str) -> str` — yaml.dump metadata between `---` markers + body
- `create_standard_metadata(type: str, source: str, priority: str = "MEDIUM", status: str = "new") -> dict` — returns dict with keys: type, source, timestamp (ISO-8601), priority, status

Tests needed:
1. parse_frontmatter with valid content returns correct dict and body
2. parse_frontmatter with no frontmatter returns empty dict and full content as body
3. parse_frontmatter with empty body returns dict and empty string
4. parse_frontmatter with malformed YAML returns empty dict and original content
5. write_frontmatter produces valid YAML between --- markers with body after
6. write_frontmatter roundtrip: write then parse returns original data
7. create_standard_metadata returns dict with all required keys
8. create_standard_metadata timestamp is valid ISO-8601
9. create_standard_metadata uses provided values and defaults

Use pytest. Import from `src.core.frontmatter`. Use `sys.path` insert if needed.

## Response snapshot

Created `tests/test_frontmatter.py` with 30 test cases organized in three classes:

- `TestParseFrontmatter` (11 tests): valid content dict/body split, YAML markers absent from body, no frontmatter → empty dict + full content, single delimiter treated as no frontmatter, empty body with/without trailing newline, malformed YAML (indent error, tab character) → empty dict + original content, multi-line body preserved, numeric/boolean YAML values, nested YAML dicts.

- `TestWriteFrontmatter` (8 tests): output structure (starts with ---, YAML in between, body after closing ---), body verbatim after closing marker, empty body valid, empty metadata dict valid, roundtrip (write→parse) for flat/nested/list metadata, return type is str.

- `TestCreateStandardMetadata` (13 tests): all 5 required keys present, ISO-8601 regex validation, timestamp is recent (within call window), type/source reflect arguments, priority defaults to "MEDIUM", status defaults to "new", custom priority/status overrides, all 4 params together, return type is dict, required keys subset check, parametrized priority levels (LOW/MEDIUM/HIGH/CRITICAL), parametrized status values (new/processed/failed/archived).

sys.path insert added so tests run from any working directory.

## Outcome

- Impact: Red phase complete — 30 failing tests written before src/core/frontmatter.py exists; drives the Green phase implementation.
- Tests: tests/test_frontmatter.py (30 test cases, expected to fail until implementation exists)
- Files: tests/test_frontmatter.py created (245 lines)
- Next prompts: Implement src/core/frontmatter.py (Green phase)
- Reflection: Tests cover all 9 specified scenarios plus edge cases (single delimiter, tab in YAML, parametrized values). ISO-8601 regex and datetime.fromisoformat used for timestamp validation. Roundtrip tests cover flat, nested, and list metadata structures.

## Evaluation notes (flywheel)

- Failure modes observed: None
- Graders run and results (PASS/FAIL): N/A (Red phase — no implementation yet)
- Prompt variant (if applicable): N/A
- Next experiment (smallest change to try): Implement src/core/frontmatter.py and run pytest to confirm all 30 tests pass (Green phase).
