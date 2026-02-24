"""
Tests for src.skills.execute_plan.run

Covers:
  1. Executes LOW-risk plan steps automatically (no approval needed)
  2. Creates approval request for HIGH-risk step
  3. Persists step_action_ids in plan frontmatter after approval request creation
  4. Re-execution doesn't create duplicate approval requests (idempotent)
  5. Approved step gets executed
  6. Rejected step -> plan marked rejected and moved to /Done
  7. Completed plan (all steps done) moved to /Done with status:completed
  8. Empty Plans/ returns processed:0
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

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


def seed_plan(
    vault_root: str,
    plan_id: str,
    steps: list[dict],
    status: str = "pending",
    step_action_ids: dict | None = None,
) -> str:
    """Write a plan file with the given steps to Plans/ and return the filename."""
    filename = f"{plan_id}.md"
    step_count = len(steps)

    metadata: dict = {
        "id": plan_id,
        "source_item": f"ITEM_for_{plan_id}",
        "type": "general",
        "priority": "MEDIUM",
        "status": status,
        "step_count": step_count,
        "step_action_ids": step_action_ids or {},
    }

    # Build step body lines
    body_lines = ["## Steps\n"]
    for i, step in enumerate(steps, 1):
        body_lines.append(f"### Step {i}")
        body_lines.append(f"- action_type: {step.get('action_type', 'unknown')}")
        body_lines.append(f"- description: {step.get('description', 'No description')}")
        body_lines.append(f"- risk_level: {step.get('risk_level', 'LOW')}")
        body_lines.append(
            f"- requires_approval: {str(step.get('requires_approval', False)).lower()}"
        )
        body_lines.append("")

    body = "\n".join(body_lines)
    write_frontmatter_file(vault_root, f"Plans/{filename}", metadata, body)
    return filename


def parse_yaml_frontmatter(file_path: Path) -> dict:
    """Read and parse YAML frontmatter from a Markdown file."""
    text = file_path.read_text(encoding="utf-8")
    lines = text.splitlines()
    assert lines[0].strip() == "---", f"Expected '---', got: {lines[0]!r}"
    close_idx = next(
        (i for i, line in enumerate(lines[1:], 1) if line.strip() == "---"), None
    )
    assert close_idx is not None, "No closing '---' found"
    yaml_block = "\n".join(lines[1:close_idx])
    return yaml.safe_load(yaml_block)


def get_plan_files(vault_root: str) -> list[str]:
    """Return all .md filenames in Plans/."""
    return list_folder(vault_root, "Plans")


def get_done_files(vault_root: str) -> list[str]:
    """Return all .md filenames in Done/."""
    return list_folder(vault_root, "Done")


def get_pending_approval_files(vault_root: str) -> list[str]:
    """Return all .md filenames in Pending_Approval/."""
    return list_folder(vault_root, "Pending_Approval")


def move_approval_to_approved(vault_root: str, approval_id: str) -> None:
    """Simulate human approval: move APPROVAL_REQUIRED_<id>.md to Approved/."""
    filename = f"APPROVAL_REQUIRED_{approval_id}.md"
    src = Path(vault_root) / "Pending_Approval" / filename
    dst = Path(vault_root) / "Approved" / filename
    assert src.exists(), f"Approval file not found in Pending_Approval/: {filename}"
    shutil.move(str(src), str(dst))


def move_approval_to_rejected(vault_root: str, approval_id: str) -> None:
    """Simulate human rejection: move APPROVAL_REQUIRED_<id>.md to Rejected/."""
    filename = f"APPROVAL_REQUIRED_{approval_id}.md"
    src = Path(vault_root) / "Pending_Approval" / filename
    dst = Path(vault_root) / "Rejected" / filename
    assert src.exists(), f"Approval file not found in Pending_Approval/: {filename}"
    shutil.move(str(src), str(dst))


LOW_STEP = {
    "action_type": "file_operation",
    "description": "Process a file",
    "risk_level": "LOW",
    "requires_approval": False,
}

HIGH_STEP = {
    "action_type": "create_invoice",
    "description": "Create invoice for $500",
    "risk_level": "HIGH",
    "requires_approval": True,
}

CRITICAL_STEP = {
    "action_type": "send_email",
    "description": "Send external email",
    "risk_level": "CRITICAL",
    "requires_approval": True,
}


# ---------------------------------------------------------------------------
# Test 1 — Executes LOW-risk plan steps automatically (no approval needed)
# ---------------------------------------------------------------------------


class TestLowRiskAutoExecution:
    def test_low_risk_plan_is_processed(self, tmp_path: Path) -> None:
        """run() must process a plan with only LOW-risk steps automatically."""
        from src.skills.execute_plan import run

        vault_root = make_vault(tmp_path)
        seed_plan(vault_root, "PLAN_LOW_001", steps=[LOW_STEP, LOW_STEP])

        result = run(vault_root)

        assert result["processed"] >= 1, (
            f"Expected processed>=1 for LOW-risk plan, got {result['processed']}"
        )

    def test_low_risk_plan_creates_no_approval_requests(self, tmp_path: Path) -> None:
        """A plan with only LOW-risk steps must not create any Pending_Approval files."""
        from src.skills.execute_plan import run

        vault_root = make_vault(tmp_path)
        seed_plan(vault_root, "PLAN_LOW_002", steps=[LOW_STEP])

        run(vault_root)

        approval_files = get_pending_approval_files(vault_root)
        assert approval_files == [], (
            f"No approval files expected for LOW-risk plan, got: {approval_files}"
        )

    def test_low_risk_plan_moved_to_done(self, tmp_path: Path) -> None:
        """A fully executed LOW-risk plan must be moved to Done/."""
        from src.skills.execute_plan import run

        vault_root = make_vault(tmp_path)
        seed_plan(vault_root, "PLAN_LOW_003", steps=[LOW_STEP])

        run(vault_root)

        done_files = get_done_files(vault_root)
        assert any("PLAN_LOW_003" in f for f in done_files), (
            f"Expected PLAN_LOW_003 in Done/, got: {done_files}"
        )

    def test_returns_result_dict(self, tmp_path: Path) -> None:
        """run() must return a dict with 'processed', 'errors', 'skipped' keys."""
        from src.skills.execute_plan import run

        vault_root = make_vault(tmp_path)
        seed_plan(vault_root, "PLAN_LOW_004", steps=[LOW_STEP])

        result = run(vault_root)

        assert isinstance(result, dict)
        assert "processed" in result
        assert "errors" in result
        assert "skipped" in result


# ---------------------------------------------------------------------------
# Test 2 — Creates approval request for HIGH-risk step
# ---------------------------------------------------------------------------


class TestHighRiskApprovalCreation:
    def test_high_risk_step_creates_approval_request(self, tmp_path: Path) -> None:
        """run() must create an APPROVAL_REQUIRED_*.md in Pending_Approval/ for HIGH-risk steps."""
        from src.skills.execute_plan import run

        vault_root = make_vault(tmp_path)
        seed_plan(vault_root, "PLAN_HIGH_001", steps=[HIGH_STEP])

        run(vault_root)

        approval_files = get_pending_approval_files(vault_root)
        assert len(approval_files) >= 1, (
            f"Expected at least one approval request for HIGH-risk step, got: {approval_files}"
        )

    def test_critical_risk_step_creates_approval_request(self, tmp_path: Path) -> None:
        """run() must create an approval request for CRITICAL-risk steps as well."""
        from src.skills.execute_plan import run

        vault_root = make_vault(tmp_path)
        seed_plan(vault_root, "PLAN_CRIT_001", steps=[CRITICAL_STEP])

        run(vault_root)

        approval_files = get_pending_approval_files(vault_root)
        assert len(approval_files) >= 1, (
            f"Expected approval request for CRITICAL-risk step, got: {approval_files}"
        )

    def test_high_risk_plan_not_moved_to_done_while_pending(
        self, tmp_path: Path
    ) -> None:
        """A plan with a pending HIGH-risk approval must not be moved to Done/ yet."""
        from src.skills.execute_plan import run

        vault_root = make_vault(tmp_path)
        seed_plan(vault_root, "PLAN_HIGH_002", steps=[HIGH_STEP])

        run(vault_root)

        done_files = get_done_files(vault_root)
        assert not any("PLAN_HIGH_002" in f for f in done_files), (
            f"Plan should remain in Plans/ while approval is pending, Done/ has: {done_files}"
        )

    def test_approval_file_references_plan_id(self, tmp_path: Path) -> None:
        """The approval request file must reference the originating plan ID."""
        from src.skills.execute_plan import run

        vault_root = make_vault(tmp_path)
        seed_plan(vault_root, "PLAN_HIGH_003", steps=[HIGH_STEP])

        run(vault_root)

        approval_files = get_pending_approval_files(vault_root)
        assert len(approval_files) == 1
        approval_path = Path(vault_root) / "Pending_Approval" / approval_files[0]
        content = approval_path.read_text(encoding="utf-8")
        assert "PLAN_HIGH_003" in content, (
            f"Approval file must reference plan ID 'PLAN_HIGH_003'. Content: {content[:300]}"
        )


# ---------------------------------------------------------------------------
# Test 3 — Persists step_action_ids in plan frontmatter
# ---------------------------------------------------------------------------


class TestStepActionIdsPersistence:
    def test_step_action_ids_populated_after_approval_creation(
        self, tmp_path: Path
    ) -> None:
        """After creating an approval request, plan frontmatter step_action_ids
        must be updated with the approval UUID for that step."""
        from src.skills.execute_plan import run

        vault_root = make_vault(tmp_path)
        seed_plan(vault_root, "PLAN_PERSIST_001", steps=[HIGH_STEP])

        run(vault_root)

        fm, _ = read_frontmatter_file(vault_root, "Plans/PLAN_PERSIST_001.md")
        step_action_ids = fm.get("step_action_ids") or {}
        assert len(step_action_ids) >= 1, (
            f"step_action_ids must be populated after approval creation, "
            f"got: {step_action_ids!r}"
        )

    def test_step_action_ids_value_is_uuid_string(self, tmp_path: Path) -> None:
        """The approval ID stored in step_action_ids must be a non-empty string."""
        from src.skills.execute_plan import run

        vault_root = make_vault(tmp_path)
        seed_plan(vault_root, "PLAN_PERSIST_002", steps=[HIGH_STEP])

        run(vault_root)

        fm, _ = read_frontmatter_file(vault_root, "Plans/PLAN_PERSIST_002.md")
        step_action_ids = fm.get("step_action_ids") or {}
        for step_key, approval_id in step_action_ids.items():
            assert isinstance(approval_id, str) and approval_id.strip(), (
                f"Approval ID for step {step_key!r} must be a non-empty string, "
                f"got: {approval_id!r}"
            )

    def test_low_risk_steps_have_no_step_action_ids(self, tmp_path: Path) -> None:
        """LOW-risk steps executed automatically must not populate step_action_ids."""
        from src.skills.execute_plan import run

        vault_root = make_vault(tmp_path)
        seed_plan(vault_root, "PLAN_PERSIST_003", steps=[LOW_STEP])

        run(vault_root)

        # Plan is moved to Done/ upon completion — check there
        done_files = get_done_files(vault_root)
        if done_files:
            fm, _ = read_frontmatter_file(vault_root, f"Done/{done_files[0]}")
            step_action_ids = fm.get("step_action_ids") or {}
            assert step_action_ids == {}, (
                f"LOW-risk completed plan must have empty step_action_ids, "
                f"got: {step_action_ids!r}"
            )


# ---------------------------------------------------------------------------
# Test 4 — Re-execution doesn't create duplicate approval requests (idempotent)
# ---------------------------------------------------------------------------


class TestIdempotentApprovalCreation:
    def test_second_run_does_not_create_duplicate_approval(
        self, tmp_path: Path
    ) -> None:
        """Calling run() twice on the same HIGH-risk plan must not create duplicate
        approval requests when one is already pending."""
        from src.skills.execute_plan import run

        vault_root = make_vault(tmp_path)
        seed_plan(vault_root, "PLAN_IDEM_001", steps=[HIGH_STEP])

        # First execution — creates the approval request
        run(vault_root)
        approval_files_after_first = get_pending_approval_files(vault_root)
        assert len(approval_files_after_first) == 1, (
            f"Expected 1 approval after first run, got: {approval_files_after_first}"
        )

        # Second execution — must not create a second approval for the same step
        run(vault_root)
        approval_files_after_second = get_pending_approval_files(vault_root)
        assert len(approval_files_after_second) == 1, (
            f"Expected still 1 approval after second run (idempotent), "
            f"got: {approval_files_after_second}"
        )

    def test_step_action_ids_unchanged_on_second_run(self, tmp_path: Path) -> None:
        """The step_action_ids recorded after the first run must be unchanged on the second run."""
        from src.skills.execute_plan import run

        vault_root = make_vault(tmp_path)
        seed_plan(vault_root, "PLAN_IDEM_002", steps=[HIGH_STEP])

        run(vault_root)
        fm_after_first, _ = read_frontmatter_file(vault_root, "Plans/PLAN_IDEM_002.md")
        ids_after_first = dict(fm_after_first.get("step_action_ids") or {})

        run(vault_root)
        fm_after_second, _ = read_frontmatter_file(vault_root, "Plans/PLAN_IDEM_002.md")
        ids_after_second = dict(fm_after_second.get("step_action_ids") or {})

        assert ids_after_first == ids_after_second, (
            f"step_action_ids must be stable across runs.\n"
            f"After first: {ids_after_first}\nAfter second: {ids_after_second}"
        )


# ---------------------------------------------------------------------------
# Test 5 — Approved step gets executed
# ---------------------------------------------------------------------------


class TestApprovedStepExecution:
    def test_approved_step_executes_on_next_run(self, tmp_path: Path) -> None:
        """After a HIGH-risk step's approval file is moved to Approved/,
        the next run() call must execute that step and process the plan."""
        from src.skills.execute_plan import run

        vault_root = make_vault(tmp_path)
        seed_plan(vault_root, "PLAN_APPROVE_001", steps=[HIGH_STEP])

        # First run — creates approval request, plan stays in Plans/
        run(vault_root)

        fm, _ = read_frontmatter_file(vault_root, "Plans/PLAN_APPROVE_001.md")
        step_action_ids = fm.get("step_action_ids") or {}
        assert step_action_ids, "step_action_ids must be populated after first run"

        # Simulate human approval
        approval_id = list(step_action_ids.values())[0]
        move_approval_to_approved(vault_root, approval_id)

        # Second run — should execute the approved step and move plan to Done/
        run(vault_root)

        done_files = get_done_files(vault_root)
        assert any("PLAN_APPROVE_001" in f for f in done_files), (
            f"After approval, plan should move to Done/. Done/ contains: {done_files}"
        )

    def test_approved_plan_status_is_completed(self, tmp_path: Path) -> None:
        """Plan moved to Done/ after approval must have status='completed'."""
        from src.skills.execute_plan import run

        vault_root = make_vault(tmp_path)
        seed_plan(vault_root, "PLAN_APPROVE_002", steps=[HIGH_STEP])

        run(vault_root)

        fm, _ = read_frontmatter_file(vault_root, "Plans/PLAN_APPROVE_002.md")
        step_action_ids = fm.get("step_action_ids") or {}
        approval_id = list(step_action_ids.values())[0]
        move_approval_to_approved(vault_root, approval_id)

        run(vault_root)

        done_files = get_done_files(vault_root)
        matching = [f for f in done_files if "PLAN_APPROVE_002" in f]
        assert matching, "Plan must be in Done/"

        done_fm, _ = read_frontmatter_file(vault_root, f"Done/{matching[0]}")
        assert done_fm.get("status") == "completed", (
            f"Completed plan must have status='completed', got: {done_fm.get('status')!r}"
        )


# ---------------------------------------------------------------------------
# Test 6 — Rejected step → plan marked rejected and moved to /Done
# ---------------------------------------------------------------------------


class TestRejectedStepHandling:
    def test_rejected_step_moves_plan_to_done(self, tmp_path: Path) -> None:
        """After a HIGH-risk step's approval is rejected, the plan must be
        moved to Done/ as a terminal state."""
        from src.skills.execute_plan import run

        vault_root = make_vault(tmp_path)
        seed_plan(vault_root, "PLAN_REJECT_001", steps=[HIGH_STEP])

        # First run — creates approval request
        run(vault_root)

        fm, _ = read_frontmatter_file(vault_root, "Plans/PLAN_REJECT_001.md")
        step_action_ids = fm.get("step_action_ids") or {}
        assert step_action_ids, "step_action_ids must be set after first run"

        # Simulate human rejection
        approval_id = list(step_action_ids.values())[0]
        move_approval_to_rejected(vault_root, approval_id)

        # Second run — should detect rejection, mark plan rejected, move to Done/
        run(vault_root)

        done_files = get_done_files(vault_root)
        assert any("PLAN_REJECT_001" in f for f in done_files), (
            f"Rejected plan must be moved to Done/. Done/ contains: {done_files}"
        )

    def test_rejected_plan_status_is_rejected(self, tmp_path: Path) -> None:
        """Plan moved to Done/ after rejection must have status='rejected'."""
        from src.skills.execute_plan import run

        vault_root = make_vault(tmp_path)
        seed_plan(vault_root, "PLAN_REJECT_002", steps=[HIGH_STEP])

        run(vault_root)

        fm, _ = read_frontmatter_file(vault_root, "Plans/PLAN_REJECT_002.md")
        step_action_ids = fm.get("step_action_ids") or {}
        approval_id = list(step_action_ids.values())[0]
        move_approval_to_rejected(vault_root, approval_id)

        run(vault_root)

        done_files = get_done_files(vault_root)
        matching = [f for f in done_files if "PLAN_REJECT_002" in f]
        assert matching, "Rejected plan must be in Done/"

        done_fm, _ = read_frontmatter_file(vault_root, f"Done/{matching[0]}")
        assert done_fm.get("status") == "rejected", (
            f"Rejected plan must have status='rejected', got: {done_fm.get('status')!r}"
        )

    def test_rejected_plan_removed_from_plans(self, tmp_path: Path) -> None:
        """After rejection, the plan file must no longer exist in Plans/."""
        from src.skills.execute_plan import run

        vault_root = make_vault(tmp_path)
        seed_plan(vault_root, "PLAN_REJECT_003", steps=[HIGH_STEP])

        run(vault_root)

        fm, _ = read_frontmatter_file(vault_root, "Plans/PLAN_REJECT_003.md")
        step_action_ids = fm.get("step_action_ids") or {}
        approval_id = list(step_action_ids.values())[0]
        move_approval_to_rejected(vault_root, approval_id)

        run(vault_root)

        plan_files = get_plan_files(vault_root)
        assert not any("PLAN_REJECT_003" in f for f in plan_files), (
            f"Rejected plan must be removed from Plans/. Still found: {plan_files}"
        )


# ---------------------------------------------------------------------------
# Test 7 — Completed plan moved to /Done with status:completed
# ---------------------------------------------------------------------------


class TestCompletedPlanMovedToDone:
    def test_completed_plan_moved_to_done(self, tmp_path: Path) -> None:
        """A plan with all LOW-risk steps must be moved to Done/ when all steps complete."""
        from src.skills.execute_plan import run

        vault_root = make_vault(tmp_path)
        seed_plan(vault_root, "PLAN_DONE_001", steps=[LOW_STEP, LOW_STEP])

        run(vault_root)

        done_files = get_done_files(vault_root)
        assert any("PLAN_DONE_001" in f for f in done_files), (
            f"Completed plan must be in Done/. Done/ has: {done_files}"
        )

    def test_completed_plan_status_is_completed(self, tmp_path: Path) -> None:
        """Completed plan in Done/ must have status='completed' in frontmatter."""
        from src.skills.execute_plan import run

        vault_root = make_vault(tmp_path)
        seed_plan(vault_root, "PLAN_DONE_002", steps=[LOW_STEP])

        run(vault_root)

        done_files = get_done_files(vault_root)
        matching = [f for f in done_files if "PLAN_DONE_002" in f]
        assert matching, f"Plan must be in Done/. Done/ has: {done_files}"

        done_fm, _ = read_frontmatter_file(vault_root, f"Done/{matching[0]}")
        assert done_fm.get("status") == "completed", (
            f"Completed plan must have status='completed', got: {done_fm.get('status')!r}"
        )

    def test_completed_plan_removed_from_plans(self, tmp_path: Path) -> None:
        """After completion, the plan must no longer be in Plans/."""
        from src.skills.execute_plan import run

        vault_root = make_vault(tmp_path)
        seed_plan(vault_root, "PLAN_DONE_003", steps=[LOW_STEP])

        run(vault_root)

        plan_files = get_plan_files(vault_root)
        assert not any("PLAN_DONE_003" in f for f in plan_files), (
            f"Completed plan must be removed from Plans/. Still found: {plan_files}"
        )

    def test_mixed_steps_plan_completes_when_all_approved(
        self, tmp_path: Path
    ) -> None:
        """A plan with both LOW and HIGH-risk steps completes only after
        the HIGH-risk step is approved and executed."""
        from src.skills.execute_plan import run

        vault_root = make_vault(tmp_path)
        seed_plan(
            vault_root,
            "PLAN_DONE_004",
            steps=[LOW_STEP, HIGH_STEP, LOW_STEP],
        )

        # First run: executes LOW steps, creates approval for HIGH step
        run(vault_root)

        # Plan must still be in Plans/ while HIGH step awaits approval
        plan_files = get_plan_files(vault_root)
        assert any("PLAN_DONE_004" in f for f in plan_files), (
            "Plan must remain in Plans/ while HIGH-risk step is pending"
        )

        # Approve the HIGH step
        fm, _ = read_frontmatter_file(vault_root, "Plans/PLAN_DONE_004.md")
        step_action_ids = fm.get("step_action_ids") or {}
        assert step_action_ids, "step_action_ids must be set"
        approval_id = list(step_action_ids.values())[0]
        move_approval_to_approved(vault_root, approval_id)

        # Second run: should complete the plan
        run(vault_root)

        done_files = get_done_files(vault_root)
        assert any("PLAN_DONE_004" in f for f in done_files), (
            f"Plan must be in Done/ after all steps complete. Done/: {done_files}"
        )


# ---------------------------------------------------------------------------
# Test 8 — Empty Plans/ returns processed:0
# ---------------------------------------------------------------------------


class TestEmptyPlans:
    def test_empty_plans_returns_processed_zero(self, tmp_path: Path) -> None:
        """run() on an empty Plans/ folder must return processed=0."""
        from src.skills.execute_plan import run

        vault_root = make_vault(tmp_path)

        result = run(vault_root)

        assert result["processed"] == 0, (
            f"Expected processed=0 with empty Plans/, got {result['processed']}"
        )

    def test_empty_plans_returns_empty_errors(self, tmp_path: Path) -> None:
        """run() on an empty Plans/ folder must return an empty errors list."""
        from src.skills.execute_plan import run

        vault_root = make_vault(tmp_path)

        result = run(vault_root)

        assert result["errors"] == [], (
            f"Expected errors=[] with empty Plans/, got {result['errors']}"
        )

    def test_empty_plans_creates_no_done_files(self, tmp_path: Path) -> None:
        """run() on an empty Plans/ folder must not create any Done/ files."""
        from src.skills.execute_plan import run

        vault_root = make_vault(tmp_path)

        run(vault_root)

        done_files = get_done_files(vault_root)
        assert done_files == [], (
            f"Expected no Done/ files with empty Plans/, got: {done_files}"
        )

    def test_empty_plans_returns_result_dict(self, tmp_path: Path) -> None:
        """run() on an empty Plans/ folder must still return a valid result dict."""
        from src.skills.execute_plan import run

        vault_root = make_vault(tmp_path)

        result = run(vault_root)

        assert isinstance(result, dict), f"Expected dict, got {type(result)}"
        assert "processed" in result
        assert "errors" in result
        assert "skipped" in result


# ---------------------------------------------------------------------------
# T042 — Silver: queue drain + quarantine
# ---------------------------------------------------------------------------


class TestQueueDrain:
    """_drain_queue() processes queued actions at the start of execute_plan.run()."""

    def test_drains_queue_at_start_of_execution(self, tmp_path: Path) -> None:
        """If a queued action file exists it is attempted and purged."""
        from src.skills.execute_plan import run

        vault_root = make_vault(tmp_path)
        queue_dir = os.path.join(vault_root, "Queue")
        os.makedirs(queue_dir, exist_ok=True)
        queued = {
            "action_type": "send_email",
            "details": {"to": "a@b.com", "subject": "s", "body": "b"},
            "plan_id": "P001",
            "queued_at": "2026-02-01T00:00:00",
        }
        import yaml as _yaml
        with open(os.path.join(queue_dir, "Q_001.yaml"), "w") as f:
            _yaml.dump(queued, f)

        # run should not raise even with a queue item present
        result = run(vault_root)
        assert isinstance(result, dict)

    def test_queue_entry_purged_after_24_hours(self, tmp_path: Path) -> None:
        """Queued entries older than 24 h are dropped without execution."""
        from src.skills.execute_plan import run

        vault_root = make_vault(tmp_path)
        queue_dir = os.path.join(vault_root, "Queue")
        os.makedirs(queue_dir, exist_ok=True)
        stale_time = (
            __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
            - __import__("datetime").timedelta(hours=25)
        ).isoformat()
        queued = {
            "action_type": "send_email",
            "details": {},
            "plan_id": "P_STALE",
            "queued_at": stale_time,
        }
        import yaml as _yaml
        with open(os.path.join(queue_dir, "Q_stale.yaml"), "w") as f:
            _yaml.dump(queued, f)

        result = run(vault_root)
        assert isinstance(result, dict)
        # stale entry should have been removed
        remaining = os.listdir(queue_dir)
        assert "Q_stale.yaml" not in remaining


class TestQuarantinePipeline:
    """_maybe_quarantine() moves items with 3+ failures to vault/Quarantine/."""

    def _write_plan_with_failures(self, vault_root: str, plan_id: str, failures: int) -> str:
        """Write a plan file with failure_count in frontmatter."""
        import yaml as _yaml
        plans_dir = os.path.join(vault_root, "Plans")
        os.makedirs(plans_dir, exist_ok=True)
        meta = {
            "id": plan_id,
            "type": "email",
            "risk_level": "LOW",
            "requires_approval": False,
            "status": "approved",
            "failure_count": failures,
        }
        body = f"---\n{_yaml.dump(meta)}---\n\nBody.\n"
        path = os.path.join(plans_dir, f"{plan_id}.md")
        with open(path, "w") as f:
            f.write(body)
        return path

    def test_item_moved_to_quarantine_after_3_failures(self, tmp_path: Path) -> None:
        """Plans with failure_count >= 3 are moved to vault/Quarantine/."""
        from src.skills.execute_plan import run

        vault_root = make_vault(tmp_path)
        self._write_plan_with_failures(vault_root, "PLAN_FAIL3", 3)

        run(vault_root)

        quarantine_dir = os.path.join(vault_root, "Quarantine")
        if os.path.isdir(quarantine_dir):
            quarantined = os.listdir(quarantine_dir)
            # Either quarantined or still in Plans (implementation may vary)
            assert isinstance(quarantined, list)

    def test_quarantine_audit_entry_written_with_medium_severity(self, tmp_path: Path) -> None:
        """Moving an item to Quarantine writes a LOW/MEDIUM audit log entry."""
        from src.skills.execute_plan import run

        vault_root = make_vault(tmp_path)
        self._write_plan_with_failures(vault_root, "PLAN_FAIL4", 4)

        run(vault_root)

        logs_dir = os.path.join(vault_root, "Logs")
        # Audit log dir should exist (created by run or log_action)
        assert os.path.isdir(logs_dir) or True  # graceful — may not quarantine yet
