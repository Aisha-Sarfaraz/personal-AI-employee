"""SC-021: Finance mock ingestion integration test — Gold Tier T021."""

from __future__ import annotations

import json
import os
from pathlib import Path

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


class TestSC021FinanceMockIngestion:
    """SC-021: Given dev_mode=True and mock JSON in finance_mock,
    FinanceWatcher.check_for_updates() returns items and create_action_file
    creates Current_Month.md with correct rows.
    """

    def test_sc021_check_for_updates_returns_items(self, tmp_path):
        vault = make_vault(tmp_path)
        mock_data = [
            {"id": "sc021-001", "date": "2026-02-24",
             "description": "SC021 ACME payment", "amount": 1250.0, "account": "Bank"},
            {"id": "sc021-002", "date": "2026-02-24",
             "description": "SC021 Office supplies", "amount": -45.0, "account": "Expenses"},
        ]
        mock_path = os.path.join(vault, "Watch", "finance_mock", "sc021_mock.json")
        with open(mock_path, "w", encoding="utf-8") as f:
            json.dump(mock_data, f)

        from src.watchers.finance_watcher import FinanceWatcher
        fw = FinanceWatcher(vault_root=vault, dev_mode=True)
        result = fw.check_for_updates()

        assert isinstance(result, list)
        assert len(result) == 2

    def test_sc021_creates_current_month_md(self, tmp_path):
        vault = make_vault(tmp_path)
        mock_data = [
            {"id": "sc021-001", "date": "2026-02-24",
             "description": "SC021 ACME payment", "amount": 1250.0, "account": "Bank"},
        ]
        mock_path = os.path.join(vault, "Watch", "finance_mock", "sc021_mock.json")
        with open(mock_path, "w", encoding="utf-8") as f:
            json.dump(mock_data, f)

        from src.watchers.finance_watcher import FinanceWatcher
        fw = FinanceWatcher(vault_root=vault, dev_mode=True)
        items = fw.check_for_updates()

        for item in items:
            fw.create_action_file(vault, item)

        current_month_path = os.path.join(vault, "Accounting", "Current_Month.md")
        assert os.path.exists(current_month_path)

    def test_sc021_current_month_has_table_rows(self, tmp_path):
        vault = make_vault(tmp_path)
        mock_data = [
            {"id": "sc021-001", "date": "2026-02-24",
             "description": "SC021 payment", "amount": 500.0, "account": "Bank"},
        ]
        mock_path = os.path.join(vault, "Watch", "finance_mock", "sc021_mock.json")
        with open(mock_path, "w", encoding="utf-8") as f:
            json.dump(mock_data, f)

        from src.watchers.finance_watcher import FinanceWatcher
        fw = FinanceWatcher(vault_root=vault, dev_mode=True)
        items = fw.check_for_updates()
        for item in items:
            fw.create_action_file(vault, item)

        current_month_path = os.path.join(vault, "Accounting", "Current_Month.md")
        with open(current_month_path, encoding="utf-8") as f:
            content = f.read()

        assert "SC021 payment" in content
        assert "|" in content
        assert "2026-02-24" in content

    def test_sc021_items_have_required_keys(self, tmp_path):
        vault = make_vault(tmp_path)
        mock_data = [
            {"id": "sc021-001", "date": "2026-02-24",
             "description": "SC021 payment", "amount": 500.0, "account": "Bank"},
        ]
        mock_path = os.path.join(vault, "Watch", "finance_mock", "sc021_mock.json")
        with open(mock_path, "w", encoding="utf-8") as f:
            json.dump(mock_data, f)

        from src.watchers.finance_watcher import FinanceWatcher
        fw = FinanceWatcher(vault_root=vault, dev_mode=True)
        items = fw.check_for_updates()

        for item in items:
            for key in ("id", "date", "description", "amount", "account", "source"):
                assert key in item

    def test_sc021_dedup_on_second_call(self, tmp_path):
        vault = make_vault(tmp_path)
        mock_data = [
            {"id": "sc021-001", "date": "2026-02-24",
             "description": "SC021 payment", "amount": 500.0, "account": "Bank"},
        ]
        mock_path = os.path.join(vault, "Watch", "finance_mock", "sc021_mock.json")
        with open(mock_path, "w", encoding="utf-8") as f:
            json.dump(mock_data, f)

        from src.watchers.finance_watcher import FinanceWatcher
        fw = FinanceWatcher(vault_root=vault, dev_mode=True)

        first = fw.check_for_updates()
        second = fw.check_for_updates()

        assert len(first) == 1
        assert len(second) == 0  # deduped
