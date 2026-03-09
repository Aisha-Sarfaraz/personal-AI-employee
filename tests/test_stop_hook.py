"""Tests for stop_hook — TDD Phase 11, T050."""

from __future__ import annotations

import json
import os
from unittest.mock import patch

import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def vault(tmp_path):
    (tmp_path / "state").mkdir()
    (tmp_path / "Done").mkdir()
    (tmp_path / "Rejected").mkdir()
    return tmp_path


def _write_state(vault, task_file, status, iteration=1):
    state = {
        "task_file": task_file,
        "prompt": "Do the task",
        "iteration": iteration,
        "status": status,
    }
    state_path = os.path.join(str(vault), "state", "ralph_loop_state.json")
    with open(state_path, "w") as f:
        json.dump(state, f)
    return state_path


# ---------------------------------------------------------------------------
# Test 1: No state file → exits 0
# ---------------------------------------------------------------------------


def test_no_state_file_exits_0(vault):
    """No state file → main() returns 0."""
    from hooks.stop_hook import main

    with patch.dict(os.environ, {"VAULT_ROOT": str(vault)}):
        result = main()

    assert result == 0


# ---------------------------------------------------------------------------
# Test 2: State status "done" → exits 0
# ---------------------------------------------------------------------------


def test_status_done_exits_0(vault):
    """State status: 'done' → returns 0."""
    from hooks.stop_hook import main

    _write_state(vault, "/fake/Plans/task.md", "done")

    with patch.dict(os.environ, {"VAULT_ROOT": str(vault)}):
        result = main()

    assert result == 0


# ---------------------------------------------------------------------------
# Test 3: State status "cancelled" → exits 0
# ---------------------------------------------------------------------------


def test_status_cancelled_exits_0(vault):
    """State status: 'cancelled' → returns 0."""
    from hooks.stop_hook import main

    _write_state(vault, "/fake/Plans/task.md", "cancelled")

    with patch.dict(os.environ, {"VAULT_ROOT": str(vault)}):
        result = main()

    assert result == 0


# ---------------------------------------------------------------------------
# Test 4: task_file found in Done/ → updates state to "done", returns 0
# ---------------------------------------------------------------------------


def test_task_in_done_updates_state(vault):
    """task_file found in Done/ → updates state to 'done', returns 0."""
    from hooks.stop_hook import main

    # Create task file in Done/
    task_filename = "PLAN_001.md"
    done_path = os.path.join(str(vault), "Done", task_filename)
    with open(done_path, "w") as f:
        f.write("# Plan\n")

    # State points to Plans/ location
    task_file_in_plans = os.path.join(str(vault), "Plans", task_filename)
    state_path = _write_state(vault, task_file_in_plans, "running")

    with patch.dict(os.environ, {"VAULT_ROOT": str(vault)}):
        result = main()

    assert result == 0

    # State should be updated to "done"
    with open(state_path) as f:
        state = json.load(f)
    assert state["status"] == "done"


# ---------------------------------------------------------------------------
# Test 5: task_file found in Rejected/ → updates state to "cancelled", returns 0
# ---------------------------------------------------------------------------


def test_task_in_rejected_updates_state(vault):
    """task_file found in Rejected/ → updates state to 'cancelled', returns 0."""
    from hooks.stop_hook import main

    task_filename = "PLAN_002.md"
    rejected_path = os.path.join(str(vault), "Rejected", task_filename)
    with open(rejected_path, "w") as f:
        f.write("# Plan\n")

    task_file_in_plans = os.path.join(str(vault), "Plans", task_filename)
    state_path = _write_state(vault, task_file_in_plans, "running")

    with patch.dict(os.environ, {"VAULT_ROOT": str(vault)}):
        result = main()

    assert result == 0

    with open(state_path) as f:
        state = json.load(f)
    assert state["status"] == "cancelled"


# ---------------------------------------------------------------------------
# Test 6: Corrupt JSON in state file → exits 0 gracefully
# ---------------------------------------------------------------------------


def test_corrupt_json_exits_0(vault):
    """Corrupt JSON in state file → returns 0 (graceful)."""
    from hooks.stop_hook import main

    state_path = os.path.join(str(vault), "state", "ralph_loop_state.json")
    with open(state_path, "w") as f:
        f.write("{corrupt json!!!}")

    with patch.dict(os.environ, {"VAULT_ROOT": str(vault)}):
        result = main()

    assert result == 0
