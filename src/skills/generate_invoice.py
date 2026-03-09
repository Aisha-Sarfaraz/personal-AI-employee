"""Generate Invoice skill — Gold Tier T025.

Scans vault/Needs_Action/ for items with intent: invoice_request,
calls OdooMCPClient.create_invoice (HITL gate), and marks processed.
"""

from __future__ import annotations

import glob
import os
import re
from datetime import datetime, timezone
from typing import Any

import yaml

from src.core.audit_logger import log as audit_log
from src.core.idempotency import check_and_store, generate_key
from src.mcp_servers.odoo_mcp.client import OdooMCPClient


def _parse_frontmatter(content: str) -> tuple[dict[str, Any], str]:
    """Parse YAML frontmatter from markdown content."""
    if not content.startswith("---"):
        return {}, content
    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}, content
    try:
        meta = yaml.safe_load(parts[1]) or {}
    except yaml.YAMLError:
        meta = {}
    body = parts[2].strip() if len(parts) > 2 else ""
    return meta, body


def _extract_partner(meta: dict[str, Any], body: str) -> str:
    """Extract partner from frontmatter or body text."""
    # Try frontmatter first
    partner = meta.get("partner") or meta.get("client") or meta.get("customer")
    if partner and str(partner).strip():
        return str(partner).strip()

    # Regex fallback in body — require a colon so "partner info." doesn't match
    patterns = [
        r"partner\s*:\s*([A-Za-z][^\n,\.]{2,50})",
        r"invoice\s+(?:for|to)\s+([A-Za-z][^\n,\.]{2,50})",
        r"client\s*:\s*([A-Za-z][^\n,\.]{2,50})",
    ]
    for pattern in patterns:
        match = re.search(pattern, body, re.IGNORECASE)
        if match:
            return match.group(1).strip()

    return "[NEEDS HUMAN INPUT]"


def _extract_amount(meta: dict[str, Any], body: str) -> float:
    """Extract amount from frontmatter or body text."""
    # Try frontmatter first
    raw_amount = meta.get("amount") or meta.get("total") or meta.get("price")
    if raw_amount is not None:
        try:
            return float(raw_amount)
        except (ValueError, TypeError):
            pass

    # Regex fallback in body
    match = re.search(r"\$?\s*([\d,]+\.?\d*)", body)
    if match:
        try:
            return float(match.group(1).replace(",", ""))
        except ValueError:
            pass

    return 0.0


def _extract_description(meta: dict[str, Any], body: str) -> str:
    """Extract description from frontmatter or body text."""
    desc = meta.get("description") or meta.get("service") or meta.get("item")
    if desc and str(desc).strip():
        return str(desc).strip()

    # Use first 100 chars of body as fallback
    if body:
        return body[:100].strip().replace("\n", " ")

    return "Invoice request"


def run(vault_root: str) -> dict[str, Any]:
    """Scan vault/Needs_Action/ for invoice_request items and create approval files.

    Args:
        vault_root: Path to vault root directory.

    Returns:
        Dict with keys: created, skipped, approval_file (last created), errors.
    """
    dev_mode = os.environ.get("DEV_MODE", "").lower() in ("true", "1", "yes")
    needs_action_dir = os.path.join(vault_root, "Needs_Action")

    if not os.path.isdir(needs_action_dir):
        return {"created": 0, "skipped": 0, "approval_file": None, "errors": []}

    created = 0
    skipped = 0
    last_approval_file = None
    errors = []

    for md_path in glob.glob(os.path.join(needs_action_dir, "*.md")):
        try:
            with open(md_path, encoding="utf-8") as f:
                content = f.read()
        except OSError:
            continue

        meta, body = _parse_frontmatter(content)

        # Only process invoice_request items
        if meta.get("intent") != "invoice_request":
            continue

        item_id = str(meta.get("id", os.path.basename(md_path)))

        # Idempotency check
        idem_key = generate_key(
            agent="generate_invoice",
            action="create_invoice",
            details={"item_id": item_id},
        )
        found, cached = check_and_store(vault_root, idem_key, {"item_id": item_id})
        if found:
            skipped += 1
            continue

        # Parse fields
        partner = _extract_partner(meta, body)
        amount = _extract_amount(meta, body)
        description = _extract_description(meta, body)

        # Use dev_mode if unset in meta or environment
        client = OdooMCPClient.from_env(vault_root=vault_root, dev_mode=dev_mode)

        try:
            # For [NEEDS HUMAN INPUT] or zero amount, still create approval file
            # but use safe defaults
            safe_partner = partner if partner != "[NEEDS HUMAN INPUT]" else "Unknown"
            safe_amount = amount if amount > 0 else 1.0
            result = client.create_invoice(
                partner=safe_partner,
                amount=safe_amount,
                description=description,
            )
            approval_file = result.get("approval_file")

            # If partner was [NEEDS HUMAN INPUT], patch the approval file
            if partner == "[NEEDS HUMAN INPUT]" and approval_file and os.path.exists(approval_file):
                with open(approval_file, encoding="utf-8") as f:
                    file_content = f.read()
                file_content = file_content.replace(
                    f"partner: {safe_partner}", "partner: [NEEDS HUMAN INPUT]"
                )
                with open(approval_file, "w", encoding="utf-8") as f:
                    f.write(file_content)

            last_approval_file = approval_file
            created += 1

            # Audit log
            try:
                audit_log(
                    vault_root=vault_root,
                    action_type="generate_invoice",
                    actor="generate_invoice",
                    target=approval_file or item_id,
                    parameters={
                        "item_id": item_id,
                        "partner": partner,
                        "amount": amount,
                        "dev_mode": dev_mode,
                    },
                    approval_status="pending",
                    approved_by=None,
                    result="success",
                )
            except Exception:
                pass

        except Exception as exc:
            errors.append(str(exc))
            # If idempotency key was stored but invoice failed, we skip storing
            # (key was already stored above, so item won't be retried automatically)

    result_dict: dict[str, Any] = {
        "created": created,
        "skipped": skipped,
        "approval_file": last_approval_file,
        "errors": errors,
    }
    if dev_mode:
        result_dict["simulated"] = created

    return result_dict
