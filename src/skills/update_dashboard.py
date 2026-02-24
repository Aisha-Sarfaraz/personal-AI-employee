"""Dashboard Updater skill — regenerates Dashboard.md with vault status."""

import json
import os
from datetime import datetime, timezone
from typing import Any

from src.core.vault import list_folder, write_frontmatter_file, read_frontmatter_file


def _get_folder_counts(vault_root: str) -> dict[str, int]:
    """Count .md files in each vault folder."""
    folders = ["Inbox", "Needs_Action", "Plans", "Done", "Logs",
               "Pending_Approval", "Approved", "Rejected"]
    counts: dict[str, int] = {}
    for folder in folders:
        counts[folder] = len(list_folder(vault_root, folder))
    return counts


def _count_optional_folder(vault_root: str, folder: str) -> int:
    """Count .md files in an optional vault folder; returns 0 if absent."""
    path = os.path.join(vault_root, folder)
    if not os.path.isdir(path):
        return 0
    return len([f for f in os.listdir(path) if f.endswith(".md")])


def _get_watcher_health(vault_root: str) -> dict[str, Any]:
    """Check watcher health from state files."""
    state_dir = os.path.join(vault_root, "state")
    health: dict[str, Any] = {}

    if not os.path.isdir(state_dir):
        return {"filesystem_watcher": {"status": "unknown", "last_updated": "N/A"}}

    for fname in os.listdir(state_dir):
        if fname.endswith("_state.json"):
            watcher_name = fname.replace("_state.json", "")
            try:
                with open(os.path.join(state_dir, fname), "r", encoding="utf-8") as f:
                    state = json.load(f)
                health[watcher_name] = {
                    "status": "running",
                    "last_updated": state.get("last_updated", "unknown"),
                    "processed_count": len(state.get("processed_ids", [])),
                }
            except (json.JSONDecodeError, OSError):
                health[watcher_name] = {"status": "error", "last_updated": "N/A"}

    if not health:
        health["filesystem_watcher"] = {"status": "not started", "last_updated": "N/A"}

    return health


def _get_pending_approvals(vault_root: str) -> list[dict[str, Any]]:
    """Get pending approval requests with age."""
    approvals: list[dict[str, Any]] = []
    pending_files = list_folder(vault_root, "Pending_Approval")
    now = datetime.now(timezone.utc)

    for filename in pending_files:
        try:
            metadata, _ = read_frontmatter_file(vault_root, f"Pending_Approval/{filename}")
            created_str = metadata.get("created", "")
            age = "unknown"
            if created_str:
                try:
                    created = datetime.fromisoformat(created_str).replace(tzinfo=timezone.utc)
                    delta = now - created
                    hours = int(delta.total_seconds() / 3600)
                    if hours < 1:
                        age = f"{int(delta.total_seconds() / 60)}m"
                    else:
                        age = f"{hours}h"
                except (ValueError, TypeError):
                    pass
            approvals.append({
                "filename": filename,
                "action_type": metadata.get("action_type", "unknown"),
                "risk_level": metadata.get("risk_level", "unknown"),
                "age": age,
            })
        except Exception:
            pass

    return approvals


def _get_recent_logs(vault_root: str, limit: int = 10) -> list[dict[str, Any]]:
    """Get recent audit log entries."""
    logs: list[dict[str, Any]] = []
    log_files = list_folder(vault_root, "Logs")
    # Sort by filename (which contains timestamp) descending
    log_files.sort(reverse=True)

    for filename in log_files[:limit]:
        try:
            metadata, _ = read_frontmatter_file(vault_root, f"Logs/{filename}")
            logs.append({
                "timestamp": metadata.get("timestamp", "unknown"),
                "agent": metadata.get("agent", "unknown"),
                "action": metadata.get("action", "unknown"),
                "status": metadata.get("status", "unknown"),
            })
        except Exception:
            pass

    return logs


