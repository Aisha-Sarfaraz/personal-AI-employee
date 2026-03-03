"""Tests for post_facebook skill — TDD Phase 8, T037."""

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


def _write_settings(vault, facebook_enabled=True, frequency_days=3):
    config_dir = os.path.join(str(vault), "..", "config")
    os.makedirs(config_dir, exist_ok=True)
    settings = {
        "facebook": {
            "enabled": facebook_enabled,
            "frequency_days": frequency_days,
        },
        "twitter": {"enabled": False},
    }
    with open(os.path.join(config_dir, "settings.yaml"), "w") as f:
        yaml.dump(settings, f)


def _write_recent_log(vault, action_type: str, days_ago: int = 0):
    """Write a JSON log entry for recent post check."""
    from datetime import timedelta
    dt = datetime.now(timezone.utc) - timedelta(days=days_ago)
    log_file = os.path.join(str(vault), "Logs", f"{dt.strftime('%Y-%m-%d')}.json")
    entry = {
        "timestamp": dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "action_type": action_type,
        "actor": "post_facebook",
        "target": "facebook",
        "parameters": {},
        "approval_status": "auto",
        "approved_by": "system",
        "result": "success",
        "error": None,
    }
    with open(log_file, "a") as f:
        f.write(json.dumps(entry) + "\n")


# ---------------------------------------------------------------------------
# Test 1: disabled returns {skipped:1, reason:"disabled"}
# ---------------------------------------------------------------------------


def test_disabled_returns_skipped(vault):
    """run() returns {skipped:1, reason:'disabled'} when facebook.enabled not set/false."""
    from src.skills.post_facebook import run

    with patch("src.skills.post_facebook._load_settings", return_value={"facebook": {"enabled": False}}):
        result = run(str(vault))

    assert result.get("skipped") == 1
    assert result.get("reason") == "disabled"


# ---------------------------------------------------------------------------
# Test 2: too_soon returns {skipped:1, reason:"too_soon"}
# ---------------------------------------------------------------------------


def test_too_soon_returns_skipped(vault):
    """run() returns {skipped:1, reason:'too_soon'} when last post within frequency_days."""
    from src.skills.post_facebook import run

    _write_recent_log(vault, "post_facebook", days_ago=1)

    with patch("src.skills.post_facebook._load_settings", return_value={"facebook": {"enabled": True, "frequency_days": 3}}):
        result = run(str(vault))

    assert result.get("skipped") == 1
    assert result.get("reason") == "too_soon"


# ---------------------------------------------------------------------------
# Test 3: enabled + not too soon returns {created:1, approval_file:...}
# ---------------------------------------------------------------------------


def test_enabled_creates_approval_file(vault):
    """run() returns {created:1, approval_file:...} when enabled + not too soon."""
    from src.skills.post_facebook import run

    with patch("src.skills.post_facebook._load_settings", return_value={"facebook": {"enabled": True, "frequency_days": 3}}):
        with patch("src.skills.post_facebook._draft_post", return_value="Test post content"):
            result = run(str(vault))

    assert result.get("created") == 1
    assert "approval_file" in result
    assert os.path.exists(result["approval_file"])


# ---------------------------------------------------------------------------
# Test 4: approval file has platforms: [facebook, instagram]
# ---------------------------------------------------------------------------


def test_approval_file_has_platforms(vault):
    """Approval file has platforms: [facebook, instagram] in content."""
    from src.skills.post_facebook import run

    with patch("src.skills.post_facebook._load_settings", return_value={"facebook": {"enabled": True, "frequency_days": 3}}):
        with patch("src.skills.post_facebook._draft_post", return_value="Test post"):
            result = run(str(vault))

    with open(result["approval_file"], encoding="utf-8") as f:
        content = f.read()

    assert "facebook" in content
    assert "instagram" in content


# ---------------------------------------------------------------------------
# Test 5: approval file has risk_level: HIGH
# ---------------------------------------------------------------------------


def test_approval_file_has_risk_level_high(vault):
    """Approval file has risk_level: HIGH."""
    from src.skills.post_facebook import run

    with patch("src.skills.post_facebook._load_settings", return_value={"facebook": {"enabled": True, "frequency_days": 3}}):
        with patch("src.skills.post_facebook._draft_post", return_value="Test post"):
            result = run(str(vault))

    parts = open(result["approval_file"], encoding="utf-8").read().split("---")
    meta = yaml.safe_load(parts[1])
    assert meta.get("risk_level") == "HIGH"


# ---------------------------------------------------------------------------
# Test 6: approval file has draft_text key
# ---------------------------------------------------------------------------


def test_approval_file_has_draft_text(vault):
    """Approval file frontmatter has draft_text key."""
    from src.skills.post_facebook import run

    with patch("src.skills.post_facebook._load_settings", return_value={"facebook": {"enabled": True, "frequency_days": 3}}):
        with patch("src.skills.post_facebook._draft_post", return_value="My draft text"):
            result = run(str(vault))

    parts = open(result["approval_file"], encoding="utf-8").read().split("---")
    meta = yaml.safe_load(parts[1])
    assert "draft_text" in meta


# ---------------------------------------------------------------------------
# Test 7: dev_mode: no requests.post call
# ---------------------------------------------------------------------------


def test_dev_mode_no_requests_post(vault):
    """dev_mode: no requests.post call."""
    from src.skills.post_facebook import run

    with patch("src.skills.post_facebook._load_settings", return_value={"facebook": {"enabled": True, "frequency_days": 3}}):
        with patch("src.skills.post_facebook._draft_post", return_value="Test"):
            with patch("requests.post") as mock_post:
                run(str(vault), dev_mode=True)
                mock_post.assert_not_called()


# ---------------------------------------------------------------------------
# Test 8: 429 error raises (retry applied)
# ---------------------------------------------------------------------------


def test_429_error_retried(vault):
    """Mock 429 error raises after retries exhausted."""
    from src.skills.post_facebook import _publish_facebook

    mock_response = MagicMock()
    mock_response.status_code = 429
    mock_response.raise_for_status.side_effect = Exception("429 Too Many Requests")

    with patch("requests.post", return_value=mock_response):
        with pytest.raises(Exception):
            _publish_facebook("Test post", "page_id_123", "token_xyz")


# ---------------------------------------------------------------------------
# Test 9: AUTH error creates META_AUTH_ALERT
# ---------------------------------------------------------------------------


def test_auth_error_creates_alert(vault):
    """AUTH error (401): creates vault/Inbox/META_AUTH_ALERT_*.md."""
    from src.core.retry_handler import ErrorCategory
    from src.skills.post_facebook import _handle_auth_error

    _handle_auth_error(str(vault), "401 Unauthorized")

    inbox = os.path.join(str(vault), "Inbox")
    alerts = [f for f in os.listdir(inbox) if f.startswith("META_AUTH_ALERT")]
    assert len(alerts) >= 1


# ---------------------------------------------------------------------------
# Test 10: template fallback used when ANTHROPIC_API_KEY not set
# ---------------------------------------------------------------------------


def test_template_fallback_no_api_key(vault):
    """Template fallback used when ANTHROPIC_API_KEY not set."""
    from src.skills.post_facebook import _draft_post

    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("ANTHROPIC_API_KEY", None)
        text = _draft_post(str(vault))

    assert isinstance(text, str)
    assert len(text) > 0
