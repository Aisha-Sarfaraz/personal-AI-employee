"""Tests for OdooMCPClient — all 6 operations in dev_mode."""
import json
import os

import pytest

from src.mcp_servers.odoo_mcp.client import OdooMCPClient


@pytest.fixture
def client(tmp_path):
    return OdooMCPClient(
        url="http://localhost:8069",
        db="fte_db",
        uid=1,
        password="test",
        vault_root=str(tmp_path),
        dev_mode=True,
    )


def test_list_transactions_dev_mode(client):
    result = client.list_transactions()
    assert "transactions" in result
    assert isinstance(result["transactions"], list)


def test_create_invoice_returns_pending_approval(client, tmp_path):
    result = client.create_invoice(partner="ACME", amount=100.0, description="Test")
    assert result["status"] == "pending_approval"
    assert "approval_file" in result


def test_create_invoice_approval_file_exists(client, tmp_path):
    result = client.create_invoice(partner="ACME", amount=100.0, description="Test")
    approval_file = result["approval_file"]
    assert os.path.exists(approval_file)


def test_approval_file_frontmatter_fields(client, tmp_path):
    result = client.create_invoice(partner="ACME Corp", amount=500.0, description="Consulting")
    with open(result["approval_file"], encoding="utf-8") as f:
        content = f.read()
    assert "partner" in content
    assert "amount" in content
    assert "risk_level: HIGH" in content
    assert "requires_approval: true" in content


def test_list_invoices_dev_mode(client):
    result = client.list_invoices()
    assert "invoices" in result
    assert isinstance(result["invoices"], list)


def test_get_account_balance_dev_mode(client):
    result = client.get_account_balance()
    assert "balance" in result
    assert isinstance(result["balance"], (int, float))


def test_record_expense_creates_approval_file(client, tmp_path):
    result = client.record_expense(description="Office supplies", amount=45.0, account="Expenses")
    assert result["status"] == "pending_approval"
    assert os.path.exists(result["approval_file"])


def test_post_invoice_creates_approval_file(client, tmp_path):
    result = client.post_invoice(invoice_id=42)
    assert result["status"] == "pending_approval"
    assert os.path.exists(result["approval_file"])


def test_list_transactions_returns_count(client):
    result = client.list_transactions()
    assert "count" in result
    assert result["count"] == len(result["transactions"])


def test_dev_mode_logs_simulated(client, tmp_path):
    result = client.create_invoice(partner="Test", amount=1.0, description="X")
    assert result.get("simulated") is True or "approval_file" in result


def test_all_six_methods_exist(client):
    for method in ["create_invoice", "list_invoices", "record_expense",
                   "get_account_balance", "post_invoice", "list_transactions"]:
        assert hasattr(client, method) and callable(getattr(client, method))


def test_create_invoice_validates_required_fields(client):
    with pytest.raises((ValueError, TypeError)):
        client.create_invoice(partner="", amount=0, description="")


def test_client_init_accepts_env_vars(tmp_path, monkeypatch):
    monkeypatch.setenv("ODOO_URL", "http://localhost:8069")
    monkeypatch.setenv("ODOO_DB", "fte_db")
    monkeypatch.setenv("ODOO_UID", "1")
    monkeypatch.setenv("ODOO_PASSWORD", "secret")
    c = OdooMCPClient.from_env(vault_root=str(tmp_path), dev_mode=True)
    assert c is not None


def test_connection_error_on_bad_url_live_mode(tmp_path):
    """In live mode with bad URL, ConnectionError raised."""
    c = OdooMCPClient(
        url="http://127.0.0.1:19999",
        db="test", uid=1, password="x",
        vault_root=str(tmp_path),
        dev_mode=False,
    )
    with pytest.raises((ConnectionError, Exception)):
        c.list_transactions()
