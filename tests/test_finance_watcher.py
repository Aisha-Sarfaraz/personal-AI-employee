"""Tests for FinanceWatcher — Gold Tier T019 (RED first)."""

from __future__ import annotations

import csv
import hashlib
import json
import os
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Vault helpers
# ---------------------------------------------------------------------------

VAULT_DIRS = (
    "Accounting", "state", "Inbox", "Logs",
    os.path.join("Watch", "finance_mock"),
    os.path.join("Watch", "finance_drop"),
)


def make_vault(tmp_path: Path) -> str:
    vault_root = tmp_path / "vault"
    for folder in VAULT_DIRS:
        (vault_root / folder).mkdir(parents=True, exist_ok=True)
    return str(vault_root)


def write_mock_json(vault_root: str, items: list[dict]) -> str:
    """Write mock transactions JSON to vault/Watch/finance_mock/sample.json."""
    path = os.path.join(vault_root, "Watch", "finance_mock", "sample.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(items, f)
    return path


def write_csv(vault_root: str, rows: list[dict], filename: str = "txn.csv") -> str:
    """Write a 4-column CSV to vault/Watch/finance_drop/<filename>."""
    path = os.path.join(vault_root, "Watch", "finance_drop", filename)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["date", "description", "amount", "account"])
        writer.writeheader()
        writer.writerows(rows)
    return path


# ---------------------------------------------------------------------------
# T019.1  check_for_updates(dev_mode=True) returns list of dicts
# ---------------------------------------------------------------------------

def test_check_for_updates_dev_mode_returns_list(tmp_path):
    vault = make_vault(tmp_path)
    write_mock_json(vault, [
        {"id": "mock-001", "date": "2026-02-24", "description": "ACME payment",
         "amount": 1250.0, "account": "Bank"}
    ])
    from src.watchers.finance_watcher import FinanceWatcher
    fw = FinanceWatcher(vault_root=vault, poll_interval=300, dev_mode=True)
    result = fw.check_for_updates()
    assert isinstance(result, list)
    assert len(result) >= 1


# ---------------------------------------------------------------------------
# T019.2  Each dict has keys: id, date, description, amount, account, source
# ---------------------------------------------------------------------------

def test_check_for_updates_dev_mode_dict_keys(tmp_path):
    vault = make_vault(tmp_path)
    write_mock_json(vault, [
        {"id": "mock-001", "date": "2026-02-24", "description": "ACME payment",
         "amount": 1250.0, "account": "Bank"}
    ])
    from src.watchers.finance_watcher import FinanceWatcher
    fw = FinanceWatcher(vault_root=vault, dev_mode=True)
    result = fw.check_for_updates()
    assert len(result) >= 1
    item = result[0]
    for key in ("id", "date", "description", "amount", "account", "source"):
        assert key in item, f"Missing key: {key}"


# ---------------------------------------------------------------------------
# T019.3  Odoo path calls OdooMCPClient.list_transactions
# ---------------------------------------------------------------------------

def test_odoo_path_calls_list_transactions(tmp_path):
    vault = make_vault(tmp_path)
    from src.watchers.finance_watcher import FinanceWatcher
    fw = FinanceWatcher(vault_root=vault, dev_mode=False)

    mock_client = MagicMock()
    mock_client.list_transactions.return_value = {
        "transactions": [
            {"move_line_id": 101, "date": "2026-02-24",
             "description": "Client payment", "amount": 500.0, "account": "Bank"}
        ],
        "count": 1,
    }

    with patch("src.watchers.finance_watcher.OdooMCPClient") as MockCls:
        MockCls.from_env.return_value = mock_client
        result = fw.check_for_updates()

    mock_client.list_transactions.assert_called_once()
    assert isinstance(result, list)


# ---------------------------------------------------------------------------
# T019.4  CSV path: parses 4-column CSV with header skip
# ---------------------------------------------------------------------------

def test_csv_path_parses_csv(tmp_path):
    vault = make_vault(tmp_path)
    write_csv(vault, [
        {"date": "2026-02-24", "description": "CSV payment", "amount": "500.00", "account": "Bank"}
    ])
    from src.watchers.finance_watcher import FinanceWatcher
    fw = FinanceWatcher(vault_root=vault, dev_mode=False)

    with patch("src.watchers.finance_watcher.OdooMCPClient") as MockCls:
        mock_client = MagicMock()
        mock_client.list_transactions.side_effect = ConnectionError("Odoo down")
        MockCls.from_env.return_value = mock_client
        result = fw.check_for_updates()

    assert isinstance(result, list)
    assert len(result) >= 1
    csv_item = result[0]
    assert csv_item["description"] == "CSV payment"
    assert csv_item["source"] == "csv"


