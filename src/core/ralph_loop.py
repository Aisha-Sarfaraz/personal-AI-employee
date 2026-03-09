"""RalphLoop — drives multi-step plans to completion via file-movement detection."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from datetime import datetime, timezone
from typing import Any

from src.core.vault import write_frontmatter_file


class RalphLoop:
    """Drives a Claude Code session in a loop until the task_file moves to vault/Done/
    or max_iterations is exceeded.
    """

    def __init__(
        self,
        vault_root: str,
        task_file: str,
        prompt: str,
        max_iterations: int = 10,
    ) -> None:
        self.vault_root = vault_root
        self.task_file = task_file
        self.prompt = prompt
        self.max_iterations = max_iterations
        self._state_file = os.path.join(vault_root, "state", "ralph_loop_state.json")

    def run(self) -> dict[str, Any]:
        """Main loop.

        Returns:
            {"status": "done", "iterations": N}         — task completed
            {"status": "cancelled", "iterations": N}    — file moved to Rejected/
            {"status": "quarantined", "iterations": N}  — max_iterations exceeded
        """
        for iteration in range(1, self.max_iterations + 1):
            self._write_state(iteration, "running")
            self._launch_claude()

            if self._is_done():
                self._write_state(iteration, "done")
                return {"status": "done", "iterations": iteration}

            if self._is_cancelled():
                self._write_state(iteration, "cancelled")
                return {"status": "cancelled", "iterations": iteration}

        # Max iterations exceeded
        self._write_state(self.max_iterations, "quarantined")
        self._quarantine_task()
        return {"status": "quarantined", "iterations": self.max_iterations}

    def _write_state(self, iteration: int, status: str) -> None:
        """Write vault/state/ralph_loop_state.json."""
        os.makedirs(os.path.dirname(self._state_file), exist_ok=True)
        state = {
            "task_file": self.task_file,
            "prompt": self.prompt,
            "iteration": iteration,
            "status": status,
        }
        with open(self._state_file, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)

    def _is_done(self) -> bool:
        """Returns True if task_file basename exists under vault/Done/."""
        done_dir = os.path.join(self.vault_root, "Done")
        filename = os.path.basename(self.task_file)
        return os.path.exists(os.path.join(done_dir, filename))

    def _is_cancelled(self) -> bool:
        """Returns True if task_file basename exists under vault/Rejected/."""
        rejected_dir = os.path.join(self.vault_root, "Rejected")
        filename = os.path.basename(self.task_file)
        return os.path.exists(os.path.join(rejected_dir, filename))

    def _launch_claude(self) -> None:
        """Launch Claude subprocess with injected prompt.

        In tests this method is mocked.
        In production: subprocess.run(["claude", "--print", self.prompt])
        """
        try:
            subprocess.run(
                ["claude", "--print", self.prompt],
                capture_output=True,
                timeout=300,
            )
        except Exception:
            pass  # Gracefully handle missing claude binary or timeout

    def _quarantine_task(self) -> None:
        """Move task_file to vault/Quarantine/ and create alert."""
        quarantine_dir = os.path.join(self.vault_root, "Quarantine")
        os.makedirs(quarantine_dir, exist_ok=True)

        if os.path.exists(self.task_file):
            shutil.move(self.task_file, quarantine_dir)

        # Create timeout alert
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        filename = f"RALPH_TIMEOUT_ALERT_{ts}.md"
        metadata = {
            "type": "ralph_timeout_alert",
            "task_file": self.task_file,
            "max_iterations": self.max_iterations,
            "risk_level": "HIGH",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        body = (
            f"# Ralph Loop Timeout\n\n"
            f"Task `{self.task_file}` exceeded max iterations ({self.max_iterations}).\n\n"
            f"The task file has been moved to `vault/Quarantine/`.\n\n"
            f"**Action Required**: Review and restart the task manually.\n"
        )
        try:
            write_frontmatter_file(self.vault_root, f"Inbox/{filename}", metadata, body)
        except Exception:
            pass
