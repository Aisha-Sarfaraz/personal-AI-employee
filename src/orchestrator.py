"""Master orchestrator — coordinates watchers and reasoning pipeline."""

import os
import signal
import sys
import threading
import time
from typing import Any

# Ensure project root is on sys.path so `src` is importable
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import yaml

# Force unbuffered stdout so prints appear immediately on Windows
sys.stdout.reconfigure(line_buffering=True)

from src.core.audit_logger import log_action
from src.skills import triage_inbox, plan_task, execute_plan, update_dashboard
from src.watchers.filesystem_watcher import FilesystemWatcher
from src.watchdog_monitor import WatchdogMonitor


class Orchestrator:
    """Main orchestrator process coordinating watchers and skills."""

    def __init__(self, config_path: str = "config/settings.yaml") -> None:
        self._running = False
        self._config = self._load_config(config_path)
        self._vault_root = os.path.abspath(self._config.get("vault", {}).get("root", "vault"))
        self._scan_interval = self._config.get("orchestrator", {}).get("scan_interval", 30)
        self._watchers: dict[str, Any] = {}
        self._watcher_threads: dict[str, threading.Thread] = {}
        self._monitor: WatchdogMonitor | None = None
        self._monitor_thread: threading.Thread | None = None

    def _load_config(self, config_path: str) -> dict[str, Any]:
        """Load configuration from settings.yaml."""
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def _ensure_vault_structure(self) -> None:
        """Ensure all vault folders exist."""
        folders = self._config.get("vault", {}).get("folders", {})
        for folder_name in folders.values():
            folder_path = os.path.join(self._vault_root, folder_name)
            os.makedirs(folder_path, exist_ok=True)
        # Also ensure state dir
        state_dir = os.path.join(self._vault_root, self._config.get("vault", {}).get("state_dir", "state"))
        os.makedirs(state_dir, exist_ok=True)

    def _init_watchers(self) -> None:
        """Initialize watcher registry."""
        watcher_config = self._config.get("watchers", {})

        if watcher_config.get("filesystem", {}).get("enabled", True):
            fs_config = watcher_config.get("filesystem", {})
            watcher = FilesystemWatcher(
                vault_root=self._vault_root,
                poll_interval=fs_config.get("poll_interval", 5),
                stability_wait=fs_config.get("stability_wait", 2.0),
            )
            self._watchers["filesystem_watcher"] = watcher

    def _start_watchers(self) -> None:
        """Start all watchers as daemon threads."""
        for name, watcher in self._watchers.items():
            if hasattr(watcher, "start_observer"):
                watcher.start_observer()
            thread = threading.Thread(
                target=watcher.run,
                args=(self._vault_root,),
                name=f"watcher-{name}",
                daemon=True,
            )
            thread.start()
            self._watcher_threads[name] = thread

    def _start_monitor(self) -> None:
        """Start the watchdog monitor as a daemon thread."""
        max_plan_age = self._config.get("orchestrator", {}).get("max_plan_age_hours", 48)
        self._monitor = WatchdogMonitor(
            vault_root=self._vault_root,
            watcher_threads=self._watcher_threads,
            max_plan_age_hours=max_plan_age,
            check_interval=60,
        )
        self._monitor_thread = threading.Thread(
            target=self._monitor.run,
            name="watchdog-monitor",
            daemon=True,
        )
        self._monitor_thread.start()

    def _setup_signal_handlers(self) -> None:
        """Set up graceful shutdown handlers."""
        def shutdown_handler(signum: int, frame: Any) -> None:
            self._running = False

        signal.signal(signal.SIGINT, shutdown_handler)
        if hasattr(signal, "SIGTERM"):
            signal.signal(signal.SIGTERM, shutdown_handler)

    def _scan_cycle(self) -> None:
        """Run one scan cycle: triage → plan → execute → dashboard."""
        # Debug: show inbox count before triage
        inbox_path = os.path.join(self._vault_root, "Inbox")
        inbox_files = [f for f in os.listdir(inbox_path) if f.endswith(".md")] if os.path.isdir(inbox_path) else []
        if inbox_files:
            print(f"  [scan]      {len(inbox_files)} file(s) in Inbox")

        try:
            triage_result = triage_inbox.run(self._vault_root)
            if triage_result.get("processed", 0) > 0:
                print(f"  [triage]    processed={triage_result['processed']}")
        except Exception as e:
            print(f"  [triage]    ERROR: {e}")

        try:
            plan_result = plan_task.run(self._vault_root)
            if plan_result.get("processed", 0) > 0:
                print(f"  [plan]      processed={plan_result['processed']}")
        except Exception as e:
            print(f"  [plan]      ERROR: {e}")

        try:
            execute_result = execute_plan.run(self._vault_root)
            if execute_result.get("processed", 0) > 0:
                print(f"  [execute]   processed={execute_result['processed']}")
        except Exception as e:
            print(f"  [execute]   ERROR: {e}")

        try:
            dashboard_result = update_dashboard.run(self._vault_root)
        except Exception as e:
            print(f"  [dashboard] ERROR: {e}")

    def start(self) -> None:
        """Start the orchestrator."""
        self._running = True
        self._ensure_vault_structure()
        self._setup_signal_handlers()
        self._init_watchers()

        print(f"[orchestrator] Starting with {len(self._watchers)} watcher(s)")
        print(f"[orchestrator] Vault: {self._vault_root}")
        print(f"[orchestrator] Scan interval: {self._scan_interval}s")
        print(f"[orchestrator] DEV_MODE: {self._config.get('dev_mode', True)}")
        print(f"[orchestrator] Press Ctrl+C to stop")
        print()

        log_action(
            vault_root=self._vault_root,
            agent="orchestrator",
            action="startup",
            risk_tier="LOW",
            status="success",
            details=f"Started with {len(self._watchers)} watcher(s)",
        )

        self._start_watchers()
        self._start_monitor()
        print("[orchestrator] Watchers and monitor started")

        # Initial scan to resume any in-flight items
        print("[orchestrator] Running initial scan...")
        self._scan_cycle()
        print("[orchestrator] Ready. Watching for files...")
        print()

        # Main loop
        while self._running:
            self._scan_cycle()
            # Sleep in small increments for responsive shutdown
            for _ in range(self._scan_interval):
                if not self._running:
                    break
                time.sleep(1)

        self._shutdown()

    def _shutdown(self) -> None:
        """Graceful shutdown."""
        print()
        print("[orchestrator] Shutting down...")
        # Stop watchers
        for name, watcher in self._watchers.items():
            if hasattr(watcher, "stop"):
                watcher.stop()
            if hasattr(watcher, "stop_observer"):
                watcher.stop_observer()

        # Stop monitor
        if self._monitor:
            self._monitor.stop()

        log_action(
            vault_root=self._vault_root,
            agent="orchestrator",
            action="shutdown",
            risk_tier="LOW",
            status="success",
            details="Graceful shutdown completed",
        )


def main() -> None:
    """Entry point for the orchestrator."""
    config_path = "config/settings.yaml"
    if len(sys.argv) > 1:
        config_path = sys.argv[1]

    orchestrator = Orchestrator(config_path)
    orchestrator.start()


if __name__ == "__main__":
    main()
