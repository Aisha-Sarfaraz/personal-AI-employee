"""Finance Watcher — Gold Tier implementation (T020).

Polls Odoo for new financial transactions every 300s.
Falls back to CSV files if Odoo is unreachable.
Dev-mode reads vault/Watch/finance_mock/*.json.
"""

from __future__ import annotations

import csv
import glob
import hashlib
import json
import logging
import os
from datetime import datetime
from typing import Any

from src.core.audit_logger import log as audit_log
from src.mcp_servers.odoo_mcp.client import OdooMCPClient
from src.watchers.base_watcher import BaseWatcher

logger = logging.getLogger(__name__)


class FinanceWatcher(BaseWatcher):
    """Odoo JSON-RPC + CSV fallback finance transaction watcher.

    Polls Odoo for new transactions every POLL_INTERVAL_S seconds.
    Falls back to CSV files if Odoo is unreachable.
    Dev-mode reads vault/Watch/finance_mock/*.json.
    """

    POLL_INTERVAL_S: int = 300

    def __init__(
        self,
        vault_root: str,
        poll_interval: int = 300,
        dev_mode: bool | None = None,
    ) -> None:
        super().__init__("finance_watcher", vault_root, poll_interval)
        if dev_mode is None:
            dev_mode = os.environ.get("DEV_MODE", "").lower() in ("true", "1", "yes")
        self.dev_mode = dev_mode
        self._finance_processed_ids: set[str] = set()
        self._finance_ids_file = os.path.join(vault_root, "state", "finance_processed_ids.json")
        self._load_finance_ids()

    # ------------------------------------------------------------------
    # State persistence (finance-specific, separate from base watcher state)
    # ------------------------------------------------------------------

    def _load_finance_ids(self) -> None:
        """Restore finance processed IDs from JSON file."""
        if os.path.exists(self._finance_ids_file):
            try:
                with open(self._finance_ids_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._finance_processed_ids = set(data.get("processed_ids", []))
            except (json.JSONDecodeError, OSError):
                self._finance_processed_ids = set()

    def _save_finance_ids(self) -> None:
        """Persist finance processed IDs to JSON file."""
        os.makedirs(os.path.dirname(self._finance_ids_file), exist_ok=True)
        data = {
            "watcher_name": "finance_watcher",
            "processed_ids": list(self._finance_processed_ids),
        }
        with open(self._finance_ids_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def save_state(self) -> None:
        """Override: persist base state + finance IDs."""
        super().save_state()
        self._save_finance_ids()

    def load_state(self) -> None:
        """Override: restore base state + finance IDs."""
        super().load_state()
        self._load_finance_ids()

    # ------------------------------------------------------------------
    # Main check_for_updates
    # ------------------------------------------------------------------

    def check_for_updates(self) -> list[dict[str, Any]]:
        """Check for new finance transactions.

        Returns list of new (unprocessed) FinanceTransaction dicts:
            [{"id": "...", "date": "YYYY-MM-DD", "description": "...",
              "amount": 0.0, "account": "...", "source": "odoo"|"csv"|"mock"}]

        Dedup: skips items whose id is in finance_processed_ids.
        On Odoo unreachable: falls back to CSV; logs result: degraded.
        """
        if self.dev_mode:
            return self._poll_mock()

        # Try Odoo first
        try:
            raw_items = self._poll_odoo()
        except ConnectionError as e:
            logger.warning("Odoo unreachable: %s — falling back to CSV", e)
            raw_items = self._poll_csv()
            # Mark as degraded if we got CSV items
            if raw_items:
                self._audit_degraded(len(raw_items))

        # Filter out already-processed IDs
        new_items = []
        for item in raw_items:
            item_id = self._make_item_id(item)
            item["id"] = item_id
            if item_id not in self._finance_processed_ids:
                new_items.append(item)
                self._finance_processed_ids.add(item_id)

        return new_items

    def _poll_odoo(self) -> list[dict[str, Any]]:
        """Poll Odoo for transactions via OdooMCPClient."""
        client = OdooMCPClient.from_env(vault_root=self.vault_root, dev_mode=False)
        result = client.list_transactions()
        transactions = result.get("transactions", [])
        items = []
        for txn in transactions:
            items.append({
                "move_line_id": txn.get("move_line_id"),
                "date": txn.get("date", ""),
                "description": txn.get("description", ""),
                "amount": float(txn.get("amount", 0.0)),
                "account": txn.get("account", ""),
                "source": "odoo",
            })
        return items

    def _poll_csv(self) -> list[dict[str, Any]]:
        """Poll CSV files in vault/Watch/finance_drop/."""
        drop_dir = os.path.join(self.vault_root, "Watch", "finance_drop")
        if not os.path.isdir(drop_dir):
            return []

        items = []
        for csv_path in glob.glob(os.path.join(drop_dir, "*.csv")):
            try:
                with open(csv_path, encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        try:
                            items.append({
                                "date": row.get("date", ""),
                                "description": row.get("description", ""),
                                "amount": float(row.get("amount", 0.0)),
                                "account": row.get("account", ""),
                                "source": "csv",
                            })
                        except (ValueError, KeyError):
                            pass  # skip malformed rows
            except OSError:
                pass  # skip unreadable files
        return items

    def _poll_mock(self) -> list[dict[str, Any]]:
        """Poll mock JSON files in vault/Watch/finance_mock/."""
        mock_folder = os.path.join(self.vault_root, "Watch", "finance_mock")
        raw_items = self._load_mock_items(mock_folder)
        items = []
        for raw in raw_items:
            item = {
                "date": raw.get("date", ""),
                "description": raw.get("description", ""),
                "amount": float(raw.get("amount", 0.0)),
                "account": raw.get("account", ""),
                "source": "mock",
            }
            # Use the raw id if present; else generate one
            if "id" in raw:
                item_id = str(raw["id"])
            else:
                item_id = self._make_item_id(item)
            item["id"] = item_id
            if item_id not in self._finance_processed_ids:
                items.append(item)
                self._finance_processed_ids.add(item_id)
        return items

    # ------------------------------------------------------------------
    # ID generation
    # ------------------------------------------------------------------

    def _make_item_id(self, item: dict[str, Any]) -> str:
        """Generate dedup ID for a transaction.

        Odoo: str(move_line_id)
        CSV/mock: SHA-256(date + description + amount)[:16]
        """
        source = item.get("source", "csv")
        if source == "odoo":
            return str(item["move_line_id"])
        raw = f"{item['date']}{item['description']}{item['amount']}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    # ------------------------------------------------------------------
    # Accounting file write
    # ------------------------------------------------------------------

    def create_action_file(self, vault_root: str, item: dict[str, Any]) -> str:
        """Append transaction as a Markdown table row to vault/Accounting/Current_Month.md.

        Creates the file with heading + table header if absent.
        Checks month rollover before appending.
        Returns the path to Current_Month.md.
        """
        # Check for month rollover first
        self._check_month_rollover(vault_root)

        accounting_dir = os.path.join(vault_root, "Accounting")
        os.makedirs(accounting_dir, exist_ok=True)
        current_month_path = os.path.join(accounting_dir, "Current_Month.md")

        # Format amount with sign
        amount = item.get("amount", 0.0)
        if amount >= 0:
            amount_str = f"+{amount:.2f}"
        else:
            amount_str = f"{amount:.2f}"

        date = item.get("date", "")
        description = item.get("description", "")
        account = item.get("account", "")
        item_id = item.get("id", "")

        # Read existing content to check for duplicates
        if os.path.exists(current_month_path):
            with open(current_month_path, encoding="utf-8") as f:
                existing_content = f.read()
            # Check if this item_id or this specific row already exists
            row_marker = f"| {date} | {description} | {amount_str} | {account} |"
            if row_marker in existing_content:
                return current_month_path  # already present
        else:
            existing_content = None

        if existing_content is None:
            # Create new file with heading and table header
            current_month_name = datetime.now().strftime("%B %Y")
            content = f"# Accounting — {current_month_name}\n\n"
            content += "| Date | Description | Amount | Account |\n"
            content += "|------|-------------|--------|---------|\n"
        else:
            content = existing_content

        # Append row
        row = f"| {date} | {description} | {amount_str} | {account} |\n"
        content += row

        with open(current_month_path, "w", encoding="utf-8") as f:
            f.write(content)

        # Track in finance processed IDs
        if item_id:
            self._finance_processed_ids.add(item_id)

        return current_month_path

    # ------------------------------------------------------------------
    # Month rollover
    # ------------------------------------------------------------------

    def _check_month_rollover(self, vault_root: str) -> None:
        """If current month != month in Current_Month.md, archive old and create new."""
        current_month_path = os.path.join(vault_root, "Accounting", "Current_Month.md")
        if not os.path.exists(current_month_path):
            return  # nothing to roll over

        with open(current_month_path, encoding="utf-8") as f:
            content = f.read()

        # Try to extract the month from the heading "# Accounting — <Month> <Year>"
        import re
        match = re.search(r"#\s+Accounting\s+[—–-]+\s+(\w+\s+\d{4})", content)
        if not match:
            return  # can't determine file month, skip

        file_month_str = match.group(1)  # e.g., "February 2026"
        try:
            file_date = datetime.strptime(file_month_str, "%B %Y")
            file_ym = file_date.strftime("%Y-%m")
        except ValueError:
            return  # can't parse, skip

        current_ym = datetime.now().strftime("%Y-%m")
        if file_ym == current_ym:
            return  # same month, no rollover needed

        # Archive: rename Current_Month.md to YYYY-MM_transactions.md
        archive_path = os.path.join(vault_root, "Accounting", f"{file_ym}_transactions.md")
        os.rename(current_month_path, archive_path)

        # Create new Current_Month.md with current month heading
        new_month_name = datetime.now().strftime("%B %Y")
        new_content = f"# Accounting — {new_month_name}\n\n"
        new_content += "| Date | Description | Amount | Account |\n"
        new_content += "|------|-------------|--------|---------|\n"
        with open(current_month_path, "w", encoding="utf-8") as f:
            f.write(new_content)

        # Audit log
        try:
            audit_log(
                vault_root=vault_root,
                action_type="finance_month_rollover",
                actor="finance_watcher",
                target=archive_path,
                parameters={"old_month": file_ym, "new_month": current_ym},
                approval_status="auto",
                approved_by="system",
                result="success",
            )
        except Exception:
            pass  # never let audit logging break the watcher

    def _audit_degraded(self, item_count: int) -> None:
        """Log a degraded audit entry for CSV fallback usage."""
        try:
            audit_log(
                vault_root=self.vault_root,
                action_type="finance_transactions_ingested",
                actor="finance_watcher",
                target="vault/Watch/finance_drop",
                parameters={"source": "csv_fallback", "count": item_count},
                approval_status="auto",
                approved_by="system",
                result="degraded",
            )
        except Exception:
            pass
