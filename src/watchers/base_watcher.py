"""Abstract base class for all watchers."""

import glob
import json
import os
import time
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any

from src.core.frontmatter import create_standard_metadata
from src.core.vault import write_frontmatter_file


class BaseWatcher(ABC):
    """Abstract base class for perception layer watchers.

    Provides deduplication via processed IDs, JSON state persistence,
    and a configurable poll interval.
    """

    def __init__(
        self,
        name: str = "base_watcher",
        vault_root: str = "",
        poll_interval: int = 5,
    ) -> None:
        self.name = name
        self.vault_root = vault_root
        self.poll_interval = poll_interval
        self._processed_ids: set[str] = set()
        state_dir = os.path.join(vault_root, "state") if vault_root else ""
        self._state_file = os.path.join(state_dir, f"{name}_state.json") if state_dir else f"{name}_state.json"
        self._running = False

    @property
    def dry_run(self) -> bool:
        """True when DRY_RUN env var is set to a truthy value (case-insensitive)."""
        val = os.environ.get("DRY_RUN", "").lower().strip()
        return val in ("true", "1", "yes")

    def _load_mock_items(self, mock_folder: str) -> list[dict[str, Any]]:
        """Load mock items from all *.json files in mock_folder.

        Args:
            mock_folder: Absolute or relative path to the mock data folder.

        Returns:
            List of item dicts. Malformed files and missing folders return [].
        """
        if not os.path.isdir(mock_folder):
            return []

        items: list[dict[str, Any]] = []
        for json_path in glob.glob(os.path.join(mock_folder, "*.json")):
            try:
                with open(json_path, encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    items.append(data)
                elif isinstance(data, list):
                    items.extend(i for i in data if isinstance(i, dict))
            except (json.JSONDecodeError, OSError):
                pass  # skip malformed files

        return items

    @abstractmethod
    def check_for_updates(self) -> list[dict[str, Any]]:
        """Check for new items. Returns list of item dicts with at least 'id' key."""

    def create_action_file(self, vault_root: str, item: dict[str, Any]) -> str:
        """Create a frontmatter .md file in Inbox/ from an item dict.

        Args:
            vault_root: Path to vault root.
            item: Dict with keys: id, body/content, type, source (optional).

        Returns:
            The absolute path to the created file.
        """
        item_id = item["id"]
        content = item.get("body", item.get("content", ""))
        item_type = item.get("type", "general")
        item_source = item.get("source", self.name)
        priority = item.get("priority", "MEDIUM")

        metadata = create_standard_metadata(
            type=item_type,
            source=item_source,
            priority=priority,
            status="new",
        )
        metadata["id"] = item_id
        metadata["original_filename"] = item.get("filename", "")
        metadata["tags"] = item.get("tags", [])

        # Format body for readable Obsidian display
        _PRIORITY_EMOJI = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🟢"}
        p_emoji = _PRIORITY_EMOJI.get(priority, "⚪")

        body = (
            f"## 📥 Incoming Item\n\n"
            f"> [!info] Item Details\n"
            f"> **Source:** {item_source}\n"
            f"> **File:** {item.get('filename', 'unknown')}\n"
            f"> **Priority:** {p_emoji} {priority}\n"
            f"> **Status:** 🆕 New\n\n"
            f"---\n\n"
            f"## 📄 Content\n\n"
            f"{content}\n\n"
            f"---\n\n"
            f"> [!tip] Next Step\n"
            f"> This item will be automatically triaged and moved to **Needs_Action/** for planning.\n"
        )

        filename = f"{item_id}.md"
        relative_path = f"Inbox/{filename}"
        write_frontmatter_file(vault_root, relative_path, metadata, body)
        self._processed_ids.add(item_id)
        return os.path.join(vault_root, relative_path)

    def save_state(self) -> None:
        """Persist processed IDs to JSON file."""
        os.makedirs(os.path.dirname(self._state_file), exist_ok=True)
        state = {
            "watcher_name": self.name,
            "last_updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
            "processed_ids": list(self._processed_ids),
        }
        with open(self._state_file, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)

    def load_state(self) -> None:
        """Restore processed IDs from JSON file."""
        if os.path.exists(self._state_file):
            with open(self._state_file, "r", encoding="utf-8") as f:
                state = json.load(f)
            self._processed_ids = set(state.get("processed_ids", []))

    def is_processed(self, item_id: str) -> bool:
        """Check if an item has already been processed."""
        return item_id in self._processed_ids

    def run(self, vault_root: str) -> None:
        """Main loop: poll for updates and create action files."""
        self._running = True
        self.load_state()
        while self._running:
            try:
                items = self.check_for_updates()
                for item in items:
                    item_id = item.get("id", "")
                    if item_id and not self.is_processed(item_id):
                        try:
                            self.create_action_file(vault_root, item)
                        except Exception:
                            pass  # Error isolation per item
                self.save_state()
            except Exception:
                pass  # Error isolation per cycle
            time.sleep(self.poll_interval)

    def stop(self) -> None:
        """Stop the run loop."""
        self._running = False
