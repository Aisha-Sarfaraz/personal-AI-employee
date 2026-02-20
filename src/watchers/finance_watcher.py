"""Finance watcher stub — Gold tier placeholder."""

from typing import Any

from src.watchers.base_watcher import BaseWatcher


class FinanceWatcher(BaseWatcher):
    """Odoo JSON-RPC + bank API watcher. Not implemented in Bronze tier."""

    def __init__(self, vault_root: str, poll_interval: int = 300) -> None:
        super().__init__("finance_watcher", vault_root, poll_interval)

    def check_for_updates(self) -> list[dict[str, Any]]:
        raise NotImplementedError("FinanceWatcher is not implemented in Bronze tier")
