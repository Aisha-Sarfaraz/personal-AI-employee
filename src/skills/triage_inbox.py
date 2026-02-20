"""Inbox Interpreter skill — classifies items by type and priority."""

import os
from typing import Any

from src.core.vault import list_folder, read_frontmatter_file, write_frontmatter_file, move_file
from src.core.audit_logger import log_action

# Keyword scoring dictionaries
TYPE_KEYWORDS: dict[str, list[str]] = {
    "financial": ["invoice", "payment", "$", "expense", "budget", "refund", "receipt", "billing", "cost", "price"],
    "communication": ["email", "message", "reply", "letter", "correspondence", "memo", "notification"],
    "task": ["todo", "assign", "deadline", "task", "action item", "deliverable", "milestone"],
    "document": ["report", "summary", "pdf", "analysis", "document", "review", "specification"],
}

PRIORITY_KEYWORDS: dict[str, list[str]] = {
    "CRITICAL": ["urgent", "emergency", "critical", "immediately", "asap now"],
    "HIGH": ["important", "deadline", "asap", "priority", "high priority"],
    "LOW": ["info", "fyi", "optional", "informational", "low priority", "no rush"],
}

TYPE_EMOJI: dict[str, str] = {
    "financial": "💰", "communication": "📧", "task": "✅",
    "document": "📄", "general": "📌", "unknown": "❓",
}

PRIORITY_EMOJI: dict[str, str] = {
    "CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🟢",
}


def _classify_type(content: str, current_type: str = "") -> str:
    """Classify item type by keyword scoring."""
    if current_type == "unknown":
        return "unknown"

    content_lower = content.lower()
    scores: dict[str, int] = {}

    for item_type, keywords in TYPE_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw.lower() in content_lower)
        if score > 0:
            scores[item_type] = score

    if not scores:
        return "general"
    return max(scores, key=scores.get)  # type: ignore[arg-type]


def _classify_priority(content: str) -> str:
    """Classify item priority by keyword scoring."""
    content_lower = content.lower()

    for priority, keywords in PRIORITY_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in content_lower:
                return priority

    return "MEDIUM"


def run(vault_root: str) -> dict[str, Any]:
    """Scan /Inbox, classify each item, move to /Needs_Action.

    Args:
        vault_root: Absolute path to the vault directory.

    Returns:
        Dict with processed count, errors list, and skipped count.
    """
    processed = 0
    errors: list[str] = []
    skipped = 0

    inbox_files = list_folder(vault_root, "Inbox")

    for filename in inbox_files:
        try:
            filepath = os.path.join("Inbox", filename)
            metadata, body = read_frontmatter_file(vault_root, filepath)

            current_type = metadata.get("type", "")

            # Skip unknown type items (binary/malformed)
            if current_type == "unknown":
                skipped += 1
                continue

            item_type = _classify_type(body, current_type)
            priority = _classify_priority(body)

            metadata["type"] = item_type
            metadata["priority"] = priority
            metadata["status"] = "triaged"

            # Append triage classification section
            t_emoji = TYPE_EMOJI.get(item_type, "📌")
            p_emoji = PRIORITY_EMOJI.get(priority, "⚪")
            body = body + (
                f"\n\n---\n\n"
                f"## 🔍 Triage Classification\n\n"
                f"> [!success] Classified\n"
                f"> **Type:** {t_emoji} {item_type.capitalize()}\n"
                f"> **Priority:** {p_emoji} {priority}\n"
                f"> **Status:** ✅ Triaged\n\n"
                f"> [!tip] Next Step\n"
                f"> A plan will be generated automatically in **Plans/**.\n"
                f"> If approval is needed, a request will appear in **Pending_Approval/**.\n"
            )

            # Write updated frontmatter back
            write_frontmatter_file(vault_root, filepath, metadata, body)

            # Move to Needs_Action
            dest_path = os.path.join("Needs_Action", filename)
            move_file(vault_root, filepath, dest_path)

            log_action(
                vault_root=vault_root,
                agent="triage_inbox",
                action=f"triaged {filename}",
                risk_tier="LOW",
                status="success",
                details=f"Classified as type={item_type}, priority={priority}",
                related_item=metadata.get("id", filename),
            )

            processed += 1

        except Exception as e:
            errors.append(f"Error processing {filename}: {str(e)}")

    return {"processed": processed, "errors": errors, "skipped": skipped}
