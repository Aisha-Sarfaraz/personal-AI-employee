"""Health monitor — checks watcher threads, stuck plans, vault integrity."""

import os
import threading
import time
from datetime import datetime, timezone
from typing import Any

from src.core.vault import list_folder, read_frontmatter_file
from src.core.audit_logger import log_action


class WatchdogMonitor:
    """Background health monitor for the FTE system."""

    def __init__(
        self,
        vault_root: str,
        watcher_threads: dict[str, threading.Thread],
        max_plan_age_hours: int = 48,
        check_interval: int = 60,
    ) -> None:
        self.vault_root = vault_root
        self.watcher_threads = watcher_threads
        self.max_plan_age_hours = max_plan_age_hours
        self.check_interval = check_interval
        self._running = False

    def check_watcher_health(self) -> dict[str, bool]:
        """Check if watcher threads are alive."""
        health: dict[str, bool] = {}
        for name, thread in self.watcher_threads.items():
            health[name] = thread.is_alive()
        return health

    def check_stuck_plans(self) -> list[str]:
        """Find plans that have been in /Plans longer than max_plan_age_hours."""
        stuck: list[str] = []
        now = datetime.now(timezone.utc)

        plan_files = list_folder(self.vault_root, "Plans")
        for filename in plan_files:
            try:
                metadata, _ = read_frontmatter_file(self.vault_root, f"Plans/{filename}")
                created_str = metadata.get("created", "")
                if created_str:
                    created = datetime.fromisoformat(created_str).replace(tzinfo=timezone.utc)
                    age_hours = (now - created).total_seconds() / 3600
                    if age_hours > self.max_plan_age_hours:
                        stuck.append(filename)
            except Exception:
                pass

        return stuck

    def check_vault_integrity(self) -> list[str]:
        """Verify all required vault folders exist."""
        required_folders = [
            "Inbox", "Needs_Action", "Plans", "Done", "Logs",
            "Pending_Approval", "Approved", "Rejected", "Watch",
        ]
        missing: list[str] = []
        for folder in required_folders:
            folder_path = os.path.join(self.vault_root, folder)
            if not os.path.isdir(folder_path):
                missing.append(folder)
        return missing

    def run(self) -> None:
        """Main monitor loop."""
        self._running = True
        while self._running:
            # Check watcher health
            health = self.check_watcher_health()
            for name, alive in health.items():
                if not alive:
                    log_action(
                        vault_root=self.vault_root,
                        agent="watchdog_monitor",
                        action=f"watcher {name} is not alive",
                        risk_tier="HIGH",
                        status="failure",
                        details=f"Watcher thread {name} has stopped",
                    )

            # Check for stuck plans
            stuck = self.check_stuck_plans()
            for plan_file in stuck:
                log_action(
                    vault_root=self.vault_root,
                    agent="watchdog_monitor",
                    action=f"stuck plan detected: {plan_file}",
                    risk_tier="MEDIUM",
                    status="failure",
                    details=f"Plan older than {self.max_plan_age_hours} hours",
                )

            # Check vault integrity
            missing = self.check_vault_integrity()
            for folder in missing:
                log_action(
                    vault_root=self.vault_root,
                    agent="watchdog_monitor",
                    action=f"missing vault folder: {folder}",
                    risk_tier="CRITICAL",
                    status="failure",
                    details=f"Required folder {folder} does not exist",
                )

            # Sleep in small increments for responsive shutdown
            for _ in range(self.check_interval):
                if not self._running:
                    break
                time.sleep(1)

    def stop(self) -> None:
        """Stop the monitor loop."""
        self._running = False
