"""Tests for generate_plan skill — TDD Red Phase (Phase 7, T031)."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest
import yaml


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_needs_action_item(vault, filename: str, metadata: dict, body: str = "") -> str:
    folder = os.path.join(str(vault), "Needs_Action")
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, filename)
    front = yaml.dump(metadata, default_flow_style=False)
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"---\n{front}---\n\n{body}")
    return path


def _count_plans(vault) -> int:
    plans_dir = os.path.join(str(vault), "Plans")
    if not os.path.isdir(plans_dir):
        return 0
    return len([f for f in os.listdir(plans_dir) if f.endswith(".md")])


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def vault(tmp_path):
    (tmp_path / "Needs_Action").mkdir()
    (tmp_path / "Plans").mkdir()
    (tmp_path / "Logs").mkdir()
    (tmp_path / "state").mkdir()
    return tmp_path


@pytest.fixture()
def item(vault):
    return _write_needs_action_item(vault, "item1.md", {
        "id": "item1", "type": "email", "priority": "MEDIUM", "source": "gmail", "status": "triaged",
    }, body="Please send me pricing information.")


# ---------------------------------------------------------------------------
# T031.1  calls plan_task.run
# ---------------------------------------------------------------------------


def test_calls_plan_task_run(vault, item):
    """generate_plan.run() must call plan_task.run() under the hood."""
    from src.skills.generate_plan import run

    with patch("src.skills.generate_plan.plan_task") as mock_pt:
        mock_pt.run.return_value = {"processed": 1, "errors": [], "skipped": 0}
        run(str(vault))
        mock_pt.run.assert_called_once_with(str(vault))


# ---------------------------------------------------------------------------
# T031.2  skips items that already have a plan
# ---------------------------------------------------------------------------


def test_skips_items_with_existing_plan(vault):
    """Items already with status:planned are skipped."""
    from src.skills.generate_plan import run

    _write_needs_action_item(vault, "planned.md", {
        "id": "planned", "type": "email", "priority": "LOW", "source": "email",
        "status": "planned",
    })

    result = run(str(vault))

    assert result["skipped"] >= 1


# ---------------------------------------------------------------------------
# T031.3  dev_mode: no Claude call, template plan returned
# ---------------------------------------------------------------------------


def test_dev_mode_returns_template_plan_no_claude_call(vault, item, monkeypatch):
    """In dev_mode=true, Claude API is NOT called; plan comes from template."""
    from src.skills.generate_plan import run

    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-fake-key")

    with patch("src.skills.generate_plan._call_claude", return_value="Claude reasoning") as mock_claude:
        result = run(str(vault), dev_mode=True)
        mock_claude.assert_not_called()

    assert result["template_fallback"] >= 1


# ---------------------------------------------------------------------------
# T031.4  no API key: template fallback, no error
# ---------------------------------------------------------------------------


def test_no_api_key_returns_template_plan(vault, item, monkeypatch):
    """Without ANTHROPIC_API_KEY, plan generated from template without error."""
    from src.skills.generate_plan import run

    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    result = run(str(vault), dev_mode=False)

    assert result["errors"] == 0
    assert result["template_fallback"] >= 1
    assert _count_plans(vault) >= 1


# ---------------------------------------------------------------------------
# T031.5  Claude enrichment prepends ## Reasoning section
# ---------------------------------------------------------------------------


def test_claude_enrichment_prepends_reasoning_section(vault, item, monkeypatch):
    """With API key in live mode, plan file contains '## Reasoning' section."""
    from src.skills.generate_plan import run

    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-key")

    with patch("src.skills.generate_plan._call_claude", return_value="Step 1: Review the lead.\nStep 2: Draft reply."):
        result = run(str(vault), dev_mode=False)

    assert result["claude_enriched"] >= 1
    plans_dir = os.path.join(str(vault), "Plans")
    plan_files = [f for f in os.listdir(plans_dir) if f.endswith(".md")]
    assert plan_files, "No plan file was created"
    with open(os.path.join(plans_dir, plan_files[0]), encoding="utf-8") as f:
        content = f.read()
    assert "## Reasoning" in content


# ---------------------------------------------------------------------------
# T031.6  returns claude_enriched count
# ---------------------------------------------------------------------------


def test_returns_claude_enriched_true_when_api_used(vault, item, monkeypatch):
    """claude_enriched count increments when Claude API is used."""
    from src.skills.generate_plan import run

    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-key")

    with patch("src.skills.generate_plan._call_claude", return_value="Reasoned plan here."):
        result = run(str(vault), dev_mode=False)

    assert result["claude_enriched"] >= 1


# ---------------------------------------------------------------------------
# T031.7  template_fallback count correct in dev_mode
# ---------------------------------------------------------------------------


def test_returns_template_fallback_true_in_dev_mode(vault, item, monkeypatch):
    """template_fallback count >= 1 when plan generated from template."""
    from src.skills.generate_plan import run

    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    result = run(str(vault), dev_mode=True)

    assert result["template_fallback"] >= 1


# ---------------------------------------------------------------------------
# T031.8  plan_task.py is not modified by generate_plan
# ---------------------------------------------------------------------------


def test_does_not_modify_plan_task_py(vault):
    """generate_plan.py imports plan_task but must NOT modify PLAN_TEMPLATES or run()."""
    import src.skills.plan_task as pt_before

    original_templates = dict(pt_before.PLAN_TEMPLATES)
    original_run = pt_before.run

    from src.skills.generate_plan import run as gp_run  # noqa: F401

    # Templates unchanged
    assert pt_before.PLAN_TEMPLATES == original_templates
    # run function object unchanged
    assert pt_before.run is original_run
