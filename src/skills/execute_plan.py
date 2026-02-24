"""Plan Executor skill — executes plans with HITL approval gates."""

import os
import re
import yaml as _yaml
from datetime import datetime, timedelta, timezone
from typing import Any

from src.core.vault import list_folder, read_frontmatter_file, write_frontmatter_file, move_file
from src.core.approval import create_approval_request, check_approval_status
from src.core.audit_logger import log_action
from src.actions.action_executor import execute_action


def _drain_queue(vault_root: str) -> None:
    """Process queued actions and drop stale ones (older than 24 h)."""
    queue_dir = os.path.join(vault_root, "Queue")
    if not os.path.isdir(queue_dir):
        return

    now = datetime.now(timezone.utc)
    for fname in list(os.listdir(queue_dir)):
        if not fname.endswith((".yaml", ".yml")):
            continue
        fpath = os.path.join(queue_dir, fname)
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                entry = _yaml.safe_load(f)
            if not isinstance(entry, dict):
                os.remove(fpath)
                continue

            queued_at_str = str(entry.get("queued_at", ""))
            if queued_at_str:
                queued_at = datetime.fromisoformat(queued_at_str.replace("Z", "+00:00"))
                if queued_at.tzinfo is None:
                    queued_at = queued_at.replace(tzinfo=timezone.utc)
                if (now - queued_at).total_seconds() > 24 * 3600:
                    os.remove(fpath)
                    continue

            # Attempt to execute the queued action
            action_type = entry.get("action_type", "")
            details = entry.get("details", {}) or {}
            plan_id = entry.get("plan_id", "")
            if action_type:
                try:
                    execute_action(action_type, details, vault_root=vault_root, plan_id=plan_id)
                except Exception:
                    pass
            os.remove(fpath)
        except Exception:
            pass


def _maybe_quarantine(
    vault_root: str,
    filepath: str,
    metadata: dict,
    body: str,
    filename: str,
) -> bool:
    """Move a plan to Quarantine/ if it has >= 3 failures. Returns True if quarantined."""
    failure_count = int(metadata.get("failure_count", 0))
    if failure_count < 3:
        return False

    quarantine_dir = os.path.join(vault_root, "Quarantine")
    os.makedirs(quarantine_dir, exist_ok=True)
    metadata["status"] = "quarantined"
    write_frontmatter_file(vault_root, filepath, metadata, body)
    try:
        move_file(vault_root, filepath, os.path.join("Quarantine", filename))
    except Exception:
        pass

    try:
        log_action(
            vault_root=vault_root,
            agent="execute_plan",
            action="quarantine",
            risk_tier="MEDIUM",
            status="warning",
            details=(
                f"Plan {metadata.get('id', filename)} quarantined after {failure_count} failures"
            ),
        )
    except Exception:
        pass

    return True


def _parse_steps_from_body(body: str) -> list[dict[str, Any]]:
    """Parse step details from plan markdown body.

    Supports both formats:
    - ``### Step 1: description`` with ``- **key**: value``
    - ``### Step 1`` with ``- key: value``
    """
    steps: list[dict[str, Any]] = []
    current_step: dict[str, Any] | None = None

    for line in body.split("\n"):
        # Match "### Step N" or "### Step N: description"
        step_match = re.match(r"^### Step (\d+)", line)
        if step_match:
            if current_step:
                steps.append(current_step)
            current_step = {"step_number": int(step_match.group(1))}
            continue

        if current_step and line.startswith("- "):
            # Try bold format: - **key**: value
            bold_match = re.match(r"- \*\*(\w+)\*\*:\s*(.+)", line)
            # Try plain format: - key: value
            plain_match = re.match(r"- (\w+):\s*(.+)", line)

            match = bold_match or plain_match
            if match:
                key = match.group(1)
                value = match.group(2).strip()
                if key == "requires_approval":
                    value = value.lower() == "true"
                current_step[key] = value

    if current_step:
        steps.append(current_step)

    return steps


