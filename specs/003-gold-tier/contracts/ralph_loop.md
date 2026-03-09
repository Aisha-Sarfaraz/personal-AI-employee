# Ralph Wiggum Loop — Interface Contract

**Feature**: 003-gold-tier
**Modules**: `src/core/ralph_loop.py`, `hooks/stop_hook.py`
**Date**: 2026-02-25

---

## Overview

The Ralph Wiggum loop drives multi-step plans to completion without requiring human re-prompting
at each step. It uses file-movement completion detection: when the plan file moves to
`vault/Done/`, the loop exits cleanly.

---

## `ralph_loop.py` Contract

```python
class RalphLoop:
    """
    Drives a Claude Code session in a loop until the task_file
    moves to vault/Done/ or max_iterations is exceeded.
    """

    def __init__(self, vault_root: str, task_file: str, prompt: str,
                 max_iterations: int = 10): ...

    def run(self) -> dict:
        """
        Main loop. Returns:
            {"status": "done", "iterations": N}         — task completed
            {"status": "cancelled", "iterations": N}    — file moved to Rejected/
            {"status": "quarantined", "iterations": N}  — max_iterations exceeded
        """

    def _write_state(self, iteration: int, status: str) -> None:
        """
        Writes vault/state/ralph_loop_state.json:
        {"task_file": "<path>", "prompt": "<str>",
         "iteration": N, "status": "running|done|cancelled|quarantined"}
        """

    def _is_done(self) -> bool:
        """Returns True if task_file path is under vault/Done/."""

    def _is_cancelled(self) -> bool:
        """Returns True if task_file path is under vault/Rejected/."""
```

### State File Path

`vault/state/ralph_loop_state.json` — written at the START of each iteration (before
launching Claude subprocess). Stop hook reads this file at session exit.

### Iteration Flow

```
for iteration in range(1, max_iterations + 1):
    1. write_state(iteration, "running")
    2. Launch Claude subprocess with injected prompt
    3. Wait for subprocess to exit (Stop hook fires here)
    4. Re-read state file
    5. if status == "done": break
    6. if status == "cancelled": break
7. if loop exhausted without done/cancelled:
    write_state(max_iterations, "quarantined")
    shutil.move(task_file, vault/Quarantine/)
    create vault/Inbox/RALPH_TIMEOUT_ALERT_<ts>.md
```

---

## `stop_hook.py` Contract

Registered at `.claude/hooks/Stop` by `install_schedule.py`.
Invoked automatically by Claude Code at session exit.

```python
#!/usr/bin/env python3
"""
Stop hook — reads ralph_loop_state.json to determine whether to:
  - Exit cleanly (task done or cancelled)
  - Re-inject prompt and continue (task still running)
"""

def main() -> int:
    """
    Returns exit code:
        0 — allow Claude Code to exit (task done or cancelled or no active loop)
        non-0 — re-inject (Note: actual continuation implemented via state write;
                 Claude Code Stop hook semantics TBD at implementation time)
    """
    state_path = "vault/state/ralph_loop_state.json"
    if not os.path.exists(state_path):
        return 0  # no active Ralph loop

    state = json.load(open(state_path))
    task_file = state["task_file"]
    status = state["status"]

    if status in ("done", "cancelled", "quarantined"):
        return 0  # loop already concluded

    # Check if file moved to Done/
    if "Done/" in task_file or os.path.exists(task_file.replace("Plans/", "Done/")):
        _update_state(state_path, state, "done")
        return 0

    # Check if file moved to Rejected/
    if "Rejected/" in task_file or os.path.exists(task_file.replace("Plans/", "Rejected/")):
        _update_state(state_path, state, "cancelled")
        return 0

    # Task still in progress — RalphLoop controls re-injection
    return 0
```

---

## `install_schedule.py` Extension

Gold extends `install_schedule.py` to register the Stop hook:

```python
def _register_stop_hook(vault_root: str) -> bool:
    """
    Writes hooks/stop_hook.py and registers it in .claude/hooks/Stop.
    Idempotent: skips if already registered (checks hook script content).
    Returns True if registered, False if already present.
    """
```

Registration is automatic on `install_schedule.py` invocation (no separate command needed).
Idempotent: safe to call multiple times.

---

## Orchestrator Integration

Orchestrator `_scan_cycle` detects `requires_ralph: true` in plan frontmatter:

```python
# In orchestrator._scan_cycle()
for plan_file in glob("vault/Plans/PLAN_*.md"):
    meta = load_frontmatter(plan_file)
    if meta.get("requires_ralph") and meta.get("status") == "approved":
        ralph = RalphLoop(vault_root=self.vault_root,
                          task_file=plan_file,
                          prompt=meta.get("ralph_prompt", DEFAULT_RALPH_PROMPT),
                          max_iterations=settings["ralph_loop"]["max_iterations"])
        result = ralph.run()
        audit_logger.log(action_type="ralph_loop_complete", result=result["status"], ...)
```

---

## Plan Frontmatter for Ralph-Enabled Plans

```yaml
---
type: plan
requires_ralph: true
ralph_prompt: "Continue executing the plan steps. Check vault/Plans/PLAN_001.md for remaining tasks."
ralph_task_file: vault/Plans/PLAN_001.md
status: approved
created_at: 2026-02-25T10:00:00Z
---
```

---

## `settings.yaml` Ralph Stanza

```yaml
ralph_loop:
  max_iterations: 10        # default; override per-plan not supported
  state_file: vault/state/ralph_loop_state.json
```
