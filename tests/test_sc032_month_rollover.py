"""SC-032: Month rollover integration test — Gold Tier T023."""

from __future__ import annotations

import os
from datetime import datetime
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


class TestSC032MonthRollover:
    """SC-032: Given existing Current_Month.md with prior month heading,
    on first new transaction of new month, old file archived to YYYY-MM_transactions.md
    and new Current_Month.md created.
    """

    def test_sc032_old_file_archived(self, tmp_path):
        vault = make_vault(tmp_path)
        current_month_path = os.path.join(vault, "Accounting", "Current_Month.md")
        with open(current_month_path, "w", encoding="utf-8") as f:
            f.write("# Accounting — January 2025\n\n")
            f.write("| Date | Description | Amount | Account |\n")
            f.write("|------|-------------|--------|---------|\n")
            f.write("| 2025-01-15 | Old payment | +100.00 | Bank |\n")

        from src.watchers.finance_watcher import FinanceWatcher
        fw = FinanceWatcher(vault_root=vault, dev_mode=True)
        fw._check_month_rollover(vault)

        archive_files = [f for f in os.listdir(os.path.join(vault, "Accounting"))
                         if "_transactions.md" in f]
        assert len(archive_files) >= 1

    def test_sc032_archive_file_named_correctly(self, tmp_path):
        vault = make_vault(tmp_path)
        current_month_path = os.path.join(vault, "Accounting", "Current_Month.md")
        with open(current_month_path, "w", encoding="utf-8") as f:
            f.write("# Accounting — January 2025\n\n")
            f.write("| Date | Description | Amount | Account |\n")
            f.write("|------|-------------|--------|---------|\n")

        from src.watchers.finance_watcher import FinanceWatcher
        fw = FinanceWatcher(vault_root=vault, dev_mode=True)
        fw._check_month_rollover(vault)

        # Should have archived as 2025-01_transactions.md
        archive_path = os.path.join(vault, "Accounting", "2025-01_transactions.md")
        assert os.path.exists(archive_path)

    def test_sc032_new_current_month_created(self, tmp_path):
        vault = make_vault(tmp_path)
        current_month_path = os.path.join(vault, "Accounting", "Current_Month.md")
        with open(current_month_path, "w", encoding="utf-8") as f:
            f.write("# Accounting — January 2025\n\n")
            f.write("| Date | Description | Amount | Account |\n")
            f.write("|------|-------------|--------|---------|\n")

        from src.watchers.finance_watcher import FinanceWatcher
        fw = FinanceWatcher(vault_root=vault, dev_mode=True)
        fw._check_month_rollover(vault)

        assert os.path.exists(current_month_path)

    def test_sc032_new_current_month_has_current_heading(self, tmp_path):
        vault = make_vault(tmp_path)
        current_month_path = os.path.join(vault, "Accounting", "Current_Month.md")
        with open(current_month_path, "w", encoding="utf-8") as f:
            f.write("# Accounting — January 2025\n\n")
            f.write("| Date | Description | Amount | Account |\n")
            f.write("|------|-------------|--------|---------|\n")

        from src.watchers.finance_watcher import FinanceWatcher
        fw = FinanceWatcher(vault_root=vault, dev_mode=True)
        fw._check_month_rollover(vault)

        with open(current_month_path, encoding="utf-8") as f:
            content = f.read()

        current_month_name = datetime.now().strftime("%B %Y")
        assert current_month_name in content

    def test_sc032_no_rollover_if_same_month(self, tmp_path):
        vault = make_vault(tmp_path)
        current_month_name = datetime.now().strftime("%B %Y")
        current_month_path = os.path.join(vault, "Accounting", "Current_Month.md")
        with open(current_month_path, "w", encoding="utf-8") as f:
            f.write(f"# Accounting — {current_month_name}\n\n")
            f.write("| Date | Description | Amount | Account |\n")
            f.write("|------|-------------|--------|---------|\n")
            f.write("| 2026-02-24 | Recent payment | +500.00 | Bank |\n")

        from src.watchers.finance_watcher import FinanceWatcher
        fw = FinanceWatcher(vault_root=vault, dev_mode=True)
        fw._check_month_rollover(vault)

        # File should still exist unchanged (same month)
        with open(current_month_path, encoding="utf-8") as f:
            content = f.read()
        assert "Recent payment" in content

    def test_sc032_create_action_file_triggers_rollover(self, tmp_path):
        vault = make_vault(tmp_path)
        current_month_path = os.path.join(vault, "Accounting", "Current_Month.md")
        with open(current_month_path, "w", encoding="utf-8") as f:
            f.write("# Accounting — January 2025\n\n")
            f.write("| Date | Description | Amount | Account |\n")
            f.write("|------|-------------|--------|---------|\n")

        from src.watchers.finance_watcher import FinanceWatcher
        fw = FinanceWatcher(vault_root=vault, dev_mode=True)

        item = {"id": "t001", "date": "2026-02-24", "description": "New month payment",
                "amount": 100.0, "account": "Bank", "source": "mock"}
        fw.create_action_file(vault, item)

        # Archive should now exist
        archive_files = [f for f in os.listdir(os.path.join(vault, "Accounting"))
                         if "_transactions.md" in f]
        assert len(archive_files) >= 1