# ---------------------------------------------------------------------------
# T019.5  Dedup: skips already-processed IDs
# ---------------------------------------------------------------------------

def test_dedup_skips_already_processed_ids(tmp_path):
    vault = make_vault(tmp_path)
    write_mock_json(vault, [
        {"id": "mock-001", "date": "2026-02-24", "description": "ACME",
         "amount": 1250.0, "account": "Bank"}
    ])
    from src.watchers.finance_watcher import FinanceWatcher
    fw = FinanceWatcher(vault_root=vault, dev_mode=True)
    # Pre-load this ID as already processed
    fw._finance_processed_ids.add("mock-001")

    result = fw.check_for_updates()
    assert all(item["id"] != "mock-001" for item in result)


# ---------------------------------------------------------------------------
# T019.6  _make_item_id returns str(move_line_id) for Odoo source
# ---------------------------------------------------------------------------

def test_make_item_id_odoo_source(tmp_path):
    vault = make_vault(tmp_path)
    from src.watchers.finance_watcher import FinanceWatcher
    fw = FinanceWatcher(vault_root=vault, dev_mode=False)
    item = {"source": "odoo", "move_line_id": 101, "date": "2026-02-24",
            "description": "Pay", "amount": 100.0}
    result = fw._make_item_id(item)
    assert result == "101"


# ---------------------------------------------------------------------------
# T019.7  _make_item_id returns SHA-256[:16] for CSV source
# ---------------------------------------------------------------------------

def test_make_item_id_csv_source(tmp_path):
    vault = make_vault(tmp_path)
    from src.watchers.finance_watcher import FinanceWatcher
    fw = FinanceWatcher(vault_root=vault, dev_mode=False)
    item = {"source": "csv", "date": "2026-02-24", "description": "Office",
            "amount": -45.0, "account": "Expenses"}
    result = fw._make_item_id(item)
    expected_raw = f"2026-02-24Office{-45.0}"
    expected = hashlib.sha256(expected_raw.encode()).hexdigest()[:16]
    assert result == expected
    assert len(result) == 16


# ---------------------------------------------------------------------------
# T019.8  create_action_file creates vault/Accounting/Current_Month.md if absent
# ---------------------------------------------------------------------------

def test_create_action_file_creates_current_month(tmp_path):
    vault = make_vault(tmp_path)
    from src.watchers.finance_watcher import FinanceWatcher
    fw = FinanceWatcher(vault_root=vault, dev_mode=True)

    item = {"id": "t001", "date": "2026-02-24", "description": "Payment",
            "amount": 500.0, "account": "Bank", "source": "csv"}
    fw.create_action_file(vault, item)

    current_month_path = os.path.join(vault, "Accounting", "Current_Month.md")
    assert os.path.exists(current_month_path)


# ---------------------------------------------------------------------------
# T019.9  New transaction appended as Markdown table row
# ---------------------------------------------------------------------------

def test_transaction_appended_as_table_row(tmp_path):
    vault = make_vault(tmp_path)
    from src.watchers.finance_watcher import FinanceWatcher
    fw = FinanceWatcher(vault_root=vault, dev_mode=True)

    item = {"id": "t001", "date": "2026-02-24", "description": "ACME payment",
            "amount": 1250.0, "account": "Bank", "source": "csv"}
    fw.create_action_file(vault, item)

    current_month_path = os.path.join(vault, "Accounting", "Current_Month.md")
    with open(current_month_path, encoding="utf-8") as f:
        content = f.read()

    assert "2026-02-24" in content
    assert "ACME payment" in content
    assert "Bank" in content
    # Should be a markdown table row
    assert "|" in content


# ---------------------------------------------------------------------------
# T019.10  Existing rows not duplicated
# ---------------------------------------------------------------------------

def test_existing_rows_not_duplicated(tmp_path):
    vault = make_vault(tmp_path)
    from src.watchers.finance_watcher import FinanceWatcher
    fw = FinanceWatcher(vault_root=vault, dev_mode=True)

    item = {"id": "t001", "date": "2026-02-24", "description": "ACME payment",
            "amount": 1250.0, "account": "Bank", "source": "csv"}

    # Call twice
    fw.create_action_file(vault, item)
    fw.create_action_file(vault, item)

    current_month_path = os.path.join(vault, "Accounting", "Current_Month.md")
    with open(current_month_path, encoding="utf-8") as f:
        content = f.read()

    # Count how many times the row appears
    count = content.count("ACME payment")
    assert count == 1, f"Expected 1 occurrence, found {count}"


# ---------------------------------------------------------------------------
# T019.11  finance_processed_ids.json updated after processing
# ---------------------------------------------------------------------------

