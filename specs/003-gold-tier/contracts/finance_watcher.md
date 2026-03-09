# Finance Watcher — Interface Contract

**Feature**: 003-gold-tier
**Module**: `src/watchers/finance_watcher.py`
**Date**: 2026-02-25

---

## Overview

`FinanceWatcher` implements the `BaseWatcher` interface (Silver stub → Gold implementation).
Primary source: Odoo `list_transactions` via `OdooMCPClient`. Fallback: CSV files in
`vault/Watch/finance_drop/`. Dev-mode: JSON mock files in `vault/Watch/finance_mock/`.

---

## Class Interface

```python
class FinanceWatcher(BaseWatcher):
    """
    Polls Odoo for new financial transactions every 300s.
    Falls back to CSV files if Odoo is unreachable.
    Dev-mode reads vault/Watch/finance_mock/*.json.
    """

    POLL_INTERVAL_S: int = 300           # from settings.yaml → odoo.poll_interval_s

    def __init__(self, vault_root: str, poll_interval: int = 300,
                 dev_mode: bool = False): ...

    def check_for_updates(self) -> list[dict]:
        """
        Returns list of new (unprocessed) FinanceTransaction dicts:
        [{"id": "...", "date": "YYYY-MM-DD", "description": "...",
          "amount": 0.0, "account": "...", "source": "odoo"|"csv"}]

        Dedup: skips items whose id is in vault/state/finance_processed_ids.json.
        On Odoo unreachable: falls back to CSV; logs result: degraded.
        """

    def create_action_file(self, vault_root: str, item: dict) -> str:
        """
        Appends transaction as a Markdown table row to vault/Accounting/Current_Month.md.
        Creates the file with header if it does not exist.
        Returns the path to Current_Month.md (not an Inbox item — appended directly).
        """

    def _poll_odoo(self) -> list[dict]: ...
    def _poll_csv(self) -> list[dict]: ...
    def _make_item_id(self, item: dict) -> str: ...
    def _append_to_accounting(self, vault_root: str, item: dict) -> None: ...
    def _check_month_rollover(self, vault_root: str) -> None: ...
```

---

## Dedup Key Specification

| Source | Dedup Key | Method |
|--------|-----------|--------|
| Odoo | `move_line_id` field from `account.move.line` | Direct use |
| CSV | SHA-256(date + description + amount) | `_make_item_id()` |

```python
import hashlib

def _make_item_id(self, item: dict) -> str:
    if item["source"] == "odoo":
        return str(item["move_line_id"])
    raw = f"{item['date']}{item['description']}{item['amount']}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]
```

---

## CSV Format Specification

Files in `vault/Watch/finance_drop/*.csv`:
- **Header row required** — exactly `date,description,amount,account`
- **Amount**: signed decimal (`-100.00` = expense, `+1250.00` = income)
- **Date**: `YYYY-MM-DD`
- **Account**: free-text account name

```csv
date,description,amount,account
2026-02-24,Client payment — ACME,1250.00,Bank
2026-02-24,Office supplies,-45.00,Expenses:Office
```

---

## Dev-Mode Mock Format

Files in `vault/Watch/finance_mock/*.json` (flat schema):
```json
[
  {
    "id": "mock-001",
    "date": "2026-02-24",
    "description": "Client payment — ACME",
    "amount": 1250.00,
    "account": "Bank"
  }
]
```

---

## Accounting File Format

`vault/Accounting/Current_Month.md`:
```markdown
# Accounting — February 2026

| Date | Description | Amount | Account |
|------|-------------|--------|---------|
| 2026-02-24 | Client payment — ACME | +1250.00 | Bank |
| 2026-02-24 | Office supplies | -45.00 | Expenses:Office |
```

Created by `FinanceWatcher` on first transaction of the month. Appended on each new transaction.

---

## Month Rollover Logic

```python
def _check_month_rollover(self, vault_root: str) -> None:
    """
    If current month != month in Current_Month.md filename:
    - Rename Current_Month.md → vault/Accounting/YYYY-MM_transactions.md
    - Create new Current_Month.md with heading for new month
    """
    current_month = datetime.now().strftime("%Y-%m")
    archive_path = os.path.join(vault_root, "Accounting",
                                f"{current_month}_transactions.md")
    current_path = os.path.join(vault_root, "Accounting", "Current_Month.md")
    # check if file exists and month has changed
```

---

## Audit Log Entries

| Event | action_type | result |
|-------|-------------|--------|
| New transactions appended | `finance_transactions_ingested` | `success` |
| Odoo unreachable, CSV used | `finance_transactions_ingested` | `degraded` |
| Odoo unreachable, no CSV | `finance_poll_skipped` | `degraded` |
| Dedup skip | (not logged — silent) | — |
| Month rollover | `finance_month_rollover` | `success` |

---

## Degradation Contract

```
Odoo unreachable (ConnectionError / requests.exceptions.RequestException):
  1. Log WARNING to Python logger
  2. Attempt CSV fallback from vault/Watch/finance_drop/
  3. If CSV files present → process them; audit {result: degraded}
  4. If no CSV files → audit {result: degraded}; create vault/Inbox/FINANCE_ALERT_<ts>.md once per session
  5. Finance Watcher DOES NOT stop — resumes polling on next cycle
```
