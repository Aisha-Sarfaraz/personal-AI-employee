"""Tests for detect_lead skill — TDD Red Phase (Phase 6, T028)."""

from __future__ import annotations

import os

import pytest
import yaml


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_needs_action_item(vault, filename: str, metadata: dict, body: str = "") -> str:
    """Write a frontmatter .md file to vault/Needs_Action/."""
    folder = os.path.join(str(vault), "Needs_Action")
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, filename)
    front = yaml.dump(metadata, default_flow_style=False)
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"---\n{front}---\n\n{body}")
    return path


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def vault(tmp_path):
    (tmp_path / "Needs_Action").mkdir()
    (tmp_path / "Logs").mkdir()
    (tmp_path / "state").mkdir()
    return tmp_path


# ---------------------------------------------------------------------------
# T028.1  detects lead with two keywords
# ---------------------------------------------------------------------------


def test_detects_lead_with_two_keywords(vault):
    """Item with ≥2 lead keywords is detected and upgraded."""
    from src.skills.detect_lead import run

    _write_needs_action_item(vault, "item1.md", {
        "id": "item1", "type": "email", "priority": "MEDIUM", "source": "gmail",
        "status": "triaged",
    }, body="I'm interested in your pricing and want to buy your product.")

    result = run(str(vault))

    assert result["leads_detected"] >= 1


def test_does_not_detect_lead_with_one_keyword(vault):
    """Item with only 1 lead keyword is NOT upgraded to lead."""
    from src.skills.detect_lead import run

    _write_needs_action_item(vault, "item2.md", {
        "id": "item2", "type": "email", "priority": "MEDIUM", "source": "email",
        "status": "triaged",
    }, body="Good morning, I am interested in your service.")

    result = run(str(vault))

    assert result["leads_detected"] == 0


# ---------------------------------------------------------------------------
# T028.3 / T028.4  upgrades type and priority
# ---------------------------------------------------------------------------


def test_upgrades_type_to_lead(vault):
    """On detection, item frontmatter type is updated to 'lead'."""
    from src.skills.detect_lead import run

    path = _write_needs_action_item(vault, "item3.md", {
        "id": "item3", "type": "email", "priority": "MEDIUM", "source": "gmail",
        "status": "triaged",
    }, body="Interested in buying your consulting package, need a quote.")

    run(str(vault))

    with open(path, encoding="utf-8") as f:
        content = f.read()

    # Parse updated frontmatter
    parts = content.split("---")
    updated_meta = yaml.safe_load(parts[1])
    assert updated_meta["type"] == "lead"


def test_upgrades_priority_to_critical(vault):
    """On detection, item frontmatter priority is updated to 'CRITICAL'."""
    from src.skills.detect_lead import run

    path = _write_needs_action_item(vault, "item4.md", {
        "id": "item4", "type": "email", "priority": "MEDIUM", "source": "gmail",
        "status": "triaged",
    }, body="Looking to purchase your services, interested in pricing.")

    run(str(vault))

    with open(path, encoding="utf-8") as f:
        content = f.read()

    parts = content.split("---")
    updated_meta = yaml.safe_load(parts[1])
    assert updated_meta["priority"] == "CRITICAL"


# ---------------------------------------------------------------------------
# T028.5  lead score calculation
# ---------------------------------------------------------------------------


def test_calculates_lead_score_correctly(vault):
    """Lead score reflects keyword count (1 per keyword, cap 10)."""
    from src.skills.detect_lead import run

    path = _write_needs_action_item(vault, "item5.md", {
        "id": "item5", "type": "email", "priority": "MEDIUM", "source": "email",
        "status": "triaged",
    }, body="Interested in pricing for your product. Want to buy and get a quote.")

    run(str(vault))

    with open(path, encoding="utf-8") as f:
        content = f.read()
    parts = content.split("---")
    updated_meta = yaml.safe_load(parts[1])

    assert "lead_score" in updated_meta
    assert updated_meta["lead_score"] >= 3  # interested + pricing + buy/quote


# ---------------------------------------------------------------------------
# T028.6  gmail source adds 2 bonus points
# ---------------------------------------------------------------------------


def test_gmail_source_adds_two_points(vault):
    """Gmail source items get 2 bonus points in lead_score."""
    from src.skills.detect_lead import run

    path_gmail = _write_needs_action_item(vault, "gmail_lead.md", {
        "id": "glead", "type": "email", "priority": "MEDIUM", "source": "gmail",
        "status": "triaged",
    }, body="Interested in buying your product.")

    path_email = _write_needs_action_item(vault, "email_lead.md", {
        "id": "elead", "type": "email", "priority": "MEDIUM", "source": "email",
        "status": "triaged",
    }, body="Interested in buying your product.")

    run(str(vault))

    def get_score(path):
        with open(path, encoding="utf-8") as f:
            parts = f.read().split("---")
        return yaml.safe_load(parts[1]).get("lead_score", 0)

    gmail_score = get_score(path_gmail)
    email_score = get_score(path_email)

    assert gmail_score == email_score + 2


# ---------------------------------------------------------------------------
# T028.7  skips items already type:lead
# ---------------------------------------------------------------------------


def test_skips_items_already_lead(vault):
    """Items with type:lead are not re-processed."""
    from src.skills.detect_lead import run

    _write_needs_action_item(vault, "already_lead.md", {
        "id": "alead", "type": "lead", "priority": "CRITICAL", "source": "gmail",
        "status": "triaged", "lead_score": 5,
    }, body="Interested in buying, pricing, quote please.")

    result = run(str(vault))

    assert result["skipped"] >= 1
    assert result["leads_detected"] == 0


# ---------------------------------------------------------------------------
# T028.8  result dict structure
# ---------------------------------------------------------------------------


def test_returns_correct_result_dict(vault):
    """run() returns dict with keys: processed, leads_detected, errors, skipped."""
    from src.skills.detect_lead import run

    result = run(str(vault))

    for key in ("processed", "leads_detected", "errors", "skipped"):
        assert key in result, f"Missing key: {key}"
    assert isinstance(result["processed"], int)
    assert isinstance(result["leads_detected"], int)
    assert isinstance(result["errors"], int)
    assert isinstance(result["skipped"], int)
