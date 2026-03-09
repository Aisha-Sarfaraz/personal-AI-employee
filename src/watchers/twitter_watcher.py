"""TwitterWatcher — polls Twitter API v2 for timeline metrics every 86400s."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

try:
    import tweepy  # type: ignore[import]
except ImportError:  # pragma: no cover
    tweepy = None  # type: ignore[assignment]

from src.core.retry_handler import ErrorCategory
from src.core.vault import write_frontmatter_file
from src.watchers.base_watcher import BaseWatcher


class TwitterWatcher(BaseWatcher):
    """Polls Twitter API v2 for timeline engagement; dev-mode reads twitter_mock/."""

    POLL_INTERVAL_S = 86400

    def __init__(
        self,
        vault_root: str = "",
        poll_interval: int = 86400,
        dev_mode: bool = False,
    ) -> None:
        super().__init__("twitter_watcher", vault_root, poll_interval)
        self.dev_mode = dev_mode or os.environ.get("DEV_MODE", "").lower() in (
            "true",
            "1",
            "yes",
        )
        self._paused = False
        self._mock_folder = os.path.join(vault_root, "Watch", "twitter_mock")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def check_for_updates(self) -> list[dict[str, Any]]:
        """Return new Twitter engagement items; dedup against _processed_ids."""
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
        """Write vault/Inbox/TW_ENGAGEMENT_{id}_{ts}.md with engagement frontmatter."""
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        item_id = item["id"]
        filename = f"TW_ENGAGEMENT_{item_id}_{ts}.md"
        relative_path = f"Inbox/{filename}"

        metadata: dict[str, Any] = {
            "type": "social_media_engagement",
            "source": "twitter",
            "tweet_id": item_id,
            "retweet_count": item.get("retweet_count", 0),
            "like_count": item.get("like_count", 0),
            "reply_count": item.get("reply_count", 0),
            "created_at": item.get("created_at", ""),
            "status": "new",
        }

        body = (
            f"## Twitter Tweet Engagement\n\n"
            f"**Tweet ID:** {item_id}\n"
            f"**Retweets:** {item.get('retweet_count', 0)}\n"
            f"**Likes:** {item.get('like_count', 0)}\n"
            f"**Replies:** {item.get('reply_count', 0)}\n\n"
            f"### Tweet Text\n\n{item.get('text', '')}\n"
        )

        write_frontmatter_file(vault_root, relative_path, metadata, body)
        self._processed_ids.add(item_id)
        return os.path.join(vault_root, relative_path)

    # ------------------------------------------------------------------
    # Internal: live API fetch via tweepy
    # ------------------------------------------------------------------

    def _fetch_live(self) -> list[dict[str, Any]]:
        """Fetch tweets via Twitter API v2 using tweepy."""
        if tweepy is None:
            raise ImportError("tweepy not installed — run: pip install tweepy")

        bearer_token = os.environ.get("TWITTER_BEARER_TOKEN", "")
        user_id = os.environ.get("TWITTER_USER_ID", "")

        try:
            client = tweepy.Client(bearer_token=bearer_token)
            response = client.get_users_tweets(
                id=user_id,
                tweet_fields=["public_metrics", "created_at"],
                max_results=10,
            )
        except Exception as e:
            # Check for auth errors from tweepy
            err_str = str(e).lower()
            if "unauthorized" in err_str or "401" in err_str or "403" in err_str:
                auth_err = PermissionError(f"Twitter auth error: {e}")
                auth_err.error_category = ErrorCategory.AUTH  # type: ignore[attr-defined]
                raise auth_err
            raise

        if not response or not response.data:
            return []

        items = []
        for tweet in response.data:
            tweet_id = str(tweet.id)
            if tweet_id in self._processed_ids:
                continue
            metrics = getattr(tweet, "public_metrics", {}) or {}
            created = getattr(tweet, "created_at", None)
            items.append({
                "id": tweet_id,
                "text": tweet.text or "",
                "retweet_count": metrics.get("retweet_count", 0),
                "like_count": metrics.get("like_count", 0),
                "reply_count": metrics.get("reply_count", 0),
                "created_at": created.isoformat() if created else "",
            })
        return items
