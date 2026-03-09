"""Tests for generate_invoice skill — Gold Tier T024 (RED first)."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml


VAULT_DIRS = (
    "Needs_Action", "Pending_Approval", "state", "Logs", "Inbox",
)


def make_vault(tmp_path: Path) -> str:
    vault_root = tmp_path / "vault"
    for folder in VAULT_DIRS:
        (vault_root / folder).mkdir(parents=True, exist_ok=True)
    return str(vault_root)


def write_invoice_request(vault_root: str, filename: str = "WHATSAPP_001.md",
                           partner: str = "ACME Corp", amount: float = 500.0,
                           description: str = "Consulting services",
                           extra_meta: dict | None = None) -> str:
    """Write an invoice_request item to vault/Needs_Action/."""
    path = os.path.join(vault_root, "Needs_Action", filename)
    meta = {
        "id": filename,
        "type": "whatsapp",
        "intent": "invoice_request",
        "status": "triaged",
        "partner": partner,
        "amount": amount,
        "description": description,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    if extra_meta:
        meta.update(extra_meta)
    front = yaml.dump(meta, default_flow_style=False)
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"---\n{front}---\n\nPlease create an invoice for {partner}.\n")
    return path


# ---------------------------------------------------------------------------
# T024.1  run(vault_root) returns dict with 'created' or 'skipped' key
# ---------------------------------------------------------------------------

def test_run_returns_dict_with_created_or_skipped(tmp_path):
    vault = make_vault(tmp_path)
    write_invoice_request(vault)

    from src.skills.generate_invoice import run
    result = run(vault)

    assert isinstance(result, dict)
    assert "created" in result or "skipped" in result


# ---------------------------------------------------------------------------
# T024.2  Creates vault/Pending_Approval/INVOICE_*.md when intent:invoice_request exists
# ---------------------------------------------------------------------------

def test_creates_approval_file_for_invoice_request(tmp_path):
    vault = make_vault(tmp_path)
    write_invoice_request(vault)

    from src.skills.generate_invoice import run
    result = run(vault)

    assert result.get("created", 0) >= 1
    approval_file = result.get("approval_file")
    assert approval_file is not None
    assert os.path.exists(approval_file)
    assert "INVOICE_" in os.path.basename(approval_file)


# ---------------------------------------------------------------------------
# T024.3  Approval file has partner, amount, description, risk_level: HIGH, requires_approval: true
# ---------------------------------------------------------------------------

def test_approval_file_has_required_frontmatter(tmp_path):
    vault = make_vault(tmp_path)
    write_invoice_request(vault, partner="Test Corp", amount=1200.0,
                          description="Web development")

    from src.skills.generate_invoice import run
    result = run(vault)

    approval_file = result.get("approval_file")
    assert approval_file is not None
    with open(approval_file, encoding="utf-8") as f:
        content = f.read()

    assert "partner" in content
    assert "amount" in content
    assert "description" in content
    assert "risk_level: HIGH" in content
    assert "requires_approval: true" in content


# ---------------------------------------------------------------------------
# T024.4  Unparseable partner sets partner field to [NEEDS HUMAN INPUT]
# ---------------------------------------------------------------------------

def test_unparseable_partner_sets_needs_human_input(tmp_path):
    vault = make_vault(tmp_path)
    # Write item with no partner field in frontmatter, no partner in body
    path = os.path.join(vault, "Needs_Action", "NOINPUT_001.md")
    meta = {
        "id": "NOINPUT_001.md",
        "intent": "invoice_request",
        "status": "triaged",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    front = yaml.dump(meta, default_flow_style=False)
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"---\n{front}---\n\nSome unstructured text without partner info.\n")

    from src.skills.generate_invoice import run
    result = run(vault)

    approval_file = result.get("approval_file")
    if approval_file and os.path.exists(approval_file):
        with open(approval_file, encoding="utf-8") as f:
            content = f.read()
        assert "NEEDS HUMAN INPUT" in content


# ---------------------------------------------------------------------------
# T024.5  Idempotency: same item_id not processed twice
# ---------------------------------------------------------------------------

def test_idempotency_same_item_not_processed_twice(tmp_path):
    vault = make_vault(tmp_path)
    write_invoice_request(vault, filename="IDEM_001.md")

    from src.skills.generate_invoice import run

    result1 = run(vault)
    result2 = run(vault)

    assert result1.get("created", 0) == 1
    # Second call should skip the already-processed item
    assert result2.get("created", 0) == 0 or result2.get("skipped", 0) >= 1


# ---------------------------------------------------------------------------
# T024.6  dev_mode=True: no real Odoo HTTP call
# ---------------------------------------------------------------------------

def test_dev_mode_no_real_odoo_call(tmp_path, monkeypatch):
    vault = make_vault(tmp_path)
    write_invoice_request(vault)
    monkeypatch.setenv("DEV_MODE", "true")

    # Patch requests.post to ensure it's never called
    with patch("requests.post") as mock_post:
        from src.skills.generate_invoice import run
        run(vault)
        mock_post.assert_not_called()


# ---------------------------------------------------------------------------
# T024.7  Returns {created: 1, approval_file: path} on success
# ---------------------------------------------------------------------------

def test_returns_created_and_approval_file_on_success(tmp_path):
    vault = make_vault(tmp_path)
    write_invoice_request(vault, partner="Beta LLC", amount=750.0,
                          description="Consulting")

    from src.skills.generate_invoice import run
    result = run(vault)

    assert result.get("created") == 1
    assert "approval_file" in result
    assert result["approval_file"] is not None


# ---------------------------------------------------------------------------
# T024.8  Items without intent:invoice_request are skipped
# ---------------------------------------------------------------------------

def test_items_without_invoice_intent_are_skipped(tmp_path):
    vault = make_vault(tmp_path)
    # Write an item with a different intent
    path = os.path.join(vault, "Needs_Action", "OTHER_001.md")
    meta = {
        "id": "OTHER_001.md",
        "intent": "lead_follow_up",
        "status": "triaged",
    }
    front = yaml.dump(meta, default_flow_style=False)
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"---\n{front}---\n\nNo invoice needed.\n")

    from src.skills.generate_invoice import run
    result = run(vault)

    assert result.get("created", 0) == 0
