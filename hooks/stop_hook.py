#!/usr/bin/env python3
"""Stop hook — reads ralph_loop_state.json to determine whether the loop is complete.

Invoked automatically by Claude Code at session exit.
Registered at .claude/hooks/Stop by install_schedule.py.
"""

from __future__ import annotations

import json
import os
import sys


def main() -> int:
    """Read ralph_loop_state.json and update status if task has moved to Done/ or Rejected/.

    Returns:
        0 — allow Claude Code to exit (task done or cancelled or no active loop)
    """
    vault_root = os.environ.get("VAULT_ROOT", "vault")
    state_path = os.path.join(vault_root, "state", "ralph_loop_state.json")

    if not os.path.exists(state_path):
        return 0

    try:
        with open(state_path, encoding="utf-8") as f:
            state = json.load(f)
    except (json.JSONDecodeError, OSError):
        return 0

    task_file = state.get("task_file", "")
    status = state.get("status", "")

    # Already concluded
    if status in ("done", "cancelled", "quarantined"):
        return 0

    if not task_file:
        return 0

    filename = os.path.basename(task_file)
    done_dir = os.path.join(vault_root, "Done")
    rejected_dir = os.path.join(vault_root, "Rejected")

    # Check if task moved to Done/
    if filename and os.path.exists(os.path.join(done_dir, filename)):
        state["status"] = "done"
        try:
            with open(state_path, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)
        except OSError:
            pass
        return 0

    # Check if task moved to Rejected/
    if filename and os.path.exists(os.path.join(rejected_dir, filename)):
        state["status"] = "cancelled"
        try:
            with open(state_path, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)
        except OSError:
            pass
        return 0

    # Task still in progress — RalphLoop controls re-injection
    return 0


if __name__ == "__main__":
    sys.exit(main())
