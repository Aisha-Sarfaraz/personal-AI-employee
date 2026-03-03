"""SC-025: Tweet Approval flow — integration test, Phase 9, T044."""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest
import yaml


@pytest.fixture()
def vault(tmp_path):
    (tmp_path / "Pending_Approval").mkdir()
    (tmp_path / "Approved").mkdir()
    (tmp_path / "Logs").mkdir()
    (tmp_path / "state").mkdir()
    (tmp_path / "Inbox").mkdir()
    return tmp_path


# ---------------------------------------------------------------------------
# SC-025.1 dev_mode + twitter.enabled: true → creates approval file with char_count <= 280
# ---------------------------------------------------------------------------


def test_sc025_creates_approval_file(vault):
    """dev_mode + twitter.enabled: true; post_twitter.run() creates approval file <= 280 chars."""
    from src.skills.post_twitter import run

    with patch("src.skills.post_twitter._load_settings", return_value={"twitter": {"enabled": True, "tweets_per_day": 1}}):
        with patch("src.skills.post_twitter.rate_limiter.check_and_increment", return_value=True):
            with patch("src.skills.post_twitter._draft_tweet", return_value="Test tweet! #AI"):
                result = run(str(vault), dev_mode=True)

    assert result.get("created") == 1
    assert os.path.exists(result["approval_file"])

    parts = open(result["approval_file"], encoding="utf-8").read().split("---")
    meta = yaml.safe_load(parts[1])
    assert meta.get("character_count", 999) <= 280
    assert meta.get("risk_level") == "HIGH"
    assert "twitter" in meta.get("platforms", [])


# ---------------------------------------------------------------------------
# SC-025.2 rate limit exceeded → returns {skipped:1, reason:"rate_limit"}
# ---------------------------------------------------------------------------


def test_sc025_rate_limit_skipped(vault):
    """Already tweeted today: returns {skipped:1, reason:'rate_limit'}."""
    from src.skills.post_twitter import run

    with patch("src.skills.post_twitter._load_settings", return_value={"twitter": {"enabled": True, "tweets_per_day": 1}}):
        with patch("src.skills.post_twitter.rate_limiter.check_and_increment", return_value=False):
            result = run(str(vault), dev_mode=True)

    assert result.get("skipped") == 1
    assert result.get("reason") == "rate_limit"


# ---------------------------------------------------------------------------
# SC-025.3 Approval file has valid YAML frontmatter
# ---------------------------------------------------------------------------


def test_sc025_approval_valid_yaml(vault):
    """Approval file frontmatter is valid YAML with all required fields."""
    from src.skills.post_twitter import run

    with patch("src.skills.post_twitter._load_settings", return_value={"twitter": {"enabled": True, "tweets_per_day": 1}}):
        with patch("src.skills.post_twitter.rate_limiter.check_and_increment", return_value=True):
            with patch("src.skills.post_twitter._draft_tweet", return_value="Tweet content"):
                result = run(str(vault), dev_mode=True)

    with open(result["approval_file"], encoding="utf-8") as f:
        content = f.read()

    parts = content.split("---")
    assert len(parts) >= 3
    meta = yaml.safe_load(parts[1])

    for field in ["type", "platforms", "draft_text", "character_count", "risk_level"]:
        assert field in meta, f"Missing field: {field}"
