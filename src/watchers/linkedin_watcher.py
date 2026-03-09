"""LinkedInWatcher — polls LinkedIn engagement data via Playwright persistent session."""

from __future__ import annotations

import hashlib
import os
import time
from typing import Any

from src.core.audit_logger import log_action
from src.watchers.base_watcher import BaseWatcher

_LINKEDIN_ACTIVITY_URL = "https://www.linkedin.com/in/{username}/detail/recent-activity/"
_LOGIN_INDICATOR = "/login"

try:
    from playwright.sync_api import sync_playwright
    _PLAYWRIGHT_AVAILABLE = True
except ImportError:  # pragma: no cover
    _PLAYWRIGHT_AVAILABLE = False
    sync_playwright = None  # type: ignore[assignment]


class LinkedInWatcher(BaseWatcher):
    """Polls LinkedIn for engagement on recent posts; supports dry-run mock mode."""

    def __init__(
        self,
        name: str = "linkedin_watcher",
        vault_root: str = "",
        poll_interval: int = 3600,  # 1 hour
        linkedin_mock_dir: str = "",
        session_path: str = "",
        username: str = "",
    ) -> None:
        super().__init__(name=name, vault_root=vault_root, poll_interval=poll_interval)
        self.linkedin_mock_dir = linkedin_mock_dir or os.path.join(vault_root, "Watch", "linkedin_mock")
        self._session_path = session_path or os.path.join(vault_root, "state", "linkedin_session")
        self.username = username

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def check_for_updates(self) -> list[dict[str, Any]]:
        """Return new LinkedIn engagement items; dedup against _processed_ids."""
        if self.dry_run:
            raw_items = self._load_mock_items(self.linkedin_mock_dir)
            return [item for item in raw_items if item.get("id") and item["id"] not in self._processed_ids]

        # Live path
        if not os.path.exists(self._session_path):
            log_action(
                vault_root=self.vault_root,
                agent="linkedin_watcher",
                action="session_missing",
                risk_tier="LOW",
                status="warning",
                details="LinkedIn session path does not exist — run setup_session() first",
            )
            return []

        try:
            return self._scrape_linkedin()
        except Exception as exc:
            log_action(
                vault_root=self.vault_root,
                agent="linkedin_watcher",
                action="scrape_error",
                risk_tier="LOW",
                status="error",
                details=str(exc),
            )
            return []

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------

    def setup_session(self) -> None:
        """Open a visible browser for manual LinkedIn login. Call once before headless use."""
        if not _PLAYWRIGHT_AVAILABLE:
            raise ImportError("playwright not installed — run: pip install playwright && playwright install chromium")

        os.makedirs(self._session_path, exist_ok=True)
        url = _LINKEDIN_ACTIVITY_URL.format(username=self.username or "me")

        with sync_playwright() as p:
            ctx = p.chromium.launch_persistent_context(
                self._session_path,
                headless=False,
                viewport={"width": 1280, "height": 900},
            )
            try:
                page = ctx.pages[0] if ctx.pages else ctx.new_page()
                page.goto("https://www.linkedin.com/feed/", wait_until="networkidle", timeout=60_000)
                print("[linkedin_watcher] Log in manually then close the browser.")
                page.wait_for_timeout(120_000)
            finally:
                ctx.close()

    # ------------------------------------------------------------------
    # Internal: Playwright scraping
    # ------------------------------------------------------------------

    def _scrape_linkedin(self) -> list[dict[str, Any]]:
        """Scrape LinkedIn activity page for recent post engagement."""
        if not _PLAYWRIGHT_AVAILABLE:
            return []

        username = self.username or "me"
        activity_url = _LINKEDIN_ACTIVITY_URL.format(username=username)
        items: list[dict[str, Any]] = []

        with sync_playwright() as p:
            ctx = p.chromium.launch_persistent_context(
                self._session_path,
                headless=True,
                viewport={"width": 1280, "height": 900},
            )
            try:
                page = ctx.pages[0] if ctx.pages else ctx.new_page()
                page.goto(activity_url, wait_until="networkidle", timeout=30_000)

                # Session expired?
                if _LOGIN_INDICATOR in page.url:
                    log_action(
                        vault_root=self.vault_root,
                        agent="linkedin_watcher",
                        action="session_expired",
                        risk_tier="LOW",
                        status="warning",
                        details="LinkedIn session expired — re-run setup_session()",
                    )
                    return []

                # Extract up to 5 posts
                post_elements = page.query_selector_all('[data-urn]')[:5]
                for el in post_elements:
                    try:
                        post_url = el.get_attribute("data-urn") or activity_url
                        text = (el.inner_text() or "")[:200]
                        reactions = self._extract_count(el, "reaction")
                        comments = self._extract_count(el, "comment")

                        post_id = self._make_post_id(post_url)
                        if post_id in self._processed_ids:
                            continue

                        items.append({
                            "id": post_id,
                            "source": "linkedin",
                            "type": "social_media_engagement",
                            "platform": "linkedin",
                            "post_url": post_url,
                            "post_preview": text,
                            "reactions": reactions,
                            "comments": comments,
                            "priority": "MEDIUM",
                            "filename": f"{post_id}.md",
                            "tags": [],
                        })
                    except Exception:
                        continue
            finally:
                ctx.close()

        return items

    @staticmethod
    def _extract_count(element: Any, keyword: str) -> int:
        try:
            text = element.inner_text() or ""
            for token in text.split():
                if keyword.lower() in token.lower():
                    digits = "".join(c for c in token if c.isdigit())
                    if digits:
                        return int(digits)
            return 0
        except Exception:
            return 0

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _make_post_id(post_url: str) -> str:
        """Generate deterministic ID from SHA256 of first 12 chars of post URL."""
        return hashlib.sha256(post_url[:12].encode()).hexdigest()[:12]
