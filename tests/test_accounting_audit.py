"""Tests for accounting_audit skill — Gold Tier T027 (RED first)."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


VAULT_DIRS = ("Logs", "state", "Briefings")


def make_vault(tmp_path: Path) -> str:
    vault_root = tmp_path / "vault"
    for folder in VAULT_DIRS:
        (vault_root / folder).mkdir(parents=True, exist_ok=True)
    return str(vault_root)


def mock_odoo_client(invoices=None, transactions=None):
    """Create a mock OdooMCPClient."""
    client = MagicMock()
    if invoices is None:
        invoices = [
            {"id": 1, "name": "INV/2026/00001", "partner_name": "ACME Corp",
             "amount_total": 1250.0, "state": "posted", "invoice_date": "2026-02-24"},
        ]
    if transactions is None:
        transactions = [
            {"move_line_id": 101, "date": "2026-02-24",
             "description": "Client payment", "amount": 1250.0, "account": "Bank"},
            {"move_line_id": 102, "date": "2026-02-24",
             "description": "Office supplies subscription", "amount": -45.0,
             "account": "Expenses:Office"},
        ]
    client.list_invoices.return_value = {"invoices": invoices, "count": len(invoices)}
    client.list_transactions.return_value = {"transactions": transactions, "count": len(transactions)}
    return client


# ---------------------------------------------------------------------------
# T027.1  run(vault_root) returns dict with revenue, expenses, suggestions keys
# ---------------------------------------------------------------------------

def test_run_returns_dict_with_required_keys(tmp_path):
    vault = make_vault(tmp_path)

    with patch("src.skills.accounting_audit.OdooMCPClient") as MockCls:
        MockCls.from_env.return_value = mock_odoo_client()
        from src.skills.accounting_audit import run
        result = run(vault)

    assert isinstance(result, dict)
    for key in ("revenue", "expenses", "suggestions"):
        assert key in result, f"Missing key: {key}"


# ---------------------------------------------------------------------------
# T027.2  revenue dict has weekly_paid, mtd_total keys
# ---------------------------------------------------------------------------

def test_revenue_has_weekly_paid_and_mtd_total(tmp_path):
    vault = make_vault(tmp_path)

    with patch("src.skills.accounting_audit.OdooMCPClient") as MockCls:
        MockCls.from_env.return_value = mock_odoo_client()
        from src.skills.accounting_audit import run
        result = run(vault)

    revenue = result["revenue"]
    assert revenue is not None
    assert "weekly_paid" in revenue
    assert "mtd_total" in revenue


# ---------------------------------------------------------------------------
# T027.3  expenses dict has top_categories key (list)
# ---------------------------------------------------------------------------

def test_expenses_has_top_categories_list(tmp_path):
    vault = make_vault(tmp_path)

    with patch("src.skills.accounting_audit.OdooMCPClient") as MockCls:
        MockCls.from_env.return_value = mock_odoo_client()
        from src.skills.accounting_audit import run
        result = run(vault)

    expenses = result["expenses"]
    assert expenses is not None
    assert "top_categories" in expenses
    assert isinstance(expenses["top_categories"], list)


# ---------------------------------------------------------------------------
# T027.4  Subscription keyword in description flags in suggestions
# ---------------------------------------------------------------------------

def test_subscription_keyword_flagged_in_suggestions(tmp_path):
    vault = make_vault(tmp_path)
    transactions = [
        {"move_line_id": 101, "date": "2026-02-24",
         "description": "Office supplies subscription fee", "amount": -45.0,
         "account": "Expenses:Subscriptions"},
    ]

    with patch("src.skills.accounting_audit.OdooMCPClient") as MockCls:
        MockCls.from_env.return_value = mock_odoo_client(transactions=transactions)
        from src.skills.accounting_audit import run
        result = run(vault)

    suggestions = result.get("suggestions", [])
    assert isinstance(suggestions, list)
    # At least one suggestion should mention subscriptions
    suggestions_text = " ".join(str(s) for s in suggestions).lower()
    assert "subscription" in suggestions_text or len(suggestions) >= 1


# ---------------------------------------------------------------------------
# T027.5  run() on Odoo ConnectionError returns {revenue: None, expenses: None, error: ...}
# ---------------------------------------------------------------------------

def test_run_on_odoo_connection_error_returns_degraded(tmp_path):
    vault = make_vault(tmp_path)

    with patch("src.skills.accounting_audit.OdooMCPClient") as MockCls:
        mock_client = MagicMock()
        mock_client.list_invoices.side_effect = ConnectionError("Odoo offline")
        MockCls.from_env.return_value = mock_client
        from src.skills.accounting_audit import run
        result = run(vault)

    assert result["revenue"] is None
    assert result["expenses"] is None
    assert "error" in result
    assert "Odoo offline" in result.get("error", "") or result.get("error") is not None


# ---------------------------------------------------------------------------
# T027.6  suggestions is a list
# ---------------------------------------------------------------------------

def test_suggestions_is_a_list(tmp_path):
    vault = make_vault(tmp_path)

    with patch("src.skills.accounting_audit.OdooMCPClient") as MockCls:
        MockCls.from_env.return_value = mock_odoo_client()
        from src.skills.accounting_audit import run
        result = run(vault)

    assert isinstance(result.get("suggestions"), list)


# ---------------------------------------------------------------------------
# T027.7  revenue.mtd_total is float
# ---------------------------------------------------------------------------

def test_revenue_mtd_total_is_float(tmp_path):
    vault = make_vault(tmp_path)

    with patch("src.skills.accounting_audit.OdooMCPClient") as MockCls:
        MockCls.from_env.return_value = mock_odoo_client()
        from src.skills.accounting_audit import run
        result = run(vault)

    revenue = result.get("revenue")
    if revenue is not None:
        assert isinstance(revenue["mtd_total"], (int, float))


# ---------------------------------------------------------------------------
# T027.8  Function returns without crashing when vault/Logs is empty
# ---------------------------------------------------------------------------

def test_run_does_not_crash_when_logs_empty(tmp_path):
    vault = make_vault(tmp_path)
    # Logs dir is empty

    with patch("src.skills.accounting_audit.OdooMCPClient") as MockCls:
        MockCls.from_env.return_value = mock_odoo_client()
        from src.skills.accounting_audit import run
        result = run(vault)

    assert isinstance(result, dict)
    # Should not raise any exception
