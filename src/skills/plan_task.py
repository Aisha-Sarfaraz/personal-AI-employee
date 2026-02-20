"""Planner skill — generates execution plans from triaged items."""

import os
from datetime import datetime, timezone
from typing import Any

from src.core.vault import list_folder, read_frontmatter_file, write_frontmatter_file, move_file
from src.core.audit_logger import log_action
from src.skills.check_handbook import classify_action_risk


# Step templates per item type
PLAN_TEMPLATES: dict[str, list[dict[str, Any]]] = {
    "financial": [
        {"action_type": "file_operation", "description": "Verify financial document details", "risk_level": "LOW", "requires_approval": False},
        {"action_type": "file_operation", "description": "Check handbook compliance for financial action", "risk_level": "LOW", "requires_approval": False},
        {"action_type": "create_invoice", "description": "Create invoice/financial record", "risk_level": "HIGH", "requires_approval": True},
        {"action_type": "file_operation", "description": "Record transaction in audit log", "risk_level": "LOW", "requires_approval": False},
    ],
    "communication": [
        {"action_type": "file_operation", "description": "Draft response content", "risk_level": "LOW", "requires_approval": False},
        {"action_type": "file_operation", "description": "Review draft against handbook", "risk_level": "LOW", "requires_approval": False},
        {"action_type": "send_email", "description": "Send communication", "risk_level": "HIGH", "requires_approval": True},
    ],
    "task": [
        {"action_type": "file_operation", "description": "Analyze task requirements", "risk_level": "LOW", "requires_approval": False},
        {"action_type": "file_operation", "description": "Execute task actions", "risk_level": "MEDIUM", "requires_approval": False},
        {"action_type": "file_operation", "description": "Verify task completion", "risk_level": "LOW", "requires_approval": False},
    ],
    "document": [
        {"action_type": "file_operation", "description": "Review document contents", "risk_level": "LOW", "requires_approval": False},
        {"action_type": "file_operation", "description": "Process and archive document", "risk_level": "LOW", "requires_approval": False},
    ],
    "general": [
        {"action_type": "file_operation", "description": "Review item contents", "risk_level": "LOW", "requires_approval": False},
        {"action_type": "file_operation", "description": "Process item", "risk_level": "MEDIUM", "requires_approval": False},
    ],
    "unknown": [
        {"action_type": "file_operation", "description": "Review unknown item", "risk_level": "LOW", "requires_approval": False},
        {"action_type": "file_operation", "description": "Classify and process item", "risk_level": "MEDIUM", "requires_approval": False},
    ],
}


def _generate_steps(item_type: str, metadata: dict[str, Any]) -> list[dict[str, Any]]:
    """Generate plan steps based on item type."""
    template = PLAN_TEMPLATES.get(item_type, PLAN_TEMPLATES["general"])
    steps: list[dict[str, Any]] = []

    for i, step_template in enumerate(template, 1):
        step = {
            "step_number": i,
            "action_type": step_template["action_type"],
            "description": step_template["description"],
            "risk_level": step_template["risk_level"],
            "requires_approval": step_template["requires_approval"],
            "status": "pending",
        }
        steps.append(step)

    return steps


def _format_steps_body(steps: list[dict[str, Any]]) -> str:
    """Format steps as human-readable Obsidian markdown."""
    _RISK_EMOJI = {"LOW": "🟢", "MEDIUM": "🟡", "HIGH": "🟠", "CRITICAL": "🔴"}
    total = len(steps)
    lines = [f"## 📋 Execution Plan ({total} step{'s' if total != 1 else ''})\n"]

    for step in steps:
        risk = step["risk_level"]
        risk_emoji = _RISK_EMOJI.get(risk, "⚪")
        needs_approval = step["requires_approval"]
        approval_note = " — 👤 **Requires human approval**" if needs_approval else ""

        lines.append(f"### Step {step['step_number']}: {step['description']}")
        lines.append(f"- [ ] {risk_emoji} {step['description']}{approval_note}")
        lines.append(f"- **action_type**: {step['action_type']}")
        lines.append(f"- **description**: {step['description']}")
        lines.append(f"- **risk_level**: {risk}")
        lines.append(f"- **requires_approval**: {str(needs_approval).lower()}")
        lines.append(f"- **status**: {step['status']}")
        lines.append("")
    return "\n".join(lines)


def run(vault_root: str) -> dict[str, Any]:
    """Scan /Needs_Action and generate plans in /Plans.

    Args:
        vault_root: Absolute path to the vault directory.

    Returns:
        Dict with processed count, errors list, and skipped count.
    """
    processed = 0
    errors: list[str] = []
    skipped = 0

    needs_action_files = list_folder(vault_root, "Needs_Action")

    for filename in needs_action_files:
        try:
            filepath = os.path.join("Needs_Action", filename)
            metadata, body = read_frontmatter_file(vault_root, filepath)

            # Skip already-planned items
            if metadata.get("status") == "planned":
                skipped += 1
                continue

            item_type = metadata.get("type", "general")
            item_id = metadata.get("id", os.path.splitext(filename)[0])

            # Generate plan steps
            steps = _generate_steps(item_type, metadata)

            # Create plan metadata
            now = datetime.now(timezone.utc)
            timestamp = now.strftime("%Y%m%d_%H%M%S")
            plan_id = f"PLAN_{timestamp}_{item_id}"

            plan_metadata: dict[str, Any] = {
                "id": plan_id,
                "source_item": item_id,
                "type": item_type,
                "priority": metadata.get("priority", "MEDIUM"),
                "status": "pending",
                "created": now.strftime("%Y-%m-%dT%H:%M:%S"),
                "updated": now.strftime("%Y-%m-%dT%H:%M:%S"),
                "step_count": len(steps),
                "steps_completed": 0,
                "step_action_ids": {},
            }

            # Format plan body
            plan_body = _format_steps_body(steps)

            # Write plan file
            plan_filename = f"{plan_id}.md"
            write_frontmatter_file(vault_root, f"Plans/{plan_filename}", plan_metadata, plan_body)

            # Update source item status
            metadata["status"] = "planned"
            write_frontmatter_file(vault_root, filepath, metadata, body)

            log_action(
                vault_root=vault_root,
                agent="plan_task",
                action=f"created plan for {filename}",
                risk_tier="LOW",
                status="success",
                details=f"Plan {plan_id} with {len(steps)} steps",
                related_item=item_id,
            )

            processed += 1

        except Exception as e:
            errors.append(f"Error planning {filename}: {str(e)}")

    return {"processed": processed, "errors": errors, "skipped": skipped}
