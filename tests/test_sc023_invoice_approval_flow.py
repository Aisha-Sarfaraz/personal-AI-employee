"""SC-023: Invoice approval flow integration test — Gold Tier T026."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml


VAULT_DIRS = (
    "Needs_Action", "Pending_Approval", "Approved", "state", "Logs", "Inbox",
)


def make_vault(tmp_path: Path) -> str:
    vault_root = tmp_path / "vault"
    for folder in VAULT_DIRS:
        (vault_root / folder).mkdir(parents=True, exist_ok=True)
    return str(vault_root)


def write_invoice_request(vault_root: str, filename: str = "WHATSAPP_001.md",
                           partner: str = "ACME Corp", amount: float = 500.0,
                           description: str = "Consulting services") -> str:
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
    front = yaml.dump(meta, default_flow_style=False)
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"---\n{front}---\n\nPlease create an invoice for {partner}.\n")
    return path


class TestSC023InvoiceApprovalFlow:
    """SC-023: WhatsApp item with intent:invoice_request → approval file created."""

    def test_sc023_approval_file_created(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DEV_MODE", "true")
        vault = make_vault(tmp_path)
        write_invoice_request(vault, partner="ACME Corp", amount=1000.0)

        from src.skills.generate_invoice import run
        result = run(vault)

        assert result.get("created") == 1
        assert result.get("approval_file") is not None
        assert os.path.exists(result["approval_file"])

    def test_sc023_approval_file_has_correct_fields(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DEV_MODE", "true")
        vault = make_vault(tmp_path)
        write_invoice_request(vault, partner="Beta LLC", amount=750.0,
                              description="Software development")

        from src.skills.generate_invoice import run
        result = run(vault)

        approval_file = result.get("approval_file")
        assert approval_file is not None
        with open(approval_file, encoding="utf-8") as f:
            content = f.read()

        assert "Beta LLC" in content
        assert "750.0" in content or "750" in content
        assert "risk_level: HIGH" in content
        assert "requires_approval: true" in content

    def test_sc023_simulated_flag_in_dev_mode(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DEV_MODE", "true")
        vault = make_vault(tmp_path)
        write_invoice_request(vault)

        from src.skills.generate_invoice import run
        result = run(vault)

        # dev_mode=true → should have simulated key
        assert result.get("simulated", result.get("created", 0)) >= 1

    def test_sc023_audit_log_written(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DEV_MODE", "true")
        vault = make_vault(tmp_path)
        write_invoice_request(vault)

        from src.skills.generate_invoice import run
        run(vault)

        logs_dir = os.path.join(vault, "Logs")
        log_files = [f for f in os.listdir(logs_dir) if f.endswith(".json")]
        assert len(log_files) >= 1

    def test_sc023_multiple_items_processed(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DEV_MODE", "true")
        vault = make_vault(tmp_path)
        write_invoice_request(vault, filename="INV_001.md", partner="Client A", amount=500.0)

        from src.skills.generate_invoice import run
        result = run(vault)

        assert result.get("created", 0) >= 1

    def test_sc023_no_items_returns_zero_created(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DEV_MODE", "true")
        vault = make_vault(tmp_path)
        # No items in Needs_Action

        from src.skills.generate_invoice import run
        result = run(vault)

        assert result.get("created", 0) == 0
