"""SC-022: CSV fallback integration test — Gold Tier T022."""

from __future__ import annotations

import csv
import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


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


def write_csv(vault_root: str, rows: list[dict], filename: str = "txn.csv") -> str:
    path = os.path.join(vault_root, "Watch", "finance_drop", filename)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["date", "description", "amount", "account"])
        writer.writeheader()
        writer.writerows(rows)
    return path


class TestSC022CsvFallback:
    """SC-022: Given Odoo connection refused, FinanceWatcher uses CSV from finance_drop."""

    def test_sc022_csv_items_returned_on_odoo_failure(self, tmp_path):
        vault = make_vault(tmp_path)
        write_csv(vault, [
            {"date": "2026-02-24", "description": "SC022 CSV payment",
             "amount": "300.00", "account": "Bank"}
        ])

        from src.watchers.finance_watcher import FinanceWatcher
        fw = FinanceWatcher(vault_root=vault, dev_mode=False)

        with patch("src.watchers.finance_watcher.OdooMCPClient") as MockCls:
            mock_client = MagicMock()
            mock_client.list_transactions.side_effect = ConnectionError("Refused")
            MockCls.from_env.return_value = mock_client
            result = fw.check_for_updates()

        assert len(result) >= 1
        assert all(item["source"] == "csv" for item in result)

    def test_sc022_csv_item_has_correct_description(self, tmp_path):
        vault = make_vault(tmp_path)
        write_csv(vault, [
            {"date": "2026-02-24", "description": "SC022 Payroll",
             "amount": "2000.00", "account": "Payroll"}
        ])

        from src.watchers.finance_watcher import FinanceWatcher
        fw = FinanceWatcher(vault_root=vault, dev_mode=False)

        with patch("src.watchers.finance_watcher.OdooMCPClient") as MockCls:
            mock_client = MagicMock()
            mock_client.list_transactions.side_effect = ConnectionError("Refused")
            MockCls.from_env.return_value = mock_client
            result = fw.check_for_updates()

        assert any(item["description"] == "SC022 Payroll" for item in result)

    def test_sc022_audit_entry_written_on_degraded(self, tmp_path):
        vault = make_vault(tmp_path)
        write_csv(vault, [
            {"date": "2026-02-24", "description": "SC022 CSV",
             "amount": "100.00", "account": "Bank"}
        ])

        from src.watchers.finance_watcher import FinanceWatcher
        fw = FinanceWatcher(vault_root=vault, dev_mode=False)

        with patch("src.watchers.finance_watcher.OdooMCPClient") as MockCls:
            mock_client = MagicMock()
            mock_client.list_transactions.side_effect = ConnectionError("Refused")
            MockCls.from_env.return_value = mock_client
            fw.check_for_updates()

        # Check that a log file was written
        log_dir = os.path.join(vault, "Logs")
        log_files = [f for f in os.listdir(log_dir) if f.endswith(".json")]
        assert len(log_files) >= 1

    def test_sc022_no_csv_files_returns_empty_list(self, tmp_path):
        vault = make_vault(tmp_path)
        # No CSV files in finance_drop

        from src.watchers.finance_watcher import FinanceWatcher
        fw = FinanceWatcher(vault_root=vault, dev_mode=False)

        with patch("src.watchers.finance_watcher.OdooMCPClient") as MockCls:
            mock_client = MagicMock()
            mock_client.list_transactions.side_effect = ConnectionError("Refused")
            MockCls.from_env.return_value = mock_client
            result = fw.check_for_updates()

        assert result == []

    def test_sc022_csv_amount_parsed_as_float(self, tmp_path):
        vault = make_vault(tmp_path)
        write_csv(vault, [
            {"date": "2026-02-24", "description": "Expense", "amount": "-45.50", "account": "Exp"}
        ])

        from src.watchers.finance_watcher import FinanceWatcher
        fw = FinanceWatcher(vault_root=vault, dev_mode=False)

        with patch("src.watchers.finance_watcher.OdooMCPClient") as MockCls:
            mock_client = MagicMock()
            mock_client.list_transactions.side_effect = ConnectionError("Refused")
            MockCls.from_env.return_value = mock_client
            result = fw.check_for_updates()

        assert len(result) >= 1
        assert isinstance(result[0]["amount"], float)
        assert result[0]["amount"] == -45.50
