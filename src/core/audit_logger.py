"""Audit logging for the vault — Markdown (Silver/Bronze) + JSON-Lines (Gold)."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import uuid as _uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from src.core.vault import write_frontmatter_file

# ---------------------------------------------------------------------------
# Gold Tier — JSON-Lines structured logging
# ---------------------------------------------------------------------------

_MANDATORY_STR_FIELDS = ("action_type", "actor", "target", "approval_status", "result")
_VALID_RESULTS = {"success", "failure", "skipped", "degraded"}
_VALID_APPROVAL = {"auto", "approved", "rejected", "pending"}


def log(
    vault_root: str,
    action_type: str,
    actor: str,
    target: str,
    parameters: dict[str, Any] | None = None,
    approval_status: str = "auto",
    approved_by: str | None = "system",
    result: str = "success",
    error: str | None = None,
) -> None:
    """Write a Gold-schema JSON-Lines audit entry to vault/Logs/YYYY-MM-DD.json.

    Schema (9 mandatory fields):
        timestamp       ISO8601
        action_type     str
        actor           str  (claude_code|orchestrator|watcher:<name>|mcp:<server>)
        target          str
        parameters      dict
        approval_status str  (auto|approved|rejected|pending)
        approved_by     str|null (human|system|null)
        result          str  (success|failure|skipped|degraded)
        error           str|null

    Raises:
        ValueError: if any mandatory string field is empty.
    """
    # Validate mandatory fields
    field_values = {
        "action_type": action_type,
        "actor": actor,
        "target": target,
        "approval_status": approval_status,
        "result": result,
    }
    for field in _MANDATORY_STR_FIELDS:
        val = field_values[field]
        if not val:
            raise ValueError(f"Mandatory audit field '{field}' must not be empty")

    now = datetime.now(timezone.utc)
    entry = {
        "timestamp": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "action_type": action_type,
        "actor": actor,
        "target": target,
        "parameters": parameters or {},
        "approval_status": approval_status,
        "approved_by": approved_by,
        "result": result,
        "error": error,
    }

    log_dir = os.path.join(vault_root, "Logs")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f"{now.strftime('%Y-%m-%d')}.json")

    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def archive_old_logs(vault_root: str, retention_days: int = 90) -> None:
    """Move JSON log files older than retention_days to vault/Logs/Archive/.

    Args:
        vault_root: Path to vault root.
        retention_days: Files older than this many days are archived.
    """
    log_dir = os.path.join(vault_root, "Logs")
    archive_dir = os.path.join(log_dir, "Archive")
    if not os.path.isdir(log_dir):
        return

    os.makedirs(archive_dir, exist_ok=True)
    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)

    for fname in os.listdir(log_dir):
        if not fname.endswith(".json"):
            continue
        date_str = fname[:-5]  # strip .json
        try:
            file_date = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            continue
        if file_date < cutoff:
            src = os.path.join(log_dir, fname)
            dst = os.path.join(archive_dir, fname)
            shutil.move(src, dst)


# ---------------------------------------------------------------------------
# Silver/Bronze backward-compatible Markdown logging
# ---------------------------------------------------------------------------

def log_action(
    vault_root: str,
    agent: str,
    action: str,
    risk_tier: str,
    status: str,
    details: str = "",
    related_item: str = "",
) -> str:
    """Write an audit log entry — Markdown file + Gold JSON-Lines entry.

    Backward-compatible wrapper: preserves the original Silver signature.
    Also appends a JSON-Lines entry to today's .json log file.

    Args:
        vault_root: Absolute path to the vault directory.
        agent: Which skill/component performed the action.
        action: Brief action description.
        risk_tier: Risk level (LOW, MEDIUM, HIGH, CRITICAL).
        status: Result status (success, failure, skipped, expired).
        details: Additional context.
        related_item: ID of related Vault Item or Plan.

    Returns:
        The filename of the created Markdown audit entry.
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

    # Also write Gold JSON-Lines entry
    _result_map = {"success": "success", "failure": "failure", "skipped": "skipped",
                   "expired": "skipped"}
    gold_result = _result_map.get(status, "success")
    try:
        log(
            vault_root=vault_root,
            action_type=action,
            actor=agent,
            target=related_item or vault_root,
            parameters={"details": details, "risk_tier": risk_tier},
            approval_status="auto",
            approved_by="system",
            result=gold_result,
            error=None if status != "failure" else details,
        )
    except Exception:
        pass  # Never let Gold logging break Silver callers

    return filename
