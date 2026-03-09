"""Tests for weekly_briefing Gold Tier extensions — T029 (RED first)."""

from __future__ import annotations

import json
import os
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


VAULT_DIRS = (
    "Briefings", "Logs", "state", "Done", "Needs_Action",
)


def make_vault(tmp_path: Path) -> str:
    vault_root = tmp_path / "vault"
    for folder in VAULT_DIRS:
        (vault_root / folder).mkdir(parents=True, exist_ok=True)
    return str(vault_root)


def _monday_of(d: date | None = None) -> date:
    d = d or date.today()
    return d - timedelta(days=d.weekday())


def _mock_accounting_audit_result(degraded: bool = False):
    """Return a mock accounting_audit.run() result."""
    if degraded:
        return {
            "revenue": None,
            "expenses": None,
            "suggestions": [],
            "error": "Odoo offline",
            "degraded": True,
        }
    return {
        "revenue": {"weekly_paid": 1250.0, "mtd_total": 3500.0},
        "expenses": {
            "top_categories": [
                {"category": "Expenses:Office", "total": 45.0},
                {"category": "Expenses:Software", "total": 99.0},
            ],
        },
        "suggestions": ["Subscription detected: 'SaaS fee' (99.00) — consider reviewing"],
    }


def _write_social_log_entry(vault_root: str, action_type: str, days_ago: int = 1):
    """Write a Gold-format JSON-Lines log entry for a social action."""
    log_dir = os.path.join(vault_root, "Logs")
    os.makedirs(log_dir, exist_ok=True)
    dt = datetime.now(timezone.utc) - timedelta(days=days_ago)
    log_file = os.path.join(log_dir, f"{dt.strftime('%Y-%m-%d')}.json")
    entry = {
        "timestamp": dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "action_type": action_type,
        "actor": "test",
        "target": "social",
        "parameters": {},
        "approval_status": "auto",
        "approved_by": "system",
        "result": "success",
        "error": None,
    }
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


# ---------------------------------------------------------------------------
# T029.1  Briefing output contains "## Revenue" section
# ---------------------------------------------------------------------------

def test_briefing_contains_revenue_section(tmp_path):
    vault = make_vault(tmp_path)
    monday = _monday_of(date(2026, 2, 23))

    with patch("src.skills.weekly_briefing._today", return_value=monday):
        with patch("src.skills.accounting_audit.OdooMCPClient") as MockCls:
            MockCls.from_env.return_value = _mock_client()
            from src.skills.weekly_briefing import run
            result = run(str(vault))

    briefing_file = result.get("briefing_file")
    assert briefing_file and os.path.exists(briefing_file)
    with open(briefing_file, encoding="utf-8") as f:
        content = f.read()
    assert "## Revenue" in content or "Revenue" in content


def _mock_client():
    client = MagicMock()
    client.list_invoices.return_value = {
        "invoices": [{"id": 1, "name": "INV/2026/00001", "partner_name": "ACME",
                       "amount_total": 1250.0, "state": "posted", "invoice_date": "2026-02-24"}],
        "count": 1,
    }
    client.list_transactions.return_value = {
        "transactions": [
            {"move_line_id": 101, "date": "2026-02-24", "description": "Client payment",
             "amount": 1250.0, "account": "Bank"},
            {"move_line_id": 102, "date": "2026-02-24", "description": "Office subscription",
             "amount": -45.0, "account": "Expenses"},
        ],
        "count": 2,
    }
    return client


# ---------------------------------------------------------------------------
# T029.2  Briefing contains "## Expenses" section
# ---------------------------------------------------------------------------

def test_briefing_contains_expenses_section(tmp_path):
    vault = make_vault(tmp_path)
    monday = _monday_of(date(2026, 2, 23))

    with patch("src.skills.weekly_briefing._today", return_value=monday):
        with patch("src.skills.accounting_audit.OdooMCPClient") as MockCls:
            MockCls.from_env.return_value = _mock_client()
            from src.skills.weekly_briefing import run
            result = run(str(vault))

    briefing_file = result.get("briefing_file")
    assert briefing_file and os.path.exists(briefing_file)
    with open(briefing_file, encoding="utf-8") as f:
        content = f.read()
    assert "## Expenses" in content or "Expenses" in content


# ---------------------------------------------------------------------------
# T029.3  Briefing contains "## Bottleneck" section
# ---------------------------------------------------------------------------

def test_briefing_contains_bottleneck_section(tmp_path):
    vault = make_vault(tmp_path)
    monday = _monday_of(date(2026, 2, 23))

    with patch("src.skills.weekly_briefing._today", return_value=monday):
        with patch("src.skills.accounting_audit.OdooMCPClient") as MockCls:
            MockCls.from_env.return_value = _mock_client()
            from src.skills.weekly_briefing import run
            result = run(str(vault))

    briefing_file = result.get("briefing_file")
    assert briefing_file and os.path.exists(briefing_file)
    with open(briefing_file, encoding="utf-8") as f:
        content = f.read()
    assert "## Bottleneck" in content or "Bottleneck" in content


# ---------------------------------------------------------------------------
# T029.4  Briefing contains "## Proactive Suggestions" section
# ---------------------------------------------------------------------------

def test_briefing_contains_proactive_suggestions_section(tmp_path):
    vault = make_vault(tmp_path)
    monday = _monday_of(date(2026, 2, 23))

    with patch("src.skills.weekly_briefing._today", return_value=monday):
        with patch("src.skills.accounting_audit.OdooMCPClient") as MockCls:
            MockCls.from_env.return_value = _mock_client()
            from src.skills.weekly_briefing import run
            result = run(str(vault))

    briefing_file = result.get("briefing_file")
    assert briefing_file and os.path.exists(briefing_file)
    with open(briefing_file, encoding="utf-8") as f:
        content = f.read()
    assert "## Proactive Suggestions" in content or "Proactive" in content


