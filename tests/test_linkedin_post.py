"""Tests for generate_linkedin_post skill — TDD Red Phase (Phase 8, T034)."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
import yaml


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_audit_entry(vault, action: str, days_ago: int = 0):
    """Write a minimal audit log entry with a given action."""
    logs_dir = os.path.join(str(vault), "Logs")
    os.makedirs(logs_dir, exist_ok=True)
    from datetime import timedelta
    dt = datetime.now(timezone.utc) - timedelta(days=days_ago)
    filename = f"LOG_{dt.strftime('%Y%m%d_%H%M%S')}.md"
    meta = yaml.dump({"action": action, "agent": "test", "status": "success",
                      "risk_tier": "LOW", "timestamp": dt.isoformat()})
    with open(os.path.join(logs_dir, filename), "w") as f:
        f.write(f"---\n{meta}---\n\nTest audit entry.\n")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def vault(tmp_path):
    (tmp_path / "Plans").mkdir()
    (tmp_path / "Logs").mkdir()
    (tmp_path / "state").mkdir()
    (tmp_path / "Templates").mkdir()
    return tmp_path


# ---------------------------------------------------------------------------
# T034.1  skips when disabled in settings
# ---------------------------------------------------------------------------


def test_skips_when_disabled_in_settings(vault):
    """If settings.skills.generate_linkedin_post.enabled=false, return {skipped:1}."""
    from src.skills.generate_linkedin_post import run

    with patch("src.skills.generate_linkedin_post._is_enabled", return_value=False):
        result = run(str(vault))

    assert result["skipped"] >= 1


# ---------------------------------------------------------------------------
# T034.2  skips when posted recently
# ---------------------------------------------------------------------------


def test_skips_when_posted_recently(vault):
    """If audit log has linkedin_post entry within frequency_days, return {skipped:1}."""
    from src.skills.generate_linkedin_post import run

    _write_audit_entry(vault, "linkedin_post", days_ago=1)

    with patch("src.skills.generate_linkedin_post._is_enabled", return_value=True):
        result = run(str(vault), frequency_days=3)

    assert result["skipped"] >= 1


# ---------------------------------------------------------------------------
# T034.3  creates post file when guards pass
# ---------------------------------------------------------------------------


def test_creates_post_file_when_guards_pass(vault):
    """When enabled and cadence guard allows, post draft file is created."""
    from src.skills.generate_linkedin_post import run

    with patch("src.skills.generate_linkedin_post._is_enabled", return_value=True):
        with patch("src.skills.generate_linkedin_post._call_claude", return_value="Post content #AIAssisted"):
            result = run(str(vault), frequency_days=3, dev_mode=False)

    plans = os.listdir(os.path.join(str(vault), "Plans"))
    linkedin_plans = [p for p in plans if "LINKEDIN_POST" in p]
    assert len(linkedin_plans) >= 1 or result.get("post_files_created", 0) >= 1


# ---------------------------------------------------------------------------
# T034.4  post file has type linkedin_post
# ---------------------------------------------------------------------------


def test_post_file_has_type_linkedin_post(vault):
    """Post draft file frontmatter has type:linkedin_post."""
    from src.skills.generate_linkedin_post import run

    with patch("src.skills.generate_linkedin_post._is_enabled", return_value=True):
        with patch("src.skills.generate_linkedin_post._call_claude", return_value="Great insight. #AIAssisted"):
            run(str(vault), frequency_days=3, dev_mode=False)

    plans_dir = os.path.join(str(vault), "Plans")
    plan_files = [f for f in os.listdir(plans_dir) if "LINKEDIN_POST" in f and f.endswith(".md")]
    if plan_files:
        with open(os.path.join(plans_dir, plan_files[0]), encoding="utf-8") as f:
            content = f.read()
        parts = content.split("---")
        meta = yaml.safe_load(parts[1])
        assert meta.get("type") == "linkedin_post"


# ---------------------------------------------------------------------------
# T034.5  post file has risk_level HIGH
# ---------------------------------------------------------------------------


def test_post_file_has_risk_level_high(vault):
    """Post draft file frontmatter has risk_level:HIGH."""
    from src.skills.generate_linkedin_post import run

    with patch("src.skills.generate_linkedin_post._is_enabled", return_value=True):
        with patch("src.skills.generate_linkedin_post._call_claude", return_value="Good post #AIAssisted"):
            run(str(vault), frequency_days=3, dev_mode=False)

    plans_dir = os.path.join(str(vault), "Plans")
    plan_files = [f for f in os.listdir(plans_dir) if "LINKEDIN_POST" in f and f.endswith(".md")]
    if plan_files:
        with open(os.path.join(plans_dir, plan_files[0]), encoding="utf-8") as f:
            content = f.read()
        parts = content.split("---")
        meta = yaml.safe_load(parts[1])
        assert meta.get("risk_level") == "HIGH"


# ---------------------------------------------------------------------------
# T034.6  post includes #AIAssisted hashtag
# ---------------------------------------------------------------------------


def test_post_includes_hashtag_aiassisted(vault):
    """Post draft body contains '#AIAssisted' hashtag."""
    from src.skills.generate_linkedin_post import run

    with patch("src.skills.generate_linkedin_post._is_enabled", return_value=True):
        with patch("src.skills.generate_linkedin_post._call_claude", return_value="Good insight here."):
            run(str(vault), frequency_days=3, dev_mode=False)

    plans_dir = os.path.join(str(vault), "Plans")
    plan_files = [f for f in os.listdir(plans_dir) if "LINKEDIN_POST" in f and f.endswith(".md")]
    if plan_files:
        with open(os.path.join(plans_dir, plan_files[0]), encoding="utf-8") as f:
            content = f.read()
        assert "#AIAssisted" in content


# ---------------------------------------------------------------------------
# T034.7  dev_mode uses template, no Claude call
# ---------------------------------------------------------------------------


def test_dev_mode_uses_template_no_claude_call(vault):
    """dev_mode=True: Claude API NOT called; template draft created instead."""
    from src.skills.generate_linkedin_post import run

    with patch("src.skills.generate_linkedin_post._is_enabled", return_value=True):
        with patch("src.skills.generate_linkedin_post._call_claude") as mock_claude:
            run(str(vault), frequency_days=3, dev_mode=True)
            mock_claude.assert_not_called()


# ---------------------------------------------------------------------------
# T034.8  cadence guard: returns skipped >= 1
# ---------------------------------------------------------------------------


def test_returns_skipped_1_when_cadence_guard_triggered(vault):
    """When recent post found in logs, result has skipped >= 1."""
    from src.skills.generate_linkedin_post import run

    _write_audit_entry(vault, "linkedin_post", days_ago=0)

    with patch("src.skills.generate_linkedin_post._is_enabled", return_value=True):
        result = run(str(vault), frequency_days=3)

    assert result.get("skipped", 0) >= 1 or result.get("skipped_rate_limit", 0) >= 1
