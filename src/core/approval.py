"""HITL approval management for the vault."""

import os
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any

from src.core.vault import write_frontmatter_file, read_frontmatter_file, list_folder
from src.core.frontmatter import parse_frontmatter


def create_approval_request(
    vault_root: str,
    plan_id: str,
    step_number: int,
    action_type: str,
    action_description: str,
    risk_level: str,
) -> str:
    """Create an approval request file in Pending_Approval/.

    Args:
        vault_root: Absolute path to the vault directory.
        plan_id: ID of the originating plan.
        step_number: Which step in the plan requires approval.
        action_type: The action being requested.
        action_description: Human-readable description.
        risk_level: Risk level (HIGH or CRITICAL).

    Returns:
        The UUID of the created approval request.
    """
    approval_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    created = now.strftime("%Y-%m-%dT%H:%M:%S")
    expires = (now + timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%S")

    metadata: dict[str, Any] = {
        "id": approval_id,
        "plan_id": plan_id,
        "step_number": step_number,
        "action_type": action_type,
        "action_description": action_description,
        "risk_level": risk_level,
        "created": created,
        "expires": expires,
        "status": "pending",
    }

    # Make plan_id human-readable
    plan_label = plan_id
    parts = plan_id.split("_")
    if len(parts) >= 3 and len(parts[1]) == 8:
        try:
            date_str = f"{parts[1][:4]}-{parts[1][4:6]}-{parts[1][6:8]}"
            time_str = f"{parts[2][:2]}:{parts[2][2:4]}" if len(parts[2]) >= 4 else ""
            plan_label = f"Plan from {date_str} at {time_str}" if time_str else f"Plan from {date_str}"
        except Exception:
            pass

    risk_emoji = {"HIGH": "🟠", "CRITICAL": "🔴"}.get(risk_level, "⚪")

    body = (
        f"# 👤 Approval Required\n\n"
        f"> [!warning] This action needs your decision\n"
        f"> The system is paused on this step and cannot proceed without your approval.\n\n"
        f"## Action Details\n\n"
        f"| Field | Value |\n"
        f"|-------|-------|\n"
        f"| **Action** | {action_description} |\n"
        f"| **Type** | `{action_type}` |\n"
        f"| **Risk Level** | {risk_emoji} {risk_level} |\n"
        f"| **Plan** | {plan_label} |\n"
        f"| **Step** | {step_number} |\n\n"
        f"## Your Decision\n\n"
        f"> [!note] Instructions\n"
        f"> Check **one** box below and save the file.\n\n"
        f"- [ ] Approve\n"
        f"- [ ] Reject\n\n"
        f"> [!caution] Expiry\n"
        f"> This request expires at **{expires} UTC**. After expiry, a new request will be created automatically.\n"
    )

    filename = f"APPROVAL_REQUIRED_{approval_id}.md"
    write_frontmatter_file(vault_root, f"Pending_Approval/{filename}", metadata, body)
    return approval_id


def check_approval_status(vault_root: str, approval_id: str) -> str:
    """Check the status of an approval request.

    Checks the file in three ways:
    1. Checkbox in body: [x] Approve or [x] Reject
    2. File moved to Approved/ or Rejected/ folder
    3. Still pending in Pending_Approval/

    Args:
        vault_root: Absolute path to the vault directory.
        approval_id: UUID of the approval request.

    Returns:
        One of: "approved", "rejected", "pending", "expired".
    """
    filename = f"APPROVAL_REQUIRED_{approval_id}.md"

    # Check Approved/ folder
    approved_path = os.path.join(vault_root, "Approved", filename)
    if os.path.exists(approved_path):
        return "approved"

    # Check Rejected/ folder
    rejected_path = os.path.join(vault_root, "Rejected", filename)
    if os.path.exists(rejected_path):
        return "rejected"

    # Check Pending_Approval/ — read checkboxes and expiry
    pending_path = os.path.join(vault_root, "Pending_Approval", filename)
    if os.path.exists(pending_path):
        with open(pending_path, "r", encoding="utf-8") as f:
            content = f.read()

        metadata, body = parse_frontmatter(content)

        # Check checkboxes in body
        if "- [x] Approve" in body or "- [X] Approve" in body:
            return "approved"
        if "- [x] Reject" in body or "- [X] Reject" in body:
            return "rejected"

        # Check for expiry
        expires_str = metadata.get("expires", "")
        if expires_str:
            try:
                expires_dt = datetime.fromisoformat(expires_str).replace(tzinfo=timezone.utc)
                if datetime.now(timezone.utc) > expires_dt:
                    return "expired"
            except (ValueError, TypeError):
                pass
        return "pending"

    return "expired"
