"""Tests for TwitterWatcher — TDD Phase 9, T040."""

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
    (tmp_path / "Watch" / "twitter_mock").mkdir(parents=True)
    (tmp_path / "Inbox").mkdir()
    (tmp_path / "state").mkdir()
    return tmp_path


@pytest.fixture()
def sample_tweet():
    return {
        "id": "tw001",
        "text": "Big announcement!",
        "retweet_count": 5,
        "like_count": 28,
        "reply_count": 3,
        "created_at": "2026-02-24T08:00:00Z",
    }


def _write_mock_tweet(vault, tweet_data):
    mock_dir = os.path.join(str(vault), "Watch", "twitter_mock")
    with open(os.path.join(mock_dir, "sample_tweet.json"), "w") as f:
        json.dump([tweet_data], f)


# ---------------------------------------------------------------------------
# Test 1: dev_mode reads twitter_mock, returns list
# ---------------------------------------------------------------------------


def test_dev_mode_reads_twitter_mock(vault, sample_tweet):
    """check_for_updates with dev_mode=True reads twitter_mock folder, returns list."""
    from src.watchers.twitter_watcher import TwitterWatcher

    _write_mock_tweet(vault, sample_tweet)
    watcher = TwitterWatcher(vault_root=str(vault), dev_mode=True)
    items = watcher.check_for_updates()

    assert isinstance(items, list)
    assert len(items) >= 1


# ---------------------------------------------------------------------------
# Test 2: items have required keys
# ---------------------------------------------------------------------------


def test_items_have_required_keys(vault, sample_tweet):
    """Each item has keys: id, text, retweet_count, like_count, reply_count, created_at."""
    from src.watchers.twitter_watcher import TwitterWatcher

    _write_mock_tweet(vault, sample_tweet)
    watcher = TwitterWatcher(vault_root=str(vault), dev_mode=True)
    items = watcher.check_for_updates()

    assert len(items) >= 1
    item = items[0]
    for key in ("id", "text", "retweet_count", "like_count", "reply_count", "created_at"):
        assert key in item, f"Missing key: {key}"


# ---------------------------------------------------------------------------
# Test 3: dedup skips already-processed IDs
# ---------------------------------------------------------------------------


def test_dedup_skips_processed_ids(vault, sample_tweet):
    """Items in _processed_ids are skipped."""
    from src.watchers.twitter_watcher import TwitterWatcher

    _write_mock_tweet(vault, sample_tweet)
    watcher = TwitterWatcher(vault_root=str(vault), dev_mode=True)
    watcher._processed_ids.add(sample_tweet["id"])
    items = watcher.check_for_updates()

    processed = [i for i in items if i["id"] == sample_tweet["id"]]
    assert len(processed) == 0


# ---------------------------------------------------------------------------
# Test 4: create_action_file writes correct path
# ---------------------------------------------------------------------------


def test_create_action_file_writes_inbox(vault, sample_tweet):
    """create_action_file writes vault/Inbox/TW_ENGAGEMENT_{id}_{ts}.md."""
    from src.watchers.twitter_watcher import TwitterWatcher

    watcher = TwitterWatcher(vault_root=str(vault), dev_mode=True)
    path = watcher.create_action_file(str(vault), sample_tweet)

    assert os.path.exists(path)
    assert "TW_ENGAGEMENT" in os.path.basename(path)
    assert sample_tweet["id"] in os.path.basename(path)


# ---------------------------------------------------------------------------
# Test 5: frontmatter has type: social_media_engagement, source: twitter
# ---------------------------------------------------------------------------


def test_create_action_file_frontmatter(vault, sample_tweet):
    """Frontmatter has type: social_media_engagement, source: twitter."""
    import yaml
    from src.watchers.twitter_watcher import TwitterWatcher

    watcher = TwitterWatcher(vault_root=str(vault), dev_mode=True)
    path = watcher.create_action_file(str(vault), sample_tweet)

    with open(path, encoding="utf-8") as f:
        content = f.read()

    parts = content.split("---")
    assert len(parts) >= 3
    meta = yaml.safe_load(parts[1])
    assert meta.get("type") == "social_media_engagement"
    assert meta.get("source") == "twitter"


# ---------------------------------------------------------------------------
# Test 6: tweepy.Client used for live reads (mock)
# ---------------------------------------------------------------------------


def test_tweepy_client_used_for_reads(vault):
    """tweepy.Client used for live reads (mock)."""
    from src.watchers.twitter_watcher import TwitterWatcher

    watcher = TwitterWatcher(vault_root=str(vault), dev_mode=False)

    mock_tweet = MagicMock()
    mock_tweet.id = "tw_live_001"
    mock_tweet.text = "Live tweet"
    mock_tweet.public_metrics = {
        "retweet_count": 2,
        "like_count": 10,
        "reply_count": 1,
    }
    mock_tweet.created_at = None

    mock_response = MagicMock()
    mock_response.data = [mock_tweet]

    mock_client = MagicMock()
    mock_client.get_users_tweets.return_value = mock_response

    with patch("src.watchers.twitter_watcher.tweepy") as mock_tweepy:
        mock_tweepy.Client.return_value = mock_client
        items = watcher.check_for_updates()

    assert mock_tweepy.Client.called


# ---------------------------------------------------------------------------
# Test 7: AUTH error sets _paused=True
# ---------------------------------------------------------------------------


def test_auth_error_sets_paused(vault):
    """AUTH error pauses watcher."""
    from src.core.retry_handler import ErrorCategory
    from src.watchers.twitter_watcher import TwitterWatcher

    watcher = TwitterWatcher(vault_root=str(vault), dev_mode=False)

    auth_err = PermissionError("401 Unauthorized")
    auth_err.error_category = ErrorCategory.AUTH

    with patch.object(watcher, "_fetch_live", side_effect=auth_err):
        result = watcher.check_for_updates()

    assert watcher._paused is True
    assert result == []


# ---------------------------------------------------------------------------
# Test 8: dev_mode does not call tweepy.Client
# ---------------------------------------------------------------------------


def test_dev_mode_no_tweepy_call(vault, sample_tweet):
    """dev_mode does not call tweepy.Client."""
    from src.watchers.twitter_watcher import TwitterWatcher

    _write_mock_tweet(vault, sample_tweet)
    watcher = TwitterWatcher(vault_root=str(vault), dev_mode=True)

    with patch("src.watchers.twitter_watcher.tweepy") as mock_tweepy:
        watcher.check_for_updates()
        mock_tweepy.Client.assert_not_called()
