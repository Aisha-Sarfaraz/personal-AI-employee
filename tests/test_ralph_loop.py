"""Tests for RalphLoop — TDD Phase 11, T048."""

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
    (tmp_path / "state").mkdir()
    (tmp_path / "Plans").mkdir()
    (tmp_path / "Done").mkdir()
    (tmp_path / "Rejected").mkdir()
    (tmp_path / "Quarantine").mkdir()
    (tmp_path / "Inbox").mkdir()
    return tmp_path


@pytest.fixture()
def task_file(vault):
    """Create a task file in Plans/."""
    path = os.path.join(str(vault), "Plans", "PLAN_test001.md")
    with open(path, "w") as f:
        f.write("---\ntype: plan\n---\n\n# Test Plan\n")
    return path


# ---------------------------------------------------------------------------
# Test 1: _write_state creates state file with correct fields
# ---------------------------------------------------------------------------


def test_write_state_creates_file(vault, task_file):
    """_write_state(1, 'running') creates vault/state/ralph_loop_state.json."""
    from src.core.ralph_loop import RalphLoop

    loop = RalphLoop(vault_root=str(vault), task_file=task_file, prompt="Do the task")
    loop._write_state(1, "running")

    state_path = os.path.join(str(vault), "state", "ralph_loop_state.json")
    assert os.path.exists(state_path)


# ---------------------------------------------------------------------------
# Test 2: state file has correct 4 keys
# ---------------------------------------------------------------------------


def test_write_state_has_correct_keys(vault, task_file):
    """State file has task_file, prompt, iteration, status keys."""
    from src.core.ralph_loop import RalphLoop

    loop = RalphLoop(vault_root=str(vault), task_file=task_file, prompt="Do the task")
    loop._write_state(2, "running")

    state_path = os.path.join(str(vault), "state", "ralph_loop_state.json")
    with open(state_path) as f:
        state = json.load(f)

    for key in ("task_file", "prompt", "iteration", "status"):
        assert key in state, f"Missing key: {key}"
    assert state["iteration"] == 2
    assert state["status"] == "running"


# ---------------------------------------------------------------------------
# Test 3: _is_done() returns True when task_file in Done/
# ---------------------------------------------------------------------------


def test_is_done_returns_true(vault, task_file):
    """_is_done() returns True when task_file path is under vault/Done/."""
    from src.core.ralph_loop import RalphLoop

    loop = RalphLoop(vault_root=str(vault), task_file=task_file, prompt="Do the task")

    # Move file to Done/
    done_path = os.path.join(str(vault), "Done", os.path.basename(task_file))
    import shutil
    shutil.copy(task_file, done_path)

    assert loop._is_done() is True


# ---------------------------------------------------------------------------
# Test 4: _is_done() returns False when task_file in Plans/
# ---------------------------------------------------------------------------


def test_is_done_returns_false_in_plans(vault, task_file):
    """_is_done() returns False when task_file is in Plans/."""
    from src.core.ralph_loop import RalphLoop

    loop = RalphLoop(vault_root=str(vault), task_file=task_file, prompt="Do the task")
    # File stays in Plans/
    assert loop._is_done() is False


# ---------------------------------------------------------------------------
# Test 5: _is_cancelled() returns True when task_file in Rejected/
# ---------------------------------------------------------------------------


def test_is_cancelled_returns_true(vault, task_file):
    """_is_cancelled() returns True when task_file is under vault/Rejected/."""
    from src.core.ralph_loop import RalphLoop

    loop = RalphLoop(vault_root=str(vault), task_file=task_file, prompt="Do the task")

    rejected_path = os.path.join(str(vault), "Rejected", os.path.basename(task_file))
    import shutil
    shutil.copy(task_file, rejected_path)

    assert loop._is_cancelled() is True


# ---------------------------------------------------------------------------
# Test 6: run() returns {status:"done"} when file moved to Done after iteration 1
# ---------------------------------------------------------------------------


def test_run_returns_done(vault, task_file):
    """run() with mock subprocess: when task_file moved to Done, returns {status:'done'}."""
    from src.core.ralph_loop import RalphLoop

    def mock_launch(self_obj=None):
        """Move task file to Done/ to simulate completion."""
        done_path = os.path.join(str(vault), "Done", os.path.basename(task_file))
        import shutil
        if os.path.exists(task_file):
            shutil.copy(task_file, done_path)

    loop = RalphLoop(vault_root=str(vault), task_file=task_file, prompt="Do the task", max_iterations=5)

    with patch.object(loop, "_launch_claude", side_effect=lambda: mock_launch()):
        result = loop.run()

    assert result["status"] == "done"
    assert result["iterations"] >= 1


# ---------------------------------------------------------------------------
# Test 7: run() returns {status:"cancelled"} when file in Rejected
# ---------------------------------------------------------------------------


def test_run_returns_cancelled(vault, task_file):
    """run() with mock subprocess: when task_file in Rejected, returns {status:'cancelled'}."""
    from src.core.ralph_loop import RalphLoop

    def mock_launch():
        rejected_path = os.path.join(str(vault), "Rejected", os.path.basename(task_file))
        import shutil
        if os.path.exists(task_file):
            shutil.copy(task_file, rejected_path)

    loop = RalphLoop(vault_root=str(vault), task_file=task_file, prompt="Do the task", max_iterations=5)

    with patch.object(loop, "_launch_claude", side_effect=mock_launch):
        result = loop.run()

    assert result["status"] == "cancelled"


# ---------------------------------------------------------------------------
# Test 8: run() with max_iterations=1 moves file to Quarantine, returns {status:"quarantined"}
# ---------------------------------------------------------------------------


def test_run_quarantines_on_max_iterations(vault, task_file):
    """run() with max_iterations=1 and no completion: moves to Quarantine, returns quarantined."""
    from src.core.ralph_loop import RalphLoop

    loop = RalphLoop(vault_root=str(vault), task_file=task_file, prompt="Do the task", max_iterations=1)

    with patch.object(loop, "_launch_claude"):
        result = loop.run()

    assert result["status"] == "quarantined"
    # File should be in Quarantine
    quarantine_dir = os.path.join(str(vault), "Quarantine")
    quarantine_files = os.listdir(quarantine_dir)
    assert len(quarantine_files) >= 1
