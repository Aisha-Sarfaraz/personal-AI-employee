"""SC-024: Facebook Post Approval flow — integration test, Phase 8, T039."""

from __future__ import annotations

import json
import os
from unittest.mock import MagicMock, patch

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
# SC-024.1 dev_mode + facebook.enabled: true → creates approval file
# ---------------------------------------------------------------------------


def test_sc024_creates_approval_file(vault):
    """dev_mode + facebook.enabled: true; post_facebook.run() creates approval file."""
    from src.skills.post_facebook import run

    with patch("src.skills.post_facebook._load_settings", return_value={"facebook": {"enabled": True, "frequency_days": 3}}):
        with patch("src.skills.post_facebook._draft_post", return_value="Great Q1 results! #AIAssisted"):
            result = run(str(vault), dev_mode=True)

    assert result.get("created") == 1
    assert os.path.exists(result["approval_file"])

    parts = open(result["approval_file"], encoding="utf-8").read().split("---")
    meta = yaml.safe_load(parts[1])
    assert meta["risk_level"] == "HIGH"
    assert "facebook" in meta["platforms"]
    assert "instagram" in meta["platforms"]


# ---------------------------------------------------------------------------
# SC-024.2 429 from mocked Meta API: retried, audit result: failure on exhaustion
# ---------------------------------------------------------------------------


def test_sc024_429_retry_and_failure(vault):
    """429 from mocked Meta API: retried 3 times, raises after exhaustion."""
    from src.skills.post_facebook import _publish_facebook

    call_count = 0

    def mock_post(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        resp = MagicMock()
        resp.status_code = 429
        resp.raise_for_status.side_effect = Exception("429 Too Many Requests")
        return resp

    with patch("requests.post", side_effect=mock_post):
        with pytest.raises(Exception):
            _publish_facebook("Test post", "page_id", "token")

    # Should have retried 3 times
    assert call_count == 3


# ---------------------------------------------------------------------------
# SC-024.3 approval file frontmatter is valid YAML with all required fields
# ---------------------------------------------------------------------------


def test_sc024_approval_file_valid_yaml(vault):
    """Approval file has valid YAML frontmatter with all required fields."""
    from src.skills.post_facebook import run

    with patch("src.skills.post_facebook._load_settings", return_value={"facebook": {"enabled": True, "frequency_days": 3}}):
        with patch("src.skills.post_facebook._draft_post", return_value="Post text"):
            result = run(str(vault), dev_mode=True)

    with open(result["approval_file"], encoding="utf-8") as f:
        content = f.read()

    parts = content.split("---")
    assert len(parts) >= 3
    meta = yaml.safe_load(parts[1])

    required_fields = ["type", "platforms", "draft_text", "character_count", "risk_level"]
    for field in required_fields:
        assert field in meta, f"Missing field: {field}"
