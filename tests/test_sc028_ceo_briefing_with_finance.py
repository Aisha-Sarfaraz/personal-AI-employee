"""SC-028: CEO Briefing with Finance integration test — Gold Tier T031."""

from __future__ import annotations

import json
import os
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


VAULT_DIRS = ("Briefings", "Logs", "state", "Done", "Needs_Action",
              os.path.join("Watch", "finance_mock"))


def make_vault(tmp_path: Path) -> str:
    vault_root = tmp_path / "vault"
    for folder in VAULT_DIRS:
        (vault_root / folder).mkdir(parents=True, exist_ok=True)
    return str(vault_root)


def _monday_of(d: date | None = None) -> date:
    d = d or date.today()
    return d - timedelta(days=d.weekday())


def _mock_odoo_client():
    """Build a mock OdooMCPClient that returns useful data."""
    client = MagicMock()
    client.list_invoices.return_value = {
        "invoices": [
            {"id": 1, "name": "INV/2026/00001", "partner_name": "ACME Corp",
             "amount_total": 1250.0, "state": "posted", "invoice_date": "2026-02-24"},
        ],
        "count": 1,
    }
    client.list_transactions.return_value = {
        "transactions": [
            {"move_line_id": 101, "date": "2026-02-24",
             "description": "Client payment", "amount": 1250.0, "account": "Bank"},
            {"move_line_id": 102, "date": "2026-02-24",
             "description": "SaaS subscription fee", "amount": -99.0,
             "account": "Expenses:Software"},
        ],
        "count": 2,
    }
    return client


class TestSC028CeoBriefingWithFinance:
    """SC-028: CEO Briefing includes all 5 new Gold sections with financial data."""

    def test_sc028_briefing_created_on_monday(self, tmp_path):
        vault = make_vault(tmp_path)
        monday = _monday_of(date(2026, 2, 23))

        with patch("src.skills.weekly_briefing._today", return_value=monday):
            with patch("src.skills.accounting_audit.OdooMCPClient") as MockCls:
                MockCls.from_env.return_value = _mock_odoo_client()
                from src.skills.weekly_briefing import run
                result = run(str(vault))

        assert result.get("skipped", 1) == 0
        assert result.get("briefing_file") is not None
        assert os.path.exists(result["briefing_file"])

    def test_sc028_briefing_has_all_5_gold_sections(self, tmp_path):
        vault = make_vault(tmp_path)
        monday = _monday_of(date(2026, 2, 23))

        with patch("src.skills.weekly_briefing._today", return_value=monday):
            with patch("src.skills.accounting_audit.OdooMCPClient") as MockCls:
                MockCls.from_env.return_value = _mock_odoo_client()
                from src.skills.weekly_briefing import run
                result = run(str(vault))

        with open(result["briefing_file"], encoding="utf-8") as f:
            content = f.read()

        for section in ("Revenue", "Expenses", "Bottleneck", "Proactive Suggestions", "Social Summary"):
            assert section in content, f"Missing section: {section}"

    def test_sc028_briefing_has_mtd_total(self, tmp_path):
        vault = make_vault(tmp_path)
        monday = _monday_of(date(2026, 2, 23))

        with patch("src.skills.weekly_briefing._today", return_value=monday):
            with patch("src.skills.accounting_audit.OdooMCPClient") as MockCls:
                MockCls.from_env.return_value = _mock_odoo_client()
                from src.skills.weekly_briefing import run
                result = run(str(vault))

        with open(result["briefing_file"], encoding="utf-8") as f:
            content = f.read()

        # MTD total should be present in Revenue section
        assert "MTD" in content

    def test_sc028_odoo_offline_briefing_still_created(self, tmp_path):
        """Scenario 2: Odoo offline — briefing is still written with degraded sections."""
        vault = make_vault(tmp_path)
        monday = _monday_of(date(2026, 2, 23))

        with patch("src.skills.weekly_briefing._today", return_value=monday):
            with patch("src.skills.accounting_audit.OdooMCPClient") as MockCls:
                mock_client = MagicMock()
                mock_client.list_invoices.side_effect = ConnectionError("Odoo offline")
                MockCls.from_env.return_value = mock_client
                from src.skills.weekly_briefing import run
                result = run(str(vault))

        # Briefing should still be created
        assert result.get("briefing_file") is not None
        assert os.path.exists(result["briefing_file"])

    def test_sc028_odoo_offline_shows_unavailable_in_revenue(self, tmp_path):
        vault = make_vault(tmp_path)
        monday = _monday_of(date(2026, 2, 23))

        with patch("src.skills.weekly_briefing._today", return_value=monday):
            with patch("src.skills.accounting_audit.OdooMCPClient") as MockCls:
                mock_client = MagicMock()
                mock_client.list_invoices.side_effect = ConnectionError("Odoo offline")
                MockCls.from_env.return_value = mock_client
                from src.skills.weekly_briefing import run
                result = run(str(vault))

        with open(result["briefing_file"], encoding="utf-8") as f:
            content = f.read()

        assert "unavailable" in content.lower() or "offline" in content.lower()

    def test_sc028_briefing_has_existing_silver_sections(self, tmp_path):
        """Verify existing Silver sections are not broken."""
        vault = make_vault(tmp_path)
        monday = _monday_of(date(2026, 2, 23))

        with patch("src.skills.weekly_briefing._today", return_value=monday):
            with patch("src.skills.accounting_audit.OdooMCPClient") as MockCls:
                MockCls.from_env.return_value = _mock_odoo_client()
                from src.skills.weekly_briefing import run
                result = run(str(vault))

        with open(result["briefing_file"], encoding="utf-8") as f:
            content = f.read()

        # Silver sections should still be there
        silver_sections = ["Date Range", "Items by Channel", "Leads Detected",
                           "Emails Sent", "LinkedIn Activity", "Plans Summary",
                           "Approvals", "Quarantine", "Next Week"]
        for section in silver_sections:
            assert section in content, f"Silver section missing: {section}"

    def test_sc028_social_summary_with_log_entries(self, tmp_path):
        """Social Summary should count social actions from JSON logs."""
        vault = make_vault(tmp_path)
        # Write a social log entry
        log_dir = os.path.join(str(vault), "Logs")
        dt = datetime.now(timezone.utc) - timedelta(days=1)
        log_file = os.path.join(log_dir, f"{dt.strftime('%Y-%m-%d')}.json")
        entry = {
            "timestamp": dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "action_type": "generate_linkedin_post",
            "actor": "linkedin_post",
            "target": "social",
            "parameters": {},
            "approval_status": "auto",
            "approved_by": "system",
            "result": "success",
            "error": None,
        }
        with open(log_file, "w", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

        monday = _monday_of(date(2026, 2, 23))

        with patch("src.skills.weekly_briefing._today", return_value=monday):
            with patch("src.skills.accounting_audit.OdooMCPClient") as MockCls:
                MockCls.from_env.return_value = _mock_odoo_client()
                from src.skills.weekly_briefing import run
                result = run(str(vault))

        with open(result["briefing_file"], encoding="utf-8") as f:
            content = f.read()

        assert "Social Summary" in content
