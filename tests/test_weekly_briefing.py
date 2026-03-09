"""Tests for weekly_briefing skill — TDD Red Phase (Phase 9, T037)."""

from __future__ import annotations

import os
from datetime import date, datetime, timedelta, timezone
from unittest.mock import patch

import pytest
import yaml


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _monday_of_week(d: date | None = None) -> date:
    d = d or date.today()
    return d - timedelta(days=d.weekday())


def _write_log_entry(vault, action: str, agent: str = "test", days_ago: int = 1):
    """Write a minimal audit log markdown file."""
    logs_dir = os.path.join(str(vault), "Logs")
    os.makedirs(logs_dir, exist_ok=True)
    dt = datetime.now(timezone.utc) - timedelta(days=days_ago)
    filename = f"LOG_{dt.strftime('%Y%m%d_%H%M%S_%f')}.md"
    meta = {
        "action": action,
        "agent": agent,
        "status": "success",
        "risk_tier": "LOW",
        "timestamp": dt.isoformat(),
    }
    front = yaml.dump(meta, default_flow_style=False)
    with open(os.path.join(logs_dir, filename), "w", encoding="utf-8") as f:
        f.write(f"---\n{front}---\n\nTest entry.\n")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def vault(tmp_path):
    (tmp_path / "Briefings").mkdir()
    (tmp_path / "Logs").mkdir()
    (tmp_path / "state").mkdir()
    return tmp_path


# ---------------------------------------------------------------------------
# T037.1  skips on non-Monday
# ---------------------------------------------------------------------------


def test_skips_on_non_monday(vault):
    """run() returns skipped=1 when called on a non-Monday."""
    from src.skills.weekly_briefing import run

    # Find a Tuesday
    today = date.today()
    days_to_tuesday = (1 - today.weekday()) % 7 or 7  # days until next Tuesday
    tuesday = today + timedelta(days=days_to_tuesday)
    if tuesday.weekday() != 1:
        tuesday = today - timedelta(days=(today.weekday() - 1) % 7)

    with patch("src.skills.weekly_briefing._today", return_value=tuesday):
        result = run(str(vault))

    assert result["skipped"] == 1


# ---------------------------------------------------------------------------
# T037.2  skips if briefing already exists
# ---------------------------------------------------------------------------


def test_skips_if_briefing_already_exists(vault):
    """run() returns skipped=1 if BRIEFING_{monday}.md already exists."""
    from src.skills.weekly_briefing import run

    monday = _monday_of_week()
    briefing_path = os.path.join(str(vault), "Briefings", f"BRIEFING_{monday}.md")
    with open(briefing_path, "w") as f:
        f.write("# Existing briefing\n")

    with patch("src.skills.weekly_briefing._today", return_value=monday):
        result = run(str(vault))

    assert result["skipped"] == 1


# ---------------------------------------------------------------------------
# T037.3  creates briefing on Monday
# ---------------------------------------------------------------------------


def test_creates_briefing_on_monday(vault):
    """On Monday, run() creates BRIEFING_{date}.md in vault/Briefings/."""
    from src.skills.weekly_briefing import run

    monday = _monday_of_week(date(2026, 2, 23))  # known Monday

    with patch("src.skills.weekly_briefing._today", return_value=monday):
        result = run(str(vault))

    assert result["skipped"] == 0
    briefing_path = os.path.join(str(vault), "Briefings", f"BRIEFING_{monday}.md")
    assert os.path.exists(briefing_path), f"Expected {briefing_path} to exist"


# ---------------------------------------------------------------------------
# T037.4  briefing has all 9 required sections
# ---------------------------------------------------------------------------

_REQUIRED_SECTIONS = [
    "Date Range",
    "Items by Channel",
    "Leads Detected",
    "Emails Sent",
    "LinkedIn Activity",
    "Plans Summary",
    "Approvals",
    "Quarantine",
    "Next Week",
]


def test_briefing_has_all_nine_required_sections(vault):
    """Generated briefing must contain all 9 required section headings."""
    from src.skills.weekly_briefing import run

    monday = _monday_of_week(date(2026, 2, 23))

    with patch("src.skills.weekly_briefing._today", return_value=monday):
        run(str(vault))

    briefing_path = os.path.join(str(vault), "Briefings", f"BRIEFING_{monday}.md")
    with open(briefing_path, encoding="utf-8") as f:
        content = f.read()

    for section in _REQUIRED_SECTIONS:
        assert section in content, f"Section '{section}' not found in briefing"


# ---------------------------------------------------------------------------
# T037.5  aggregates items by channel
# ---------------------------------------------------------------------------


def test_aggregates_items_by_channel(vault):
    """Briefing aggregates log entries by agent/channel."""
    from src.skills.weekly_briefing import run

    _write_log_entry(vault, "sent_email", agent="action_executor", days_ago=2)
    _write_log_entry(vault, "lead_detected", agent="detect_lead", days_ago=3)

    monday = _monday_of_week(date(2026, 2, 23))

    with patch("src.skills.weekly_briefing._today", return_value=monday):
        result = run(str(vault))

    assert result["processed"] >= 1


# ---------------------------------------------------------------------------
# T037.6  returns correct result dict
# ---------------------------------------------------------------------------


def test_returns_correct_result_dict(vault):
    """run() returns dict with keys: processed, briefing_file, week_start, errors, skipped."""
    from src.skills.weekly_briefing import run

    monday = _monday_of_week(date(2026, 2, 23))

    with patch("src.skills.weekly_briefing._today", return_value=monday):
        result = run(str(vault))

    for key in ("processed", "briefing_file", "week_start", "errors", "skipped"):
        assert key in result, f"Missing key: {key}"


# ---------------------------------------------------------------------------
# T037.7  template fallback when no API key
# ---------------------------------------------------------------------------


def test_template_fallback_when_no_api_key(vault, monkeypatch):
    """Without ANTHROPIC_API_KEY, briefing is generated without error."""
    from src.skills.weekly_briefing import run

    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monday = _monday_of_week(date(2026, 2, 23))

    with patch("src.skills.weekly_briefing._today", return_value=monday):
        result = run(str(vault))

    assert result["errors"] == [] or result["errors"] == 0
    assert result["briefing_file"] is not None


# ---------------------------------------------------------------------------
# T037.8  does not modify vault items — reads Logs/ only
# ---------------------------------------------------------------------------


def test_does_not_reprocess_vault_items(vault):
    """weekly_briefing.run() only reads from Logs/ — does not write to Needs_Action/ etc."""
    from src.skills.weekly_briefing import run

    # Create a Needs_Action item
    na_dir = os.path.join(str(vault), "Needs_Action")
    os.makedirs(na_dir, exist_ok=True)
    item_path = os.path.join(na_dir, "test_item.md")
    with open(item_path, "w") as f:
        f.write("---\nid: test\ntype: email\nstatus: triaged\n---\n\nBody\n")

    monday = _monday_of_week(date(2026, 2, 23))

    with patch("src.skills.weekly_briefing._today", return_value=monday):
        run(str(vault))

    # Needs_Action item must not have been modified
    with open(item_path, encoding="utf-8") as f:
        content = f.read()
    assert "triaged" in content  # status unchanged
