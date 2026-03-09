"""Tests for FacebookWatcher — TDD Phase 8, T035."""

from __future__ import annotations

import json
import os
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def vault(tmp_path):
    (tmp_path / "Watch" / "facebook_mock").mkdir(parents=True)
    (tmp_path / "Inbox").mkdir()
    (tmp_path / "state").mkdir()
    return tmp_path


@pytest.fixture()
def sample_fb_post():
    return {
        "id": "fb001",
        "text": "Our Q1 update!",
        "likes": 42,
        "comments": 7,
        "reach": 310,
        "created_at": "2026-02-24T09:00:00Z",
    }


def _write_mock_post(vault, post_data):
    mock_dir = os.path.join(str(vault), "Watch", "facebook_mock")
    with open(os.path.join(mock_dir, "sample_post.json"), "w") as f:
        json.dump([post_data], f)


# ---------------------------------------------------------------------------
# Test 1: dev_mode returns list from facebook_mock folder
# ---------------------------------------------------------------------------


def test_dev_mode_reads_facebook_mock(vault, sample_fb_post):
    """check_for_updates with dev_mode=True reads facebook_mock folder, returns list."""
    from src.watchers.facebook_watcher import FacebookWatcher

    _write_mock_post(vault, sample_fb_post)
    watcher = FacebookWatcher(vault_root=str(vault), dev_mode=True)
    items = watcher.check_for_updates()

    assert isinstance(items, list)
    assert len(items) >= 1


# ---------------------------------------------------------------------------
# Test 2: items have correct keys
# ---------------------------------------------------------------------------


def test_items_have_required_keys(vault, sample_fb_post):
    """Each item has keys: id, text, likes, comments, reach, created_at."""
    from src.watchers.facebook_watcher import FacebookWatcher

    _write_mock_post(vault, sample_fb_post)
    watcher = FacebookWatcher(vault_root=str(vault), dev_mode=True)
    items = watcher.check_for_updates()

    assert len(items) >= 1
    item = items[0]
    for key in ("id", "text", "likes", "comments", "reach", "created_at"):
        assert key in item, f"Missing key: {key}"


# ---------------------------------------------------------------------------
# Test 3: dedup skips already-processed IDs
# ---------------------------------------------------------------------------


def test_dedup_skips_processed_ids(vault, sample_fb_post):
    """Items in _processed_ids are skipped."""
    from src.watchers.facebook_watcher import FacebookWatcher

    _write_mock_post(vault, sample_fb_post)
    watcher = FacebookWatcher(vault_root=str(vault), dev_mode=True)
    watcher._processed_ids.add(sample_fb_post["id"])
    items = watcher.check_for_updates()

    processed = [i for i in items if i["id"] == sample_fb_post["id"]]
    assert len(processed) == 0


# ---------------------------------------------------------------------------
# Test 4: create_action_file writes correct path
# ---------------------------------------------------------------------------


def test_create_action_file_writes_inbox(vault, sample_fb_post):
    """create_action_file writes vault/Inbox/FB_ENGAGEMENT_{id}_{ts}.md."""
    from src.watchers.facebook_watcher import FacebookWatcher

    watcher = FacebookWatcher(vault_root=str(vault), dev_mode=True)
    path = watcher.create_action_file(str(vault), sample_fb_post)

    assert os.path.exists(path)
    assert "FB_ENGAGEMENT" in os.path.basename(path)
    assert sample_fb_post["id"] in os.path.basename(path)


# ---------------------------------------------------------------------------
# Test 5: frontmatter has type: social_media_engagement, source: facebook
# ---------------------------------------------------------------------------


def test_create_action_file_frontmatter(vault, sample_fb_post):
    """Frontmatter has type: social_media_engagement, source: facebook."""
    import yaml
    from src.watchers.facebook_watcher import FacebookWatcher

    watcher = FacebookWatcher(vault_root=str(vault), dev_mode=True)
    path = watcher.create_action_file(str(vault), sample_fb_post)

    with open(path, encoding="utf-8") as f:
        content = f.read()

    parts = content.split("---")
    assert len(parts) >= 3
    meta = yaml.safe_load(parts[1])
    assert meta.get("type") == "social_media_engagement"
    assert meta.get("source") == "facebook"


# ---------------------------------------------------------------------------
# Test 6: AUTH error sets _paused=True
# ---------------------------------------------------------------------------


def test_auth_error_sets_paused(vault):
    """Mock PermissionError with error_category=ErrorCategory.AUTH sets _paused=True."""
    from src.core.retry_handler import ErrorCategory
    from src.watchers.facebook_watcher import FacebookWatcher

    watcher = FacebookWatcher(vault_root=str(vault), dev_mode=False)

    auth_err = PermissionError("401 Unauthorized")
    auth_err.error_category = ErrorCategory.AUTH

    with patch.object(watcher, "_fetch_live", side_effect=auth_err):
        result = watcher.check_for_updates()

    assert watcher._paused is True
    assert result == []


# ---------------------------------------------------------------------------
# Test 7: dev_mode does not call requests.get
# ---------------------------------------------------------------------------


def test_dev_mode_no_requests_get(vault, sample_fb_post):
    """dev_mode does not call requests.get."""
    from src.watchers.facebook_watcher import FacebookWatcher

    _write_mock_post(vault, sample_fb_post)
    watcher = FacebookWatcher(vault_root=str(vault), dev_mode=True)

    with patch("requests.get") as mock_get:
        watcher.check_for_updates()
        mock_get.assert_not_called()


# ---------------------------------------------------------------------------
# Test 8: non-dev mode mock returns items from _load_mock_items
# ---------------------------------------------------------------------------


def test_non_dev_mock_returns_items(vault, sample_fb_post):
    """Non-dev mode mock returns items from _load_mock_items when requests mocked."""
    from src.watchers.facebook_watcher import FacebookWatcher

    watcher = FacebookWatcher(vault_root=str(vault), dev_mode=False)

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "data": [
            {
                "id": "fb001",
                "message": "Test post",
                "likes": {"summary": {"total_count": 10}},
                "comments": {"summary": {"total_count": 2}},
                "created_time": "2026-02-24T09:00:00Z",
            }
        ]
    }

    with patch("requests.get", return_value=mock_response):
        items = watcher.check_for_updates()

    assert isinstance(items, list)
    assert len(items) >= 1
