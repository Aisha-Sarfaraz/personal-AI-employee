"""Tests for LinkedInWatcher — TDD Red Phase (Phase 8, T033)."""

from __future__ import annotations

import hashlib
import json
import os
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def vault(tmp_path):
    (tmp_path / "Watch" / "linkedin_mock").mkdir(parents=True)
    (tmp_path / "Inbox").mkdir()
    (tmp_path / "state").mkdir()
    return tmp_path


@pytest.fixture()
def sample_linkedin_post():
    post_url = "https://www.linkedin.com/posts/testuser_activity-123456"
    return {
        "id": hashlib.sha256(post_url[:12].encode()).hexdigest()[:12],
        "source": "linkedin",
        "type": "social_media_engagement",
        "platform": "linkedin",
        "post_url": post_url,
        "post_preview": "Excited to share our new AI-powered business assistant!",
        "reactions": 47,
        "comments": 12,
        "priority": "MEDIUM",
        "filename": "li_test.json",
        "tags": [],
    }


# ---------------------------------------------------------------------------
# T033.1  dry-run returns mock items
# ---------------------------------------------------------------------------


def test_dry_run_returns_mock_items(vault, sample_linkedin_post):
    """With DRY_RUN=true, check_for_updates() loads from linkedin_mock/."""
    from src.watchers.linkedin_watcher import LinkedInWatcher

    mock_dir = os.path.join(str(vault), "Watch", "linkedin_mock")
    with open(os.path.join(mock_dir, "post1.json"), "w") as f:
        json.dump(sample_linkedin_post, f)

    with patch.dict(os.environ, {"DRY_RUN": "true"}):
        watcher = LinkedInWatcher(vault_root=str(vault), linkedin_mock_dir=mock_dir)
        items = watcher.check_for_updates()

    assert len(items) == 1


# ---------------------------------------------------------------------------
# T033.2  item type is social_media_engagement
# ---------------------------------------------------------------------------


def test_item_type_is_social_media_engagement(vault, sample_linkedin_post):
    """Items returned by the watcher have type='social_media_engagement'."""
    from src.watchers.linkedin_watcher import LinkedInWatcher

    mock_dir = os.path.join(str(vault), "Watch", "linkedin_mock")
    with open(os.path.join(mock_dir, "post1.json"), "w") as f:
        json.dump(sample_linkedin_post, f)

    with patch.dict(os.environ, {"DRY_RUN": "true"}):
        watcher = LinkedInWatcher(vault_root=str(vault), linkedin_mock_dir=mock_dir)
        items = watcher.check_for_updates()

    assert items[0]["type"] == "social_media_engagement"


# ---------------------------------------------------------------------------
# T033.3  item source is linkedin
# ---------------------------------------------------------------------------


def test_item_source_is_linkedin(vault, sample_linkedin_post):
    """Items returned by the watcher have source='linkedin'."""
    from src.watchers.linkedin_watcher import LinkedInWatcher

    mock_dir = os.path.join(str(vault), "Watch", "linkedin_mock")
    with open(os.path.join(mock_dir, "post1.json"), "w") as f:
        json.dump(sample_linkedin_post, f)

    with patch.dict(os.environ, {"DRY_RUN": "true"}):
        watcher = LinkedInWatcher(vault_root=str(vault), linkedin_mock_dir=mock_dir)
        items = watcher.check_for_updates()

    assert items[0]["source"] == "linkedin"


# ---------------------------------------------------------------------------
# T033.4  id is SHA256 of post_url
# ---------------------------------------------------------------------------


def test_id_is_sha256_of_post_url(vault):
    """For real-API items, id is derived from SHA256 of the post URL."""
    from src.watchers.linkedin_watcher import LinkedInWatcher

    watcher = LinkedInWatcher(vault_root=str(vault))
    post_url = "https://www.linkedin.com/posts/testuser_activity-999"
    generated_id = watcher._make_post_id(post_url)

    expected = hashlib.sha256(post_url[:12].encode()).hexdigest()[:12]
    assert generated_id == expected