def run(vault_root: str) -> dict[str, Any]:
    """Scan /Plans for pending plans and execute them.

    Args:
        vault_root: Absolute path to the vault directory.

    Returns:
        Dict with processed count, errors list, and skipped count.
    """
    processed = 0
    errors: list[str] = []
    skipped = 0

    # Silver Tier: drain queued actions before processing plans
    _drain_queue(vault_root)

    plan_files = list_folder(vault_root, "Plans")

    for filename in plan_files:
        try:
            filepath = os.path.join("Plans", filename)
            metadata, body = read_frontmatter_file(vault_root, filepath)

            # Silver Tier: quarantine plans with too many failures
            if _maybe_quarantine(vault_root, filepath, metadata, body, filename):
                skipped += 1
                continue

            plan_status = metadata.get("status", "")
            if plan_status not in ("pending", "executing"):
                skipped += 1
                continue

            metadata["status"] = "executing"
            step_action_ids = metadata.get("step_action_ids", {})
            if not isinstance(step_action_ids, dict):
                step_action_ids = {}

            steps = _parse_steps_from_body(body)
            plan_id = metadata.get("id", filename)
            all_complete = True
            plan_rejected = False

            # Track which steps are already done (persisted as list in metadata)
            completed_steps = set(metadata.get("completed_steps", []))

            for step in steps:
                step_num = step.get("step_number", 0)
                step_key = str(step_num)
                risk_level = step.get("risk_level", "LOW")
                requires_approval = step.get("requires_approval", False)
                action_type = step.get("action_type", "file_operation")

                # Skip already-completed steps
                if step_key in completed_steps:
                    continue

                # Check if step needs approval
                if requires_approval or risk_level in ("HIGH", "CRITICAL"):
                    # Check for existing approval ID (idempotent)
                    approval_id = step_action_ids.get(step_key)

                    if approval_id is None:
                        # Create new approval request
                        approval_id = create_approval_request(
                            vault_root=vault_root,
                            plan_id=plan_id,
                            step_number=step_num,
                            action_type=action_type,
                            action_description=step.get("description", ""),
                            risk_level=risk_level,
                        )
                        step_action_ids[step_key] = approval_id
                        metadata["step_action_ids"] = step_action_ids
                        write_frontmatter_file(vault_root, filepath, metadata, body)

                        log_action(
                            vault_root=vault_root,
                            agent="execute_plan",
                            action=f"created approval request for step {step_num}",
                            risk_tier=risk_level,
                            status="success",
                            details=f"Approval ID: {approval_id}",
                            related_item=plan_id,
                        )

                    # Check approval status
                    status = check_approval_status(vault_root, approval_id)

                    if status == "approved":
                        # Execute the approved action
                        result = execute_action(action_type, step.get("details", {}))
                        completed_steps.add(step_key)
                        log_action(
                            vault_root=vault_root,
                            agent="execute_plan",
                            action=f"executed step {step_num} ({action_type})",
                            risk_tier=risk_level,
                            status="success",
                            details=result.get("details", ""),
                            related_item=plan_id,
                        )
                    elif status == "rejected":
                        # Rejection is terminal
                        plan_rejected = True
                        log_action(
                            vault_root=vault_root,
                            agent="execute_plan",
                            action=f"step {step_num} rejected",
                            risk_tier=risk_level,
                            status="skipped",
                            details="Approval rejected by human. Plan terminated.",
                            related_item=plan_id,
                        )
                        break
                    elif status == "expired":
                        all_complete = False
                        # Re-queue: clear the approval ID so a new one is created next run
                        step_action_ids.pop(step_key, None)
                        metadata["step_action_ids"] = step_action_ids
                        write_frontmatter_file(vault_root, filepath, metadata, body)
                        break
                    else:
                        # Still pending
                        all_complete = False
                        break
                else:
                    # Low/medium risk — auto-execute
                    result = execute_action(action_type, step.get("details", {}))
                    completed_steps.add(step_key)

            # Persist completed steps tracking
            metadata["completed_steps"] = sorted(completed_steps)
            metadata["steps_completed"] = len(completed_steps)

            # Update plan status based on outcome
            if plan_rejected:
                metadata["status"] = "rejected"
                now_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
                body = body + (
                    f"\n\n---\n\n"
                    f"## ❌ Rejection Summary\n\n"
                    f"> [!failure] Plan Rejected\n"
                    f"> A required approval was rejected. No further steps will be executed.\n\n"
                    f"| Field | Value |\n"
                    f"|-------|-------|\n"
                    f"| **Outcome** | Rejected |\n"
                    f"| **Terminated** | {now_str} UTC |\n"
                    f"| **Steps Completed** | {len(completed_steps)} of {len(steps)} |\n"
                )
                write_frontmatter_file(vault_root, filepath, metadata, body)
                move_file(vault_root, filepath, os.path.join("Done", filename))
                log_action(
                    vault_root=vault_root,
                    agent="execute_plan",
                    action=f"plan rejected: {plan_id}",
                    risk_tier="HIGH",
                    status="skipped",
                    details="Plan rejected and moved to Done",
                    related_item=plan_id,
                )
            elif all_complete:
                metadata["status"] = "completed"
                metadata["steps_completed"] = len(steps)
                now_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
                body = body + (
                    f"\n\n---\n\n"
                    f"## ✅ Completion Summary\n\n"
                    f"> [!success] Plan Completed\n"
                    f"> All steps were executed successfully.\n\n"
                    f"| Field | Value |\n"
                    f"|-------|-------|\n"
                    f"| **Outcome** | Completed |\n"
                    f"| **Finished** | {now_str} UTC |\n"
                    f"| **Steps Completed** | {len(steps)} of {len(steps)} |\n"
                )
                write_frontmatter_file(vault_root, filepath, metadata, body)
                move_file(vault_root, filepath, os.path.join("Done", filename))
                log_action(
                    vault_root=vault_root,
                    agent="execute_plan",
                    action=f"plan completed: {plan_id}",
                    risk_tier="LOW",
                    status="success",
                    details=f"All {len(steps)} steps completed",
                    related_item=plan_id,
                )
            else:
                # Still waiting for approvals
                write_frontmatter_file(vault_root, filepath, metadata, body)

            processed += 1

        except Exception as e:
            errors.append(f"Error executing {filename}: {str(e)}")

    return {"processed": processed, "errors": errors, "skipped": skipped}
