"""Lead detection skill — upgrades qualifying Needs_Action items to type:lead."""

from __future__ import annotations

import os
from typing import Any

from src.core.audit_logger import log_action
from src.core.vault import list_folder, read_frontmatter_file, write_frontmatter_file

_DEFAULT_KEYWORDS = [
    "interested",
    "pricing",
    "price",
    "quote",
    "buy",
    "purchase",
    "contract",
    "consulting",
    "package",
    "demo",
    "trial",
]

_LEAD_THRESHOLD = 2  # minimum keyword matches to qualify as lead
_MAX_SCORE = 10


def run(vault_root: str, keywords: list[str] | None = None) -> dict[str, Any]:
    """Scan vault/Needs_Action/ and upgrade qualifying items to type:lead.

    Args:
        vault_root: Path to vault root directory.
        keywords: Override default keyword list from settings.yaml.
                  If None, uses _DEFAULT_KEYWORDS.

    Returns:
        Dict with keys: processed, leads_detected, errors, skipped.
    """
    kws = [k.lower() for k in (keywords or _DEFAULT_KEYWORDS)]
    needs_action_dir = "Needs_Action"

    files = list_folder(vault_root, needs_action_dir)
    processed = 0
    leads_detected = 0
    errors = 0
    skipped = 0

    for filename in files:
        relative_path = f"{needs_action_dir}/{filename}"
        try:
            metadata, body = read_frontmatter_file(vault_root, relative_path)
        except Exception:
            errors += 1
            continue

        # Skip items already classified as leads
        if metadata.get("type") == "lead":
            skipped += 1
            continue

        processed += 1
        text = (body + " " + metadata.get("subject", "") + " " + str(metadata.get("tags", ""))).lower()

        # Count keyword matches (unique keywords only, cap at MAX_SCORE)
        matched = [kw for kw in kws if kw in text]
        score = min(len(matched), _MAX_SCORE)

        # Bonus: gmail source adds 2 points
        if str(metadata.get("source", "")).lower() == "gmail":
            score += 2

        # Bonus: already CRITICAL priority adds 1 point
        if str(metadata.get("priority", "")).upper() == "CRITICAL":
            score += 1

        if score < _LEAD_THRESHOLD:
            continue

        # Upgrade item in-place
        metadata["type"] = "lead"
        metadata["priority"] = "CRITICAL"
        metadata["lead_score"] = score

        try:
            write_frontmatter_file(vault_root, relative_path, metadata, body)
        except Exception:
            errors += 1
            continue

        leads_detected += 1

        # Write HIGH audit entry
        try:
            log_action(
                vault_root=vault_root,
                agent="detect_lead",
                action=f"lead_detected: {metadata.get('id', filename)}",
                risk_tier="HIGH",
                status="success",
                details=f"score={score} keywords={matched[:5]}",
            )
        except Exception:
            pass  # audit failure never blocks the skill

    return {
        "processed": processed,
        "leads_detected": leads_detected,
        "errors": errors,
        "skipped": skipped,
    }
