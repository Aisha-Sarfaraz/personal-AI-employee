"""Tests for post_twitter skill — TDD Phase 9, T042."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
import yaml


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def vault(tmp_path):
    (tmp_path / "Pending_Approval").mkdir()
    (tmp_path / "Logs").mkdir()
    (tmp_path / "state").mkdir()
    (tmp_path / "Inbox").mkdir()
    return tmp_path


# ---------------------------------------------------------------------------
# Test 1: disabled returns {skipped:1, reason:"disabled"}
# ---------------------------------------------------------------------------


def test_disabled_returns_skipped(vault):
    """run() returns {skipped:1, reason:'disabled'} when twitter.enabled false."""
    from src.skills.post_twitter import run

    with patch("src.skills.post_twitter._load_settings", return_value={"twitter": {"enabled": False}}):
        result = run(str(vault))

    assert result.get("skipped") == 1
    assert result.get("reason") == "disabled"


# ---------------------------------------------------------------------------
# Test 2: rate_limit exceeded returns {skipped:1, reason:"rate_limit"}
# ---------------------------------------------------------------------------


def test_rate_limit_exceeded_returns_skipped(vault):
    """rate_limiter exceeded returns {skipped:1, reason:'rate_limit'}."""
    from src.skills.post_twitter import run

    with patch("src.skills.post_twitter._load_settings", return_value={"twitter": {"enabled": True, "tweets_per_day": 1}}):
        with patch("src.skills.post_twitter.rate_limiter.check_and_increment", return_value=False):
            result = run(str(vault))

    assert result.get("skipped") == 1
    assert result.get("reason") == "rate_limit"


# ---------------------------------------------------------------------------
# Test 3: enabled + under limit returns {created:1, approval_file:...}
# ---------------------------------------------------------------------------


def test_enabled_creates_approval_file(vault):
    """run() returns {created:1, approval_file:...} when enabled + under limit."""
    from src.skills.post_twitter import run

    with patch("src.skills.post_twitter._load_settings", return_value={"twitter": {"enabled": True, "tweets_per_day": 1}}):
        with patch("src.skills.post_twitter.rate_limiter.check_and_increment", return_value=True):
            with patch("src.skills.post_twitter._draft_tweet", return_value="Great news! #AI"):
                result = run(str(vault))

    assert result.get("created") == 1
    assert "approval_file" in result
    assert os.path.exists(result["approval_file"])


# ---------------------------------------------------------------------------
# Test 4: approval file has platforms: [twitter]
# ---------------------------------------------------------------------------


def test_approval_file_has_platforms_twitter(vault):
    """Approval file frontmatter has platforms: [twitter]."""
    from src.skills.post_twitter import run

    with patch("src.skills.post_twitter._load_settings", return_value={"twitter": {"enabled": True, "tweets_per_day": 1}}):
        with patch("src.skills.post_twitter.rate_limiter.check_and_increment", return_value=True):
            with patch("src.skills.post_twitter._draft_tweet", return_value="Tweet text"):
                result = run(str(vault))

    parts = open(result["approval_file"], encoding="utf-8").read().split("---")
    meta = yaml.safe_load(parts[1])
    assert "twitter" in meta.get("platforms", [])
    assert len(meta.get("platforms", [])) == 1


# ---------------------------------------------------------------------------
# Test 5: character_count <= 280
# ---------------------------------------------------------------------------


def test_character_count_le_280(vault):
    """Approval file character_count <= 280."""
    from src.skills.post_twitter import run

    with patch("src.skills.post_twitter._load_settings", return_value={"twitter": {"enabled": True, "tweets_per_day": 1}}):
        with patch("src.skills.post_twitter.rate_limiter.check_and_increment", return_value=True):
            with patch("src.skills.post_twitter._draft_tweet", return_value="Short tweet"):
                result = run(str(vault))

    parts = open(result["approval_file"], encoding="utf-8").read().split("---")
    meta = yaml.safe_load(parts[1])
    assert meta.get("character_count", 999) <= 280


# ---------------------------------------------------------------------------
# Test 6: tweet > 280 chars truncated to 277 + "..."
# ---------------------------------------------------------------------------


def test_long_tweet_truncated(vault):
    """Tweet > 280 chars truncated to 277 + '...'."""
    from src.skills.post_twitter import _enforce_tweet_limit

    long_text = "A" * 300
    result = _enforce_tweet_limit(long_text)

    assert len(result) <= 280
    assert result.endswith("...")


# ---------------------------------------------------------------------------
# Test 7: dev_mode no tweepy.Client.create_tweet call
# ---------------------------------------------------------------------------


def test_dev_mode_no_tweepy_call(vault):
    """dev_mode: no tweepy.Client.create_tweet call."""
    from src.skills.post_twitter import run

    with patch("src.skills.post_twitter._load_settings", return_value={"twitter": {"enabled": True, "tweets_per_day": 1}}):
        with patch("src.skills.post_twitter.rate_limiter.check_and_increment", return_value=True):
            with patch("src.skills.post_twitter._draft_tweet", return_value="Test tweet"):
                with patch("src.skills.post_twitter.tweepy") as mock_tweepy:
                    run(str(vault), dev_mode=True)
                    if mock_tweepy:
                        mock_tweepy.Client.assert_not_called()


# ---------------------------------------------------------------------------
# Test 8: AUTH error creates TWITTER_AUTH_ALERT
# ---------------------------------------------------------------------------


def test_auth_error_creates_alert(vault):
    """AUTH (Unauthorized): no retry + vault alert created."""
    from src.skills.post_twitter import _handle_auth_error

    _handle_auth_error(str(vault), "401 Unauthorized")

    inbox = os.path.join(str(vault), "Inbox")
    alerts = [f for f in os.listdir(inbox) if f.startswith("TWITTER_AUTH_ALERT")]
    assert len(alerts) >= 1


# ---------------------------------------------------------------------------
# Test 9: approval file has risk_level: HIGH
# ---------------------------------------------------------------------------


def test_approval_file_risk_level_high(vault):
    """Approval file has risk_level: HIGH."""
    from src.skills.post_twitter import run

    with patch("src.skills.post_twitter._load_settings", return_value={"twitter": {"enabled": True, "tweets_per_day": 1}}):
        with patch("src.skills.post_twitter.rate_limiter.check_and_increment", return_value=True):
            with patch("src.skills.post_twitter._draft_tweet", return_value="Test tweet"):
                result = run(str(vault))

    parts = open(result["approval_file"], encoding="utf-8").read().split("---")
    meta = yaml.safe_load(parts[1])
    assert meta.get("risk_level") == "HIGH"
