"""Gmail watcher stub — Silver tier placeholder."""

from typing import Any

from src.watchers.base_watcher import BaseWatcher


class GmailWatcher(BaseWatcher):
    """Gmail API polling watcher. Not implemented in Bronze tier."""

    def __init__(self, vault_root: str, poll_interval: int = 60) -> None:
        super().__init__("gmail_watcher", vault_root, poll_interval)

    def check_for_updates(self) -> list[dict[str, Any]]:
        raise NotImplementedError("GmailWatcher is not implemented in Bronze tier")