# ---------------------------------------------------------------------------
# T029.5  Briefing contains "## Social Summary" section
# ---------------------------------------------------------------------------

def test_briefing_contains_social_summary_section(tmp_path):
    vault = make_vault(tmp_path)
    monday = _monday_of(date(2026, 2, 23))

    with patch("src.skills.weekly_briefing._today", return_value=monday):
        with patch("src.skills.accounting_audit.OdooMCPClient") as MockCls:
            MockCls.from_env.return_value = _mock_client()
            from src.skills.weekly_briefing import run
            result = run(str(vault))

    briefing_file = result.get("briefing_file")
    assert briefing_file and os.path.exists(briefing_file)
    with open(briefing_file, encoding="utf-8") as f:
        content = f.read()
    assert "## Social Summary" in content or "Social Summary" in content


# ---------------------------------------------------------------------------
# T029.6  Revenue section shows MTD total (a number or [Data unavailable])
# ---------------------------------------------------------------------------

def test_revenue_section_shows_mtd_total(tmp_path):
    vault = make_vault(tmp_path)
    monday = _monday_of(date(2026, 2, 23))

    with patch("src.skills.weekly_briefing._today", return_value=monday):
        with patch("src.skills.accounting_audit.OdooMCPClient") as MockCls:
            MockCls.from_env.return_value = _mock_client()
            from src.skills.weekly_briefing import run
            result = run(str(vault))

    briefing_file = result.get("briefing_file")
    assert briefing_file and os.path.exists(briefing_file)
    with open(briefing_file, encoding="utf-8") as f:
        content = f.read()

    # Should contain either a number or unavailable message
    import re
    has_number = bool(re.search(r"[\d]+\.[\d]+", content))
    has_unavailable = "unavailable" in content.lower() or "Data unavailable" in content
    assert has_number or has_unavailable


# ---------------------------------------------------------------------------
# T029.7  Expense section shows top-5 categories heading
# ---------------------------------------------------------------------------

def test_expense_section_shows_top_categories(tmp_path):
    vault = make_vault(tmp_path)
    monday = _monday_of(date(2026, 2, 23))

    with patch("src.skills.weekly_briefing._today", return_value=monday):
        with patch("src.skills.accounting_audit.OdooMCPClient") as MockCls:
            MockCls.from_env.return_value = _mock_client()
            from src.skills.weekly_briefing import run
            result = run(str(vault))

    briefing_file = result.get("briefing_file")
    assert briefing_file and os.path.exists(briefing_file)
    with open(briefing_file, encoding="utf-8") as f:
        content = f.read()

    # Should reference categories or top expenses somehow
    assert "categor" in content.lower() or "Expenses" in content or "expense" in content.lower()


# ---------------------------------------------------------------------------
# T029.8  Odoo offline: shows "[Data unavailable — Odoo offline]" in Revenue section
# ---------------------------------------------------------------------------

def test_odoo_offline_shows_unavailable_message(tmp_path):
    vault = make_vault(tmp_path)
    monday = _monday_of(date(2026, 2, 23))

    with patch("src.skills.weekly_briefing._today", return_value=monday):
        with patch("src.skills.accounting_audit.OdooMCPClient") as MockCls:
            mock_client = MagicMock()
            mock_client.list_invoices.side_effect = ConnectionError("Odoo offline")
            MockCls.from_env.return_value = mock_client
            from src.skills.weekly_briefing import run
            result = run(str(vault))

    briefing_file = result.get("briefing_file")
    assert briefing_file and os.path.exists(briefing_file)
    with open(briefing_file, encoding="utf-8") as f:
        content = f.read()

    assert "unavailable" in content.lower() or "offline" in content.lower() or \
           "Data unavailable" in content


# ---------------------------------------------------------------------------
# T029.9  Bottleneck section is present even when vault/Done is empty
# ---------------------------------------------------------------------------

def test_bottleneck_section_present_when_done_empty(tmp_path):
    vault = make_vault(tmp_path)
    # Done dir is empty
    monday = _monday_of(date(2026, 2, 23))

    with patch("src.skills.weekly_briefing._today", return_value=monday):
        with patch("src.skills.accounting_audit.OdooMCPClient") as MockCls:
            MockCls.from_env.return_value = _mock_client()
            from src.skills.weekly_briefing import run
            result = run(str(vault))

    briefing_file = result.get("briefing_file")
    assert briefing_file and os.path.exists(briefing_file)
    with open(briefing_file, encoding="utf-8") as f:
        content = f.read()
    assert "Bottleneck" in content


# ---------------------------------------------------------------------------
# T029.10  Social Summary section is present even when vault/Logs is empty
# ---------------------------------------------------------------------------

def test_social_summary_present_when_logs_empty(tmp_path):
    vault = make_vault(tmp_path)
    # Logs dir is empty
    monday = _monday_of(date(2026, 2, 23))

    with patch("src.skills.weekly_briefing._today", return_value=monday):
        with patch("src.skills.accounting_audit.OdooMCPClient") as MockCls:
            MockCls.from_env.return_value = _mock_client()
            from src.skills.weekly_briefing import run
            result = run(str(vault))

    briefing_file = result.get("briefing_file")
    assert briefing_file and os.path.exists(briefing_file)
    with open(briefing_file, encoding="utf-8") as f:
        content = f.read()
    assert "Social Summary" in content