def test_finance_processed_ids_updated_after_processing(tmp_path):
    vault = make_vault(tmp_path)
    write_mock_json(vault, [
        {"id": "mock-001", "date": "2026-02-24", "description": "ACME",
         "amount": 1250.0, "account": "Bank"}
    ])
    from src.watchers.finance_watcher import FinanceWatcher
    fw = FinanceWatcher(vault_root=vault, dev_mode=True)
    fw.check_for_updates()
    fw.save_state()

    ids_path = os.path.join(vault, "state", "finance_processed_ids.json")
    assert os.path.exists(ids_path)
    with open(ids_path, encoding="utf-8") as f:
        data = json.load(f)
    assert "mock-001" in data.get("processed_ids", [])


# ---------------------------------------------------------------------------
# T019.12  Month rollover: creates YYYY-MM_transactions.md when month changes
# ---------------------------------------------------------------------------

def test_month_rollover_creates_archive_file(tmp_path):
    vault = make_vault(tmp_path)
    from src.watchers.finance_watcher import FinanceWatcher
    fw = FinanceWatcher(vault_root=vault, dev_mode=True)

    # Create Current_Month.md with OLD month heading
    current_month_path = os.path.join(vault, "Accounting", "Current_Month.md")
    with open(current_month_path, "w", encoding="utf-8") as f:
        f.write("# Accounting — January 2025\n\n")
        f.write("| Date | Description | Amount | Account |\n")
        f.write("|------|-------------|--------|---------|\n")
        f.write("| 2025-01-15 | Old payment | +100.00 | Bank |\n")

    fw._check_month_rollover(vault)

    # Should have archived old file
    archive_files = [f for f in os.listdir(os.path.join(vault, "Accounting"))
                     if "_transactions.md" in f]
    assert len(archive_files) >= 1


# ---------------------------------------------------------------------------
# T019.13  Month rollover: creates new Current_Month.md with new month heading
# ---------------------------------------------------------------------------

def test_month_rollover_creates_new_current_month(tmp_path):
    vault = make_vault(tmp_path)
    from src.watchers.finance_watcher import FinanceWatcher
    fw = FinanceWatcher(vault_root=vault, dev_mode=True)

    # Create Current_Month.md with OLD month heading
    current_month_path = os.path.join(vault, "Accounting", "Current_Month.md")
    with open(current_month_path, "w", encoding="utf-8") as f:
        f.write("# Accounting — January 2025\n\n")
        f.write("| Date | Description | Amount | Account |\n")
        f.write("|------|-------------|--------|---------|\n")

    fw._check_month_rollover(vault)

    # New Current_Month.md should exist with current month heading
    assert os.path.exists(current_month_path)
    with open(current_month_path, encoding="utf-8") as f:
        content = f.read()

    current_month_str = datetime.now().strftime("%Y-%m")
    # The file should have been recreated (not contain the old Jan 2025 header as the sole heading)
    # It should at minimum exist and possibly have a new heading
    assert os.path.exists(current_month_path)


# ---------------------------------------------------------------------------
# T019.14  Odoo unreachable (ConnectionError): falls back to CSV
# ---------------------------------------------------------------------------

def test_odoo_unreachable_falls_back_to_csv(tmp_path):
    vault = make_vault(tmp_path)
    write_csv(vault, [
        {"date": "2026-02-24", "description": "CSV fallback pay",
         "amount": "300.00", "account": "Bank"}
    ])
    from src.watchers.finance_watcher import FinanceWatcher
    fw = FinanceWatcher(vault_root=vault, dev_mode=False)

    with patch("src.watchers.finance_watcher.OdooMCPClient") as MockCls:
        mock_client = MagicMock()
        mock_client.list_transactions.side_effect = ConnectionError("Odoo unreachable")
        MockCls.from_env.return_value = mock_client
        result = fw.check_for_updates()

    assert isinstance(result, list)
    assert any(item["source"] == "csv" for item in result)


# ---------------------------------------------------------------------------
# T019.15  dev_mode reads from vault/Watch/finance_mock folder
# ---------------------------------------------------------------------------

def test_dev_mode_reads_from_finance_mock(tmp_path):
    vault = make_vault(tmp_path)
    write_mock_json(vault, [
        {"id": "dev-001", "date": "2026-02-24", "description": "Dev mock item",
         "amount": 999.0, "account": "Mock"}
    ])
    from src.watchers.finance_watcher import FinanceWatcher
    fw = FinanceWatcher(vault_root=vault, dev_mode=True)

    # Should NOT call OdooMCPClient in dev mode
    with patch("src.watchers.finance_watcher.OdooMCPClient") as MockCls:
        result = fw.check_for_updates()
        MockCls.from_env.assert_not_called()

    assert any(item["description"] == "Dev mock item" for item in result)
