"""FacebookWatcher — polls Meta Graph API for Page engagement every 3600s."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

try:
    import requests
except ImportError:  # pragma: no cover
    requests = None  # type: ignore[assignment]

from src.core.retry_handler import ErrorCategory, with_retry
from src.core.vault import write_frontmatter_file
from src.watchers.base_watcher import BaseWatcher


class FacebookWatcher(BaseWatcher):
    """Polls Meta Graph API for Page post engagement; dev-mode reads facebook_mock/."""

    POLL_INTERVAL_S = 3600

    def __init__(
        self,
        vault_root: str = "",
        poll_interval: int = 3600,
        dev_mode: bool = False,
    ) -> None:
        super().__init__("facebook_watcher", vault_root, poll_interval)
        self.dev_mode = dev_mode or os.environ.get("DEV_MODE", "").lower() in (
            "true",
            "1",
            "yes",
        )
        self._paused = False
        self._mock_folder = os.path.join(vault_root, "Watch", "facebook_mock")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def check_for_updates(self) -> list[dict[str, Any]]:
        """Return new Facebook engagement items; dedup against _processed_ids."""
        if self._paused:
            return []

        if self.dev_mode:
            raw = self._load_mock_items(self._mock_folder)
            return [i for i in raw if i.get("id") and i["id"] not in self._processed_ids]

        try:
            return self._fetch_live()
        except Exception as e:
            if getattr(e, "error_category", None) == ErrorCategory.AUTH:
                self._paused = True
                return []
            raise

    def create_action_file(self, vault_root: str, item: dict[str, Any]) -> str:
        """Write vault/Inbox/FB_ENGAGEMENT_{id}_{ts}.md with engagement frontmatter."""
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        item_id = item["id"]
        filename = f"FB_ENGAGEMENT_{item_id}_{ts}.md"
        relative_path = f"Inbox/{filename}"

        metadata: dict[str, Any] = {
            "type": "social_media_engagement",
            "source": "facebook",
            "post_id": item_id,
            "likes": item.get("likes", 0),
            "comments": item.get("comments", 0),
            "reach": item.get("reach", 0),
            "created_at": item.get("created_at", ""),
            "status": "new",
        }

        body = (
            f"## Facebook Post Engagement\n\n"
            f"**Post ID:** {item_id}\n"
            f"**Likes:** {item.get('likes', 0)}\n"
            f"**Comments:** {item.get('comments', 0)}\n"
            f"**Reach:** {item.get('reach', 0)}\n\n"
            f"### Post Text\n\n{item.get('text', '')}\n"
        )

        write_frontmatter_file(vault_root, relative_path, metadata, body)
        self._processed_ids.add(item_id)
        return os.path.join(vault_root, relative_path)

    # ------------------------------------------------------------------
    # Internal: live API fetch
    # ------------------------------------------------------------------

    @with_retry(max_attempts=3, base_delay=1.0, max_delay=60.0)
    def _fetch_live(self) -> list[dict[str, Any]]:
        """GET /v20.0/me/posts from Meta Graph API."""
        token = os.environ.get("FACEBOOK_ACCESS_TOKEN", "")
        resp = requests.get(
            "https://graph.facebook.com/v20.0/me/posts",
            params={
                "fields": "message,likes.summary(true),comments.summary(true),created_time",
                "access_token": token,
            },
            timeout=10,
        )
        if resp.status_code in (401, 403):
            err = PermissionError(f"Meta API auth error {resp.status_code}")
            err.error_category = ErrorCategory.AUTH  # type: ignore[attr-defined]
            raise err
        resp.raise_for_status()
        data = resp.json()
        return [
            {
                "id": p["id"],
                "text": p.get("message", ""),
                "likes": p.get("likes", {}).get("summary", {}).get("total_count", 0),
                "comments": p.get("comments", {}).get("summary", {}).get("total_count", 0),
                "reach": 0,
                "created_at": p.get("created_time", ""),
            }
            for p in data.get("data", [])
        ]
