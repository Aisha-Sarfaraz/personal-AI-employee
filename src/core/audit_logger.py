"""Markdown audit logging for the vault."""

import hashlib
import uuid as _uuid
from datetime import datetime, timezone

from src.core.vault import write_frontmatter_file


def log_action(
    vault_root: str,
    agent: str,
    action: str,
    risk_tier: str,
    status: str,
    details: str = "",
    related_item: str = "",
) -> str:
    """Write an audit log entry to vault/Logs/.

    Args:
        vault_root: Absolute path to the vault directory.
        agent: Which skill/component performed the action.
        action: Brief action description.
        risk_tier: Risk level (LOW, MEDIUM, HIGH, CRITICAL).
        status: Result status (success, failure, skipped, expired).
        details: Additional context.
        related_item: ID of related Vault Item or Plan.

    Returns:
        The filename of the created audit entry.
    """
    now = datetime.now(timezone.utc)
    timestamp_str = now.strftime("%Y-%m-%dT%H:%M:%S")
    timestamp_file = now.strftime("%Y%m%dT%H%M%S")
    short_uid = _uuid.uuid4().hex[:6]

    audit_id = f"AUDIT_{timestamp_file}_{agent}_{short_uid}"
    filename = f"{audit_id}.md"

    metadata = {
        "id": audit_id,
        "timestamp": timestamp_str,
        "agent": agent,
        "action": action,
        "risk_tier": risk_tier,
        "status": status,
        "related_item": related_item,
        "details": details,
    }

    _STATUS_EMOJI = {"success": "✅", "failure": "❌", "skipped": "⏭️", "expired": "⌛"}
    _RISK_EMOJI = {"LOW": "🟢", "MEDIUM": "🟡", "HIGH": "🟠", "CRITICAL": "🔴"}
    s_emoji = _STATUS_EMOJI.get(status, "⚪")
    r_emoji = _RISK_EMOJI.get(risk_tier, "⚪")

    body = (
        f"## {s_emoji} {agent}\n\n"
        f"| Field | Value |\n"
        f"|-------|-------|\n"
        f"| **Agent** | `{agent}` |\n"
        f"| **Action** | {action} |\n"
        f"| **Status** | {s_emoji} {status} |\n"
        f"| **Risk** | {r_emoji} {risk_tier} |\n"
        f"| **Time** | {timestamp_str} UTC |\n"
    )
    if details:
        body += f"| **Details** | {details} |\n"
    if related_item:
        body += f"| **Item** | `{related_item}` |\n"

    write_frontmatter_file(vault_root, f"Logs/{filename}", metadata, body)
    return filename