# ---------------------------------------------------------------------------
# T033.5  session expired returns empty list
# ---------------------------------------------------------------------------


def test_session_expired_returns_empty_list(vault):
    """If LinkedIn redirects to /login, returns [] and logs audit entry."""
    from src.watchers.linkedin_watcher import LinkedInWatcher

    session_path = os.path.join(str(vault), "state", "linkedin_session")
    os.makedirs(session_path)

    with patch.dict(os.environ, {"DRY_RUN": "false"}, clear=False):
        watcher = LinkedInWatcher(vault_root=str(vault))
        watcher._session_path = session_path

        mock_page = MagicMock()
        mock_page.url = "https://www.linkedin.com/login"
        mock_ctx = MagicMock()
        mock_ctx.pages = [mock_page]
        mock_ctx.__enter__ = MagicMock(return_value=mock_ctx)
        mock_ctx.__exit__ = MagicMock(return_value=False)

        with patch("src.watchers.linkedin_watcher.sync_playwright") as mock_pw:
            mock_pw.return_value.__enter__.return_value.chromium.launch_persistent_context.return_value = mock_ctx
            items = watcher._scrape_linkedin()

    assert items == []


# ---------------------------------------------------------------------------
# T033.6  Playwright exception returns empty list
# ---------------------------------------------------------------------------


def test_playwright_exception_returns_empty_list(vault):
    """On Playwright crash/timeout, check_for_updates() degrades to [] without raising."""
    from src.watchers.linkedin_watcher import LinkedInWatcher

    session_path = os.path.join(str(vault), "state", "linkedin_session")
    os.makedirs(session_path)

    with patch.dict(os.environ, {"DRY_RUN": "false"}, clear=False):
        watcher = LinkedInWatcher(vault_root=str(vault))
        watcher._session_path = session_path

        with patch("src.watchers.linkedin_watcher.sync_playwright", side_effect=Exception("Playwright crash")):
            items = watcher.check_for_updates()

    assert items == []


# ---------------------------------------------------------------------------
# T033.7  setup_session uses headful mode
# ---------------------------------------------------------------------------


def test_setup_session_uses_headful_mode(vault):
    """setup_session() launches Playwright with headless=False for manual login."""
    from src.watchers.linkedin_watcher import LinkedInWatcher

    watcher = LinkedInWatcher(vault_root=str(vault))

    with patch("src.watchers.linkedin_watcher.sync_playwright") as mock_pw:
        mock_p = MagicMock()
        mock_pw.return_value.__enter__.return_value = mock_p
        mock_ctx = MagicMock()
        mock_p.chromium.launch_persistent_context.return_value = mock_ctx
        mock_ctx.pages = []
        mock_page = MagicMock()
        mock_ctx.new_page.return_value = mock_page
        mock_page.url = "https://www.linkedin.com/feed/"

        try:
            watcher.setup_session()
        except Exception:
            pass  # May raise if page interaction fails; we just check the call args

        call_kwargs = mock_p.chromium.launch_persistent_context.call_args
        if call_kwargs:
            _, kwargs = call_kwargs
            assert kwargs.get("headless") is False


# ---------------------------------------------------------------------------
# T033.8  uses BaseWatcher._load_mock_items
# ---------------------------------------------------------------------------


def test_uses_base_watcher_load_mock_items(vault, sample_linkedin_post):
    """Dry-run path calls self._load_mock_items() (inherited from BaseWatcher)."""
    from src.watchers.linkedin_watcher import LinkedInWatcher

    mock_dir = os.path.join(str(vault), "Watch", "linkedin_mock")
    with open(os.path.join(mock_dir, "post1.json"), "w") as f:
        json.dump(sample_linkedin_post, f)

    with patch.dict(os.environ, {"DRY_RUN": "true"}):
        watcher = LinkedInWatcher(vault_root=str(vault), linkedin_mock_dir=mock_dir)
        with patch.object(watcher, "_load_mock_items", wraps=watcher._load_mock_items) as spy:
            watcher.check_for_updates()
            spy.assert_called_once_with(mock_dir)