def run(vault_root: str) -> dict[str, Any]:
    """Regenerate Dashboard.md with current vault status.

    Args:
        vault_root: Absolute path to the vault directory.

    Returns:
        Dict with processed count, errors list, and skipped count.
    """
    try:
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
        counts = _get_folder_counts(vault_root)
        quarantine_count = _count_optional_folder(vault_root, "Quarantine")
        briefings_count = _count_optional_folder(vault_root, "Briefings")
        watcher_health = _get_watcher_health(vault_root)
        pending_approvals = _get_pending_approvals(vault_root)
        recent_logs = _get_recent_logs(vault_root)

        # Build dashboard content
        lines: list[str] = []
        lines.append("# 🤖 FTE System Dashboard\n")
        lines.append(f"**Last Updated:** {now}\n")
        lines.append("> [!tip] Quick Guide\n"
                      "> Drop files in **Watch/** to start the pipeline. "
                      "Check **Pending_Approval/** for items needing your decision. "
                      "Open any approval file and check the **Approve** or **Reject** box.\n")
        lines.append("---\n")

        # Bank Balance (Documents.md §1 requirement)
        lines.append("## 💰 Bank Balance\n")
        lines.append("| Account | Balance | Last Updated |")
        lines.append("|---------|---------|--------------|")
        lines.append("| Business Checking | *update manually* | — |")
        lines.append("| MTD Revenue | *update manually* | — |")
        lines.append("")

        # System Status
        _W_EMOJI = {"running": "🟢", "error": "🔴", "not started": "⚪", "unknown": "⚪"}
        lines.append("## 🔧 System Status\n")
        lines.append("| Component | Status | Last Updated |")
        lines.append("|-----------|--------|--------------|")
        for watcher, info in watcher_health.items():
            w_emoji = _W_EMOJI.get(info['status'], '⚪')
            lines.append(f"| {watcher} | {w_emoji} {info['status']} | {info.get('last_updated', 'N/A')} |")
        lines.append("")

        # Folder Summary
        lines.append("## 📁 Vault Summary\n")
        lines.append("| Folder | Count |")
        lines.append("|--------|-------|")
        for folder, count in counts.items():
            lines.append(f"| {folder} | {count} |")
        lines.append(f"| **Total** | **{sum(counts.values())}** |")
        # Silver Tier: optional folders
        lines.append(f"| Quarantine | {quarantine_count} |")
        lines.append(f"| Briefings | {briefings_count} |")
        lines.append("")

        # Pending Tasks
        inbox_count = counts.get("Inbox", 0)
        needs_action_count = counts.get("Needs_Action", 0)
        plans_count = counts.get("Plans", 0)
        lines.append("## ⏳ Pending Tasks\n")
        lines.append(f"- 📥 **Inbox:** {inbox_count} items awaiting triage")
        lines.append(f"- 📋 **Needs Action:** {needs_action_count} items awaiting planning")
        lines.append(f"- ⚙️ **Active Plans:** {plans_count} plans in progress")
        lines.append("")

        # Awaiting Approval
        _R_EMOJI = {"HIGH": "🟠", "CRITICAL": "🔴"}
        lines.append("## 👤 Awaiting Approval\n")
        if pending_approvals:
            lines.append("| File | Action | Risk | Age |")
            lines.append("|------|--------|------|-----|")
            for approval in pending_approvals:
                r_emoji = _R_EMOJI.get(approval['risk_level'], '⚪')
                lines.append(f"| {approval['filename']} | {approval['action_type']} | {r_emoji} {approval['risk_level']} | {approval['age']} |")
        else:
            lines.append("No pending approval requests.")
        lines.append("")

        # Recent Activity (Documents.md naming convention)
        _S_EMOJI = {"success": "✅", "failure": "❌", "skipped": "⏭️"}
        lines.append("## 📝 Recent Activity\n")
        if recent_logs:
            lines.append("| Time | Agent | Action | Status |")
            lines.append("|------|-------|--------|--------|")
            for log in recent_logs:
                s_emoji = _S_EMOJI.get(log['status'], '⚪')
                lines.append(f"| {log['timestamp']} | {log['agent']} | {log['action']} | {s_emoji} {log['status']} |")
        else:
            lines.append("No recent actions.")
        lines.append("")

        body = "\n".join(lines)

        metadata = {
            "type": "dashboard",
            "last_updated": now,
            "auto_generated": True,
        }

        write_frontmatter_file(vault_root, "Dashboard.md", metadata, body)

        return {"processed": 1, "errors": [], "skipped": 0}

    except Exception as e:
        return {"processed": 0, "errors": [str(e)], "skipped": 0}
