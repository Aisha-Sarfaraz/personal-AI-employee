"""SC-029: Ralph Loop Done — integration test, Phase 11, T054."""

from __future__ import annotations

import json
import os
import shutil
from unittest.mock import patch

import pytest


@pytest.fixture()
def vault(tmp_path):
    (tmp_path / "state").mkdir()
    (tmp_path / "Plans").mkdir()
    (tmp_path / "Done").mkdir()
    (tmp_path / "Rejected").mkdir()
    (tmp_path / "Quarantine").mkdir()
    (tmp_path / "Inbox").mkdir()
    return tmp_path


@pytest.fixture()
def task_file(vault):
    path = os.path.join(str(vault), "Plans", "PLAN_sc029.md")
    with open(path, "w") as f:
        f.write("---\ntype: plan\nrequires_ralph: true\n---\n\n# SC-029 Test Plan\n")
    return path


# ---------------------------------------------------------------------------
# SC-029.1 Loop drives until file moved to Done/
# ---------------------------------------------------------------------------


def test_sc029_task_completes_in_done(vault, task_file):
    """Given PLAN file, RalphLoop drives until file moved to Done/; exits {status:'done'}."""
    from src.core.ralph_loop import RalphLoop

    def mock_launch():
        """Simulate Claude moving file to Done/."""
        done_path = os.path.join(str(vault), "Done", os.path.basename(task_file))
        if os.path.exists(task_file) and not os.path.exists(done_path):
            shutil.copy(task_file, done_path)

    loop = RalphLoop(
        vault_root=str(vault),
        task_file=task_file,
        prompt="Continue executing the plan steps.",
        max_iterations=5,
    )

    with patch.object(loop, "_launch_claude", side_effect=mock_launch):
        result = loop.run()

    assert result["status"] == "done"
    assert result["iterations"] >= 1

    # Verify state file shows done
    state_path = os.path.join(str(vault), "state", "ralph_loop_state.json")
    with open(state_path) as f:
        state = json.load(f)
    assert state["status"] == "done"


# ---------------------------------------------------------------------------
# SC-029.2 max_iterations exceeded → task moved to Quarantine
# ---------------------------------------------------------------------------


def test_sc029_max_iterations_quarantines(vault, task_file):
    """Given max_iterations=2 exceeded, task moved to Quarantine."""
    from src.core.ralph_loop import RalphLoop

    loop = RalphLoop(
        vault_root=str(vault),
        task_file=task_file,
        prompt="Continue executing the plan steps.",
        max_iterations=2,
    )

    with patch.object(loop, "_launch_claude"):
        result = loop.run()

    assert result["status"] == "quarantined"
    assert result["iterations"] == 2

    # File moved to Quarantine
    quarantine_dir = os.path.join(str(vault), "Quarantine")
    quarantine_files = os.listdir(quarantine_dir)
    assert len(quarantine_files) >= 1


# ---------------------------------------------------------------------------
# SC-029.3 Manual move to Done/ during loop detected cleanly
# ---------------------------------------------------------------------------


def test_sc029_manual_move_to_done_detected(vault, task_file):
    """Given manual move to Done/ during loop, _is_done() detects and exits cleanly."""
    from src.core.ralph_loop import RalphLoop

    loop = RalphLoop(
        vault_root=str(vault),
        task_file=task_file,
        prompt="Test prompt",
        max_iterations=10,
    )

    # Manually move to Done before running
    done_path = os.path.join(str(vault), "Done", os.path.basename(task_file))
    shutil.copy(task_file, done_path)

    # _is_done should detect it
    assert loop._is_done() is True

    # Run with mock that doesn't move file (already moved)
    with patch.object(loop, "_launch_claude"):
        result = loop.run()

    assert result["status"] == "done"
