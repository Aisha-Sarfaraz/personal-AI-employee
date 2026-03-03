"""Watchdog — monitors all daemon watcher threads; auto-restarts dead threads."""

from __future__ import annotations

import threading
from datetime import datetime, timezone
from typing import Any

from src.core.audit_logger import log
from src.core.vault import write_frontmatter_file
from src.watchers.base_watcher import BaseWatcher


class Watchdog:
    """Monitors all daemon watcher threads. Runs every 60s.

    Attempts restart on thread death.
    Creates vault alert after MAX_RESTART_ATTEMPTS consecutive failed restarts.
    """

    CHECK_INTERVAL_S: int = 60
    MAX_RESTART_ATTEMPTS: int = 3

    def __init__(
        self,
        vault_root: str = "",
        check_interval_s: int = 60,
        max_restart_attempts: int = 3,
    ) -> None:
        self.vault_root = vault_root
        self.check_interval_s = check_interval_s
        self.max_restart_attempts = max_restart_attempts
        self._failure_counts: dict[str, int] = {}
        self._exhausted: set[str] = set()

    def check_all_threads(
        self,
        watcher_registry: dict[str, Any],
        thread_registry: dict[str, threading.Thread],
    ) -> None:
        """For each thread: if not alive → attempt restart.

        Track failure_count per watcher name.
        On failure_count >= max_restart_attempts: create vault alert, stop retrying.
        """
        for name, thread in list(thread_registry.items()):
            if name in self._exhausted:
                continue

            if not thread.is_alive():
                watcher = watcher_registry.get(name)
                new_thread = self._restart_watcher(name, watcher, thread_registry)

                if new_thread is not None:
                    thread_registry[name] = new_thread
                    self._failure_counts[name] = 0
                    # Audit log success
                    try:
                        log(
                            vault_root=self.vault_root,
                            action_type="watchdog_restart",
                            actor="watchdog",
                            target=name,
                            parameters={"watcher_name": name},
                            approval_status="auto",
                            approved_by="system",
                            result="success",
                        )
                    except Exception:
                        pass
                else:
                    self._failure_counts[name] = self._failure_counts.get(name, 0) + 1
                    # Audit log failure
                    try:
                        log(
                            vault_root=self.vault_root,
                            action_type="watchdog_restart",
                            actor="watchdog",
                            target=name,
                            parameters={"watcher_name": name, "failure_count": self._failure_counts[name]},
                            approval_status="auto",
                            approved_by="system",
                            result="failure",
                        )
                    except Exception:
                        pass

                    if self._failure_counts[name] >= self.max_restart_attempts:
                        self._create_alert(name)
                        self._exhausted.add(name)

    def _restart_watcher(
        self,
        name: str,
        watcher: Any,
        thread_registry: dict[str, threading.Thread],
    ) -> threading.Thread | None:
        """Attempt to restart a dead watcher thread.

        Returns new thread on success, None on failure.
        """
        if watcher is None:
            return None

        try:
            vault_root = getattr(watcher, "vault_root", self.vault_root)
            new_thread = threading.Thread(
                target=watcher.run,
                args=(vault_root,),
                daemon=True,
                name=f"{name}_restarted",
            )
            new_thread.start()
            return new_thread
        except Exception:
            return None

    def _create_alert(self, watcher_name: str) -> None:
        """Create vault/Inbox/WATCHDOG_ALERT_{watcher}_{ts}.md."""
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        filename = f"WATCHDOG_ALERT_{watcher_name}_{ts}.md"

        metadata = {
            "type": "watchdog_alert",
            "watcher_name": watcher_name,
            "failure_count": self._failure_counts.get(watcher_name, self.max_restart_attempts),
            "risk_level": "CRITICAL",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        body = (
            f"# Watchdog Alert: {watcher_name} Failed\n\n"
            f"The watcher `{watcher_name}` has failed {self.max_restart_attempts} consecutive restart attempts.\n\n"
            f"**Action Required**: Investigate and manually restart the watcher.\n"
        )

        try:
            write_frontmatter_file(self.vault_root, f"Inbox/{filename}", metadata, body)
        except Exception:
            pass

        # Audit log
        try:
            log(
                vault_root=self.vault_root,
                action_type="watchdog_alert",
                actor="watchdog",
                target=watcher_name,
                parameters={"watcher_name": watcher_name, "max_attempts": self.max_restart_attempts},
                approval_status="auto",
                approved_by="system",
                result="success",
            )
        except Exception:
            pass
