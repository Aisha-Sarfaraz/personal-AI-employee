"""
Tests for src.skills.plan_task.run

Covers:
  1. Creates PLAN_*.md in /Plans from an item in /Needs_Action
  2. Plan has correct frontmatter (id, source_item, type, priority,
     status:pending, step_count, step_action_ids:{})
  3. Financial item generates financial-specific steps with approval flags
  4. Communication item generates communication-specific steps
  5. Task item generates task-specific steps
  6. General item generates general-specific steps
  7. Empty Needs_Action returns processed:0
  8. Source item status is updated to "planned" after processing
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
import yaml

from src.core.vault import write_frontmatter_file, read_frontmatter_file, list_folder


# ---------------------------------------------------------------------------
# Vault directories required by the Bronze Tier FTE system
# ---------------------------------------------------------------------------

VAULT_DIRS = (
    "Needs_Action",
    "Plans",
    "Done",
    "Logs",
    "Pending_Approval",
    "Approved",
    "Rejected",
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_vault(tmp_path: Path) -> str:
    """Create the standard vault directory structure and return its root path."""
    vault_root = tmp_path / "vault"
    for folder in VAULT_DIRS:
        (vault_root / folder).mkdir(parents=True, exist_ok=True)
    return str(vault_root)


def seed_needs_action_item(
    vault_root: str,
    filename: str,
    item_type: str,
    priority: str = "MEDIUM",
    status: str = "new",
) -> str:
    """Write a Needs_Action item and return its relative path."""
    metadata = {
        "id": filename.replace(".md", ""),
        "type": item_type,
        "priority": priority,
        "status": status,
        "source": "test_watcher",
        "timestamp": "2026-02-17T10:00:00",
    }
    body = f"Test item of type {item_type}."
    relative_path = f"Needs_Action/{filename}"
    write_frontmatter_file(vault_root, relative_path, metadata, body)
    return relative_path


def parse_yaml_frontmatter(file_path: Path) -> dict:
    """Read YAML frontmatter from a Markdown file and return the parsed dict."""
    text = file_path.read_text(encoding="utf-8")
    lines = text.splitlines()
    assert lines[0].strip() == "---", f"Expected frontmatter delimiter, got: {lines[0]!r}"
    close_idx = next(
        (i for i, line in enumerate(lines[1:], 1) if line.strip() == "---"), None
    )
    assert close_idx is not None, "No closing '---' found in frontmatter"
    yaml_block = "\n".join(lines[1:close_idx])
    return yaml.safe_load(yaml_block)


def get_plan_files(vault_root: str) -> list[str]:
    """Return all PLAN_*.md filenames from the Plans/ directory."""
    return [f for f in list_folder(vault_root, "Plans") if f.startswith("PLAN_")]


def read_plan_frontmatter(vault_root: str, plan_filename: str) -> dict:
    """Read and parse the frontmatter of a plan file."""
    plan_path = Path(vault_root) / "Plans" / plan_filename
    return parse_yaml_frontmatter(plan_path)


def read_plan_body(vault_root: str, plan_filename: str) -> str:
    """Return the body (non-frontmatter) content of a plan file."""
    _, body = read_frontmatter_file(vault_root, f"Plans/{plan_filename}")
    return body


# ---------------------------------------------------------------------------
# Test 1 — run() creates PLAN_*.md in /Plans from an item in /Needs_Action
# ---------------------------------------------------------------------------


class TestPlanFileCreation:
    def test_creates_plan_file_in_plans_folder(self, tmp_path: Path) -> None:
        """run() must produce at least one PLAN_*.md file inside Plans/."""
        from src.skills.plan_task import run

        vault_root = make_vault(tmp_path)
        seed_needs_action_item(vault_root, "ITEM_001.md", "general")

        result = run(vault_root)

        plan_files = get_plan_files(vault_root)
        assert len(plan_files) >= 1, (
            f"Expected at least one PLAN_*.md in Plans/, got: {plan_files}"
        )

    def test_plan_filename_matches_pattern(self, tmp_path: Path) -> None:
        """Plan filenames must start with PLAN_ and end with .md."""
        from src.skills.plan_task import run

        vault_root = make_vault(tmp_path)
        seed_needs_action_item(vault_root, "ITEM_002.md", "task")

        run(vault_root)

        plan_files = get_plan_files(vault_root)
        assert len(plan_files) == 1
        name = plan_files[0]
        assert name.startswith("PLAN_"), f"Expected PLAN_ prefix, got: {name}"
        assert name.endswith(".md"), f"Expected .md suffix, got: {name}"

    def test_returns_dict_with_processed_count(self, tmp_path: Path) -> None:
        """run() must return a dict with 'processed' count equal to items processed."""
        from src.skills.plan_task import run

        vault_root = make_vault(tmp_path)
        seed_needs_action_item(vault_root, "ITEM_003.md", "communication")

        result = run(vault_root)

        assert isinstance(result, dict), f"Expected dict, got {type(result)}"
        assert result["processed"] == 1, (
            f"Expected processed=1, got {result['processed']}"
        )

    def test_returns_dict_with_errors_list(self, tmp_path: Path) -> None:
        """run() must return a dict with 'errors' as a list."""
        from src.skills.plan_task import run

        vault_root = make_vault(tmp_path)
        seed_needs_action_item(vault_root, "ITEM_004.md", "financial")

        result = run(vault_root)

        assert "errors" in result, "Result dict must contain 'errors' key"
        assert isinstance(result["errors"], list), (
            f"'errors' must be a list, got {type(result['errors'])}"
        )

    def test_returns_dict_with_skipped_count(self, tmp_path: Path) -> None:
        """run() must return a dict with a 'skipped' integer."""
        from src.skills.plan_task import run

        vault_root = make_vault(tmp_path)
        seed_needs_action_item(vault_root, "ITEM_005.md", "general")

        result = run(vault_root)

        assert "skipped" in result, "Result dict must contain 'skipped' key"
        assert isinstance(result["skipped"], int), (
            f"'skipped' must be an int, got {type(result['skipped'])}"
        )


# ---------------------------------------------------------------------------
# Test 2 — Plan has correct frontmatter
# ---------------------------------------------------------------------------


class TestPlanFrontmatter:
    def test_plan_has_id_field(self, tmp_path: Path) -> None:
        """Plan frontmatter must include an 'id' field."""
        from src.skills.plan_task import run

        vault_root = make_vault(tmp_path)
        seed_needs_action_item(vault_root, "ITEM_010.md", "general")
        run(vault_root)

        plan_files = get_plan_files(vault_root)
        fm = read_plan_frontmatter(vault_root, plan_files[0])
        assert "id" in fm, f"Plan frontmatter missing 'id'. Keys: {list(fm.keys())}"
        assert fm["id"], "'id' must be non-empty"

    def test_plan_has_source_item_field(self, tmp_path: Path) -> None:
        """Plan frontmatter must include 'source_item' referencing the Needs_Action file."""
        from src.skills.plan_task import run

        vault_root = make_vault(tmp_path)
        seed_needs_action_item(vault_root, "ITEM_011.md", "general")
        run(vault_root)

        plan_files = get_plan_files(vault_root)
        fm = read_plan_frontmatter(vault_root, plan_files[0])
        assert "source_item" in fm, "Plan frontmatter missing 'source_item'"
        assert "ITEM_011" in str(fm["source_item"]), (
            f"source_item should reference ITEM_011, got: {fm['source_item']!r}"
        )

    def test_plan_has_type_field(self, tmp_path: Path) -> None:
        """Plan frontmatter must include a 'type' field matching the source item type."""
        from src.skills.plan_task import run

        vault_root = make_vault(tmp_path)
        seed_needs_action_item(vault_root, "ITEM_012.md", "financial")
        run(vault_root)

        plan_files = get_plan_files(vault_root)
        fm = read_plan_frontmatter(vault_root, plan_files[0])
        assert "type" in fm, "Plan frontmatter missing 'type'"
        assert fm["type"] == "financial", (
            f"Expected type='financial', got {fm['type']!r}"
        )

    def test_plan_has_priority_field(self, tmp_path: Path) -> None:
        """Plan frontmatter must include 'priority' matching the source item priority."""
        from src.skills.plan_task import run

        vault_root = make_vault(tmp_path)
        seed_needs_action_item(vault_root, "ITEM_013.md", "task", priority="HIGH")
        run(vault_root)

        plan_files = get_plan_files(vault_root)
        fm = read_plan_frontmatter(vault_root, plan_files[0])
        assert "priority" in fm, "Plan frontmatter missing 'priority'"
        assert fm["priority"] == "HIGH", (
            f"Expected priority='HIGH', got {fm['priority']!r}"
        )

    def test_plan_status_is_pending(self, tmp_path: Path) -> None:
        """Newly created plan frontmatter must have status='pending'."""
        from src.skills.plan_task import run

        vault_root = make_vault(tmp_path)
        seed_needs_action_item(vault_root, "ITEM_014.md", "general")
        run(vault_root)

        plan_files = get_plan_files(vault_root)
        fm = read_plan_frontmatter(vault_root, plan_files[0])
        assert "status" in fm, "Plan frontmatter missing 'status'"
        assert fm["status"] == "pending", (
            f"Expected status='pending', got {fm['status']!r}"
        )

    def test_plan_has_step_count_field(self, tmp_path: Path) -> None:
        """Plan frontmatter must include 'step_count' as a positive integer."""
        from src.skills.plan_task import run

        vault_root = make_vault(tmp_path)
        seed_needs_action_item(vault_root, "ITEM_015.md", "general")
        run(vault_root)

        plan_files = get_plan_files(vault_root)
        fm = read_plan_frontmatter(vault_root, plan_files[0])
        assert "step_count" in fm, "Plan frontmatter missing 'step_count'"
        assert isinstance(fm["step_count"], int) and fm["step_count"] > 0, (
            f"step_count must be a positive int, got {fm['step_count']!r}"
        )

    def test_plan_has_step_action_ids_as_empty_dict(self, tmp_path: Path) -> None:
        """Plan frontmatter must include 'step_action_ids' as an empty dict on creation."""
        from src.skills.plan_task import run

        vault_root = make_vault(tmp_path)
        seed_needs_action_item(vault_root, "ITEM_016.md", "general")
        run(vault_root)

        plan_files = get_plan_files(vault_root)
        fm = read_plan_frontmatter(vault_root, plan_files[0])
        assert "step_action_ids" in fm, "Plan frontmatter missing 'step_action_ids'"
        # Must be an empty dict (or None equivalent from YAML — coerce None to {})
        step_action_ids = fm["step_action_ids"] or {}
        assert step_action_ids == {}, (
            f"step_action_ids must be {{}} on creation, got {fm['step_action_ids']!r}"
        )


# ---------------------------------------------------------------------------
# Test 3 — Financial item generates financial-specific steps with approval flags
# ---------------------------------------------------------------------------


class TestFinancialItemSteps:
    def test_financial_plan_has_verify_step(self, tmp_path: Path) -> None:
        """Financial plan body must contain a step with action_type 'verify'."""
        from src.skills.plan_task import run

        vault_root = make_vault(tmp_path)
        seed_needs_action_item(vault_root, "FIN_001.md", "financial")
        run(vault_root)

        plan_files = get_plan_files(vault_root)
        body = read_plan_body(vault_root, plan_files[0])
        assert "verify" in body.lower(), (
            "Financial plan must include a 'verify' step in body"
        )

    def test_financial_plan_has_create_invoice_step(self, tmp_path: Path) -> None:
        """Financial plan body must contain a step with action_type 'create_invoice'."""
        from src.skills.plan_task import run

        vault_root = make_vault(tmp_path)
        seed_needs_action_item(vault_root, "FIN_002.md", "financial")
        run(vault_root)

        plan_files = get_plan_files(vault_root)
        body = read_plan_body(vault_root, plan_files[0])
        assert "create_invoice" in body.lower(), (
            "Financial plan must include 'create_invoice' action step in body"
        )

    def test_financial_plan_has_record_step(self, tmp_path: Path) -> None:
        """Financial plan body must contain a 'record' step."""
        from src.skills.plan_task import run

        vault_root = make_vault(tmp_path)
        seed_needs_action_item(vault_root, "FIN_003.md", "financial")
        run(vault_root)

        plan_files = get_plan_files(vault_root)
        body = read_plan_body(vault_root, plan_files[0])
        assert "record" in body.lower(), (
            "Financial plan must include a 'record' step in body"
        )

    def test_financial_plan_has_requires_approval_flag(self, tmp_path: Path) -> None:
        """Financial plan body must flag at least one step with requires_approval."""
        from src.skills.plan_task import run

        vault_root = make_vault(tmp_path)
        seed_needs_action_item(vault_root, "FIN_004.md", "financial")
        run(vault_root)

        plan_files = get_plan_files(vault_root)
        body = read_plan_body(vault_root, plan_files[0])
        assert "requires_approval" in body.lower(), (
            "Financial plan must mark at least one step with requires_approval"
        )

    def test_financial_plan_step_count_matches_financial_workflow(
        self, tmp_path: Path
    ) -> None:
        """Financial plan must have at least 3 steps (verify, create_invoice, record)."""
        from src.skills.plan_task import run

        vault_root = make_vault(tmp_path)
        seed_needs_action_item(vault_root, "FIN_005.md", "financial")
        run(vault_root)

        plan_files = get_plan_files(vault_root)
        fm = read_plan_frontmatter(vault_root, plan_files[0])
        assert fm["step_count"] >= 3, (
            f"Financial plan should have at least 3 steps, got {fm['step_count']}"
        )


# ---------------------------------------------------------------------------
# Test 4 — Communication item generates communication-specific steps
# ---------------------------------------------------------------------------


class TestCommunicationItemSteps:
    def test_communication_plan_has_draft_step(self, tmp_path: Path) -> None:
        """Communication plan body must contain a 'draft' step."""
        from src.skills.plan_task import run

        vault_root = make_vault(tmp_path)
        seed_needs_action_item(vault_root, "COMM_001.md", "communication")
        run(vault_root)

        plan_files = get_plan_files(vault_root)
        body = read_plan_body(vault_root, plan_files[0])
        assert "draft" in body.lower(), (
            "Communication plan must include a 'draft' step in body"
        )

    def test_communication_plan_has_send_step(self, tmp_path: Path) -> None:
        """Communication plan body must contain a 'send' step."""
        from src.skills.plan_task import run

        vault_root = make_vault(tmp_path)
        seed_needs_action_item(vault_root, "COMM_002.md", "communication")
        run(vault_root)

        plan_files = get_plan_files(vault_root)
        body = read_plan_body(vault_root, plan_files[0])
        assert "send" in body.lower(), (
            "Communication plan must include a 'send' step in body"
        )

    def test_communication_plan_has_review_step(self, tmp_path: Path) -> None:
        """Communication plan body must contain a 'review' step."""
        from src.skills.plan_task import run

        vault_root = make_vault(tmp_path)
        seed_needs_action_item(vault_root, "COMM_003.md", "communication")
        run(vault_root)

        plan_files = get_plan_files(vault_root)
        body = read_plan_body(vault_root, plan_files[0])
        assert "review" in body.lower(), (
            "Communication plan must include a 'review' step in body"
        )

    def test_communication_plan_step_count_at_least_three(self, tmp_path: Path) -> None:
        """Communication plan must have at least 3 steps (draft, review, send)."""
        from src.skills.plan_task import run

        vault_root = make_vault(tmp_path)
        seed_needs_action_item(vault_root, "COMM_004.md", "communication")
        run(vault_root)

        plan_files = get_plan_files(vault_root)
        fm = read_plan_frontmatter(vault_root, plan_files[0])
        assert fm["step_count"] >= 3, (
            f"Communication plan should have at least 3 steps, got {fm['step_count']}"
        )


# ---------------------------------------------------------------------------
# Test 5 — Task item generates task-specific steps
# ---------------------------------------------------------------------------


class TestTaskItemSteps:
    def test_task_plan_has_analyze_step(self, tmp_path: Path) -> None:
        """Task plan body must contain an 'analyze' step."""
        from src.skills.plan_task import run

        vault_root = make_vault(tmp_path)
        seed_needs_action_item(vault_root, "TASK_001.md", "task")
        run(vault_root)

        plan_files = get_plan_files(vault_root)
        body = read_plan_body(vault_root, plan_files[0])
        assert "analyze" in body.lower(), (
            "Task plan must include an 'analyze' step in body"
        )

    def test_task_plan_has_execute_step(self, tmp_path: Path) -> None:
        """Task plan body must contain an 'execute' step."""
        from src.skills.plan_task import run

        vault_root = make_vault(tmp_path)
        seed_needs_action_item(vault_root, "TASK_002.md", "task")
        run(vault_root)

        plan_files = get_plan_files(vault_root)
        body = read_plan_body(vault_root, plan_files[0])
        assert "execute" in body.lower(), (
            "Task plan must include an 'execute' step in body"
        )

    def test_task_plan_has_verify_step(self, tmp_path: Path) -> None:
        """Task plan body must contain a 'verify' step."""
        from src.skills.plan_task import run

        vault_root = make_vault(tmp_path)
        seed_needs_action_item(vault_root, "TASK_003.md", "task")
        run(vault_root)

        plan_files = get_plan_files(vault_root)
        body = read_plan_body(vault_root, plan_files[0])
        assert "verify" in body.lower(), (
            "Task plan must include a 'verify' step in body"
        )

    def test_task_plan_step_count_at_least_three(self, tmp_path: Path) -> None:
        """Task plan must have at least 3 steps (analyze, execute, verify)."""
        from src.skills.plan_task import run

        vault_root = make_vault(tmp_path)
        seed_needs_action_item(vault_root, "TASK_004.md", "task")
        run(vault_root)

        plan_files = get_plan_files(vault_root)
        fm = read_plan_frontmatter(vault_root, plan_files[0])
        assert fm["step_count"] >= 3, (
            f"Task plan should have at least 3 steps, got {fm['step_count']}"
        )


# ---------------------------------------------------------------------------
# Test 6 — General item generates general-specific steps
# ---------------------------------------------------------------------------


class TestGeneralItemSteps:
    def test_general_plan_has_review_step(self, tmp_path: Path) -> None:
        """General plan body must contain a 'review' step."""
        from src.skills.plan_task import run

        vault_root = make_vault(tmp_path)
        seed_needs_action_item(vault_root, "GEN_001.md", "general")
        run(vault_root)

        plan_files = get_plan_files(vault_root)
        body = read_plan_body(vault_root, plan_files[0])
        assert "review" in body.lower(), (
            "General plan must include a 'review' step in body"
        )

    def test_general_plan_has_process_step(self, tmp_path: Path) -> None:
        """General plan body must contain a 'process' step."""
        from src.skills.plan_task import run

        vault_root = make_vault(tmp_path)
        seed_needs_action_item(vault_root, "GEN_002.md", "general")
        run(vault_root)

        plan_files = get_plan_files(vault_root)
        body = read_plan_body(vault_root, plan_files[0])
        assert "process" in body.lower(), (
            "General plan must include a 'process' step in body"
        )

    def test_general_plan_step_count_at_least_two(self, tmp_path: Path) -> None:
        """General plan must have at least 2 steps (review, process)."""
        from src.skills.plan_task import run

        vault_root = make_vault(tmp_path)
        seed_needs_action_item(vault_root, "GEN_003.md", "general")
        run(vault_root)

        plan_files = get_plan_files(vault_root)
        fm = read_plan_frontmatter(vault_root, plan_files[0])
        assert fm["step_count"] >= 2, (
            f"General plan should have at least 2 steps, got {fm['step_count']}"
        )


# ---------------------------------------------------------------------------
# Test 7 — Empty Needs_Action returns processed:0
# ---------------------------------------------------------------------------


class TestEmptyNeedsAction:
    def test_empty_needs_action_returns_processed_zero(self, tmp_path: Path) -> None:
        """run() on an empty Needs_Action folder must return processed=0."""
        from src.skills.plan_task import run

        vault_root = make_vault(tmp_path)

        result = run(vault_root)

        assert result["processed"] == 0, (
            f"Expected processed=0 with empty Needs_Action, got {result['processed']}"
        )

    def test_empty_needs_action_creates_no_plan_files(self, tmp_path: Path) -> None:
        """run() on an empty Needs_Action folder must not create any plan files."""
        from src.skills.plan_task import run

        vault_root = make_vault(tmp_path)

        run(vault_root)

        plan_files = get_plan_files(vault_root)
        assert plan_files == [], (
            f"Expected no plan files with empty Needs_Action, got: {plan_files}"
        )

    def test_empty_needs_action_returns_empty_errors(self, tmp_path: Path) -> None:
        """run() on an empty Needs_Action folder must return an empty errors list."""
        from src.skills.plan_task import run

        vault_root = make_vault(tmp_path)

        result = run(vault_root)

        assert result["errors"] == [], (
            f"Expected errors=[] with empty Needs_Action, got {result['errors']}"
        )

    def test_empty_needs_action_returns_skipped_zero(self, tmp_path: Path) -> None:
        """run() on an empty Needs_Action folder must return skipped=0."""
        from src.skills.plan_task import run

        vault_root = make_vault(tmp_path)

        result = run(vault_root)

        assert result["skipped"] == 0, (
            f"Expected skipped=0 with empty Needs_Action, got {result['skipped']}"
        )


# ---------------------------------------------------------------------------
# Test 8 — Source item status updated to "planned"
# ---------------------------------------------------------------------------


class TestSourceItemStatusUpdate:
    def test_source_item_status_updated_to_planned(self, tmp_path: Path) -> None:
        """After run(), the source item in Needs_Action must have status='planned'."""
        from src.skills.plan_task import run

        vault_root = make_vault(tmp_path)
        seed_needs_action_item(vault_root, "ITEM_STATUS_001.md", "general")

        run(vault_root)

        # Re-read the source item from Needs_Action
        source_fm, _ = read_frontmatter_file(vault_root, "Needs_Action/ITEM_STATUS_001.md")
        assert source_fm["status"] == "planned", (
            f"Expected status='planned' after planning, got {source_fm['status']!r}"
        )

    def test_multiple_items_all_updated_to_planned(self, tmp_path: Path) -> None:
        """All processed items in Needs_Action must have status='planned' after run()."""
        from src.skills.plan_task import run

        vault_root = make_vault(tmp_path)
        items = [
            ("ITEM_A.md", "financial"),
            ("ITEM_B.md", "communication"),
            ("ITEM_C.md", "task"),
        ]
        for filename, item_type in items:
            seed_needs_action_item(vault_root, filename, item_type)

        result = run(vault_root)

        assert result["processed"] == 3, (
            f"Expected processed=3, got {result['processed']}"
        )
        for filename, _ in items:
            source_fm, _ = read_frontmatter_file(vault_root, f"Needs_Action/{filename}")
            assert source_fm["status"] == "planned", (
                f"{filename} status must be 'planned', got {source_fm['status']!r}"
            )

    def test_already_planned_items_are_skipped(self, tmp_path: Path) -> None:
        """Items already in 'planned' status must be skipped (not double-processed)."""
        from src.skills.plan_task import run

        vault_root = make_vault(tmp_path)
        # Seed one new item and one already-planned item
        seed_needs_action_item(vault_root, "NEW_ITEM.md", "general", status="new")
        seed_needs_action_item(vault_root, "OLD_ITEM.md", "general", status="planned")

        result = run(vault_root)

        # Only the new item should be processed; the planned one skipped
        assert result["processed"] == 1, (
            f"Expected processed=1 (only new item), got {result['processed']}"
        )
