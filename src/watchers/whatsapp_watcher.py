"""WhatsApp watcher stub — Silver tier placeholder."""

from typing import Any

from src.watchers.base_watcher import BaseWatcher


class WhatsAppWatcher(BaseWatcher):
    """WhatsApp Business API watcher. Not implemented in Bronze tier."""

    def __init__(self, vault_root: str, poll_interval: int = 60) -> None:
        super().__init__("whatsapp_watcher", vault_root, poll_interval)

    def check_for_updates(self) -> list[dict[str, Any]]:
        raise NotImplementedError("WhatsAppWatcher is not implemented in Bronze tier")
