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
from src.skills import detect_lead, generate_plan, generate_linkedin_post, weekly_briefing
from src.watchers.filesystem_watcher import FilesystemWatcher
from src.watchdog_monitor import WatchdogMonitor

try:
    from src.watchers.gmail_watcher import GmailWatcher
    _GMAIL_AVAILABLE = True
except ImportError:  # pragma: no cover
    _GMAIL_AVAILABLE = False
    GmailWatcher = None  # type: ignore[assignment,misc]

try:
    from src.watchers.whatsapp_watcher import WhatsAppWatcher
    _WHATSAPP_AVAILABLE = True
except ImportError:  # pragma: no cover
    _WHATSAPP_AVAILABLE = False
    WhatsAppWatcher = None  # type: ignore[assignment,misc]

try:
    from src.watchers.linkedin_watcher import LinkedInWatcher
    _LINKEDIN_AVAILABLE = True
except ImportError:  # pragma: no cover
    _LINKEDIN_AVAILABLE = False
    LinkedInWatcher = None  # type: ignore[assignment,misc]

# Gold Tier imports (graceful fallback)
try:
    from src.watchers.finance_watcher import FinanceWatcher
    _FINANCE_AVAILABLE = True
except ImportError:  # pragma: no cover
    _FINANCE_AVAILABLE = False
    FinanceWatcher = None  # type: ignore[assignment,misc]

try:
    from src.watchers.facebook_watcher import FacebookWatcher
    _FACEBOOK_AVAILABLE = True
except ImportError:  # pragma: no cover
    _FACEBOOK_AVAILABLE = False
    FacebookWatcher = None  # type: ignore[assignment,misc]

try:
    from src.watchers.twitter_watcher import TwitterWatcher
    _TWITTER_AVAILABLE = True
except ImportError:  # pragma: no cover
    _TWITTER_AVAILABLE = False
    TwitterWatcher = None  # type: ignore[assignment,misc]

try:
    from src.watchers.watchdog import Watchdog as WatchdogGold
    _WATCHDOG_GOLD_AVAILABLE = True
except ImportError:  # pragma: no cover
    _WATCHDOG_GOLD_AVAILABLE = False
    WatchdogGold = None  # type: ignore[assignment,misc]

try:
    from src.core.audit_logger import archive_old_logs
    from src.core.ralph_loop import RalphLoop
    _RALPH_AVAILABLE = True
except ImportError:  # pragma: no cover
    _RALPH_AVAILABLE = False
    RalphLoop = None  # type: ignore[assignment,misc]
    archive_old_logs = None  # type: ignore[assignment,misc]


class Orchestrator:
    """Main orchestrator process coordinating watchers and skills."""

    def __init__(self, config_path: str = "config/settings.yaml") -> None:
        self._running = False
        self._config = self._load_config(config_path)
        self._vault_root = os.path.abspath(self._config.get("vault", {}).get("root", "vault"))
        self._scan_interval = self._config.get("orchestrator", {}).get("scan_interval", 30)
        self._watchers: dict[str, Any] = {}
        self._watcher_threads: dict[str, threading.Thread] = {}
        self._watcher_health: dict[str, Any] = {}
        self._health_lock = threading.Lock()
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
        # Silver Tier: additional folders
        for silver_folder in ("Briefings", "Quarantine", "Templates",
                               os.path.join("Watch", "gmail_mock"),
                               os.path.join("Watch", "whatsapp_mock"),
                               os.path.join("Watch", "linkedin_mock")):
            os.makedirs(os.path.join(self._vault_root, silver_folder), exist_ok=True)
        # Gold Tier: additional folders
        for gold_folder in ("Accounting", "Needs_Action", "Pending_Approval",
                             os.path.join("Watch", "finance_mock"),
                             os.path.join("Watch", "finance_drop"),
                             os.path.join("Watch", "facebook_mock"),
                             os.path.join("Watch", "twitter_mock"),
                             os.path.join("Logs", "Archive")):
            os.makedirs(os.path.join(self._vault_root, gold_folder), exist_ok=True)

    def _watcher_loop(self, watcher: Any, name: str) -> None:
        """Run a watcher in a loop, updating health on each poll."""
        while True:
            try:
                items = watcher.check_for_updates() if hasattr(watcher, "check_for_updates") else []
                with self._health_lock:
                    self._watcher_health[name] = {
                        "status": "running",
                        "last_poll": time.strftime("%Y-%m-%dT%H:%M:%S"),
                        "items_this_cycle": len(items) if items else 0,
                    }
            except Exception as exc:
                with self._health_lock:
                    self._watcher_health[name] = {
                        "status": "ERROR",
                        "last_poll": time.strftime("%Y-%m-%dT%H:%M:%S"),
                        "items_this_cycle": 0,
                        "error": str(exc),
                    }
            poll_interval = getattr(watcher, "poll_interval", 120)
            time.sleep(poll_interval)

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

        # Silver Tier: Gmail watcher
        if _GMAIL_AVAILABLE and watcher_config.get("gmail", {}).get("enabled", False):
            gm_cfg = watcher_config.get("gmail", {})
            gmail_watcher = GmailWatcher(
                vault_root=self._vault_root,
                poll_interval=gm_cfg.get("poll_interval", 120),
                gmail_mock_dir=gm_cfg.get("mock_folder", ""),
            )
            self._watchers["gmail_watcher"] = gmail_watcher

        # Silver Tier: WhatsApp watcher
        if _WHATSAPP_AVAILABLE and watcher_config.get("whatsapp", {}).get("enabled", False):
            wa_cfg = watcher_config.get("whatsapp", {})
            whatsapp_watcher = WhatsAppWatcher(
                vault_root=self._vault_root,
                poll_interval=wa_cfg.get("poll_interval", 120),
                whatsapp_mock_dir=wa_cfg.get("mock_folder", ""),
            )
            self._watchers["whatsapp_watcher"] = whatsapp_watcher

        # Silver Tier: LinkedIn watcher
        if _LINKEDIN_AVAILABLE and watcher_config.get("linkedin", {}).get("enabled", False):
            li_cfg = watcher_config.get("linkedin", {})
            linkedin_watcher = LinkedInWatcher(
                vault_root=self._vault_root,
                poll_interval=li_cfg.get("poll_interval", 3600),
                linkedin_mock_dir=li_cfg.get("mock_folder", ""),
                username=li_cfg.get("username", ""),
            )
            self._watchers["linkedin_watcher"] = linkedin_watcher

        # Gold Tier: Finance watcher
        if _FINANCE_AVAILABLE and watcher_config.get("finance", {}).get("enabled", False):
            fi_cfg = watcher_config.get("finance", {})
            finance_watcher = FinanceWatcher(
                vault_root=self._vault_root,
                poll_interval=fi_cfg.get("poll_interval", 300),
            )
            self._watchers["finance_watcher"] = finance_watcher

        # Gold Tier: Facebook watcher
        if _FACEBOOK_AVAILABLE and watcher_config.get("facebook", {}).get("enabled", False):
            fb_cfg = watcher_config.get("facebook", {})
            facebook_watcher = FacebookWatcher(
                vault_root=self._vault_root,
                poll_interval=fb_cfg.get("poll_interval", 3600),
            )
            self._watchers["facebook_watcher"] = facebook_watcher

        # Gold Tier: Twitter watcher
        if _TWITTER_AVAILABLE and watcher_config.get("twitter", {}).get("enabled", False):
            tw_cfg = watcher_config.get("twitter", {})
            twitter_watcher = TwitterWatcher(
                vault_root=self._vault_root,
                poll_interval=tw_cfg.get("poll_interval", 86400),
            )
            self._watchers["twitter_watcher"] = twitter_watcher

    def _start_watchers(self) -> None:
        """Start all watchers as daemon threads."""
        for name, watcher in self._watchers.items():
            if hasattr(watcher, "start_observer"):
                watcher.start_observer()
            # Silver watchers (GmailWatcher, WhatsAppWatcher, LinkedInWatcher) use _watcher_loop;
            # FilesystemWatcher uses its own .run() with vault_root arg.
            if hasattr(watcher, "check_for_updates") and not hasattr(watcher, "run"):
                target = self._watcher_loop
                args = (watcher, name)
            else:
                target = watcher.run
                args = (self._vault_root,)
            thread = threading.Thread(
                target=target,
                args=args,
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
        """Run one scan cycle: triage → detect_lead → generate_plan → execute → Silver skills → dashboard."""
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

        # Silver Tier: detect leads after triage
        try:
            lead_result = detect_lead.run(self._vault_root)
            if lead_result.get("leads_detected", 0) > 0:
                print(f"  [detect_lead] leads={lead_result['leads_detected']}")
        except Exception as e:
            print(f"  [detect_lead] ERROR: {e}")

        # Silver Tier: generate_plan replaces plan_task in scan cycle
        try:
            plan_result = generate_plan.run(self._vault_root)
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

        # Silver Tier: LinkedIn post generator (self-guarded by cadence + enabled flag)
        try:
            generate_linkedin_post.run(self._vault_root)
        except Exception as e:
            print(f"  [linkedin_post] ERROR: {e}")

        # Silver Tier: weekly briefing (self-guarded: runs only on Monday)
        try:
            weekly_briefing.run(self._vault_root)
        except Exception as e:
            print(f"  [briefing]  ERROR: {e}")

        try:
            update_dashboard.run(self._vault_root)
        except Exception as e:
            print(f"  [dashboard] ERROR: {e}")

        # Gold Tier: check for requires_ralph plans
        try:
            self._scan_cycle_ralph_check()
        except Exception as e:
            print(f"  [ralph]     ERROR: {e}")

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

        # Gold Tier: archive old audit logs on startup
        if archive_old_logs is not None:
            try:
                retention = self._config.get("audit", {}).get("retention_days", 90)
                archive_old_logs(self._vault_root, retention_days=retention)
            except Exception:
                pass

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

    def _load_mcp_servers(self, mcp_yaml_path: str = "config/mcp_servers.yaml") -> list[Any]:
        """Load MCP server definitions from config/mcp_servers.yaml.

        Returns list of server config dicts, or [] if file not found.
        """
        if not os.path.isfile(mcp_yaml_path):
            return []
        try:
            with open(mcp_yaml_path, encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            return data.get("mcp_servers", [])
        except Exception:
            return []

    def _start_mcp_servers(self) -> None:
        """Start MCP server subprocesses defined in config/mcp_servers.yaml.

        In DEV_MODE (or when server is not available) this is a no-op.
        Each server runs as a daemon subprocess; errors are logged but non-fatal.
        """
        dev_mode = os.environ.get("DEV_MODE", "").lower() in ("true", "1", "yes")
        if dev_mode:
            return
        servers = self._load_mcp_servers()
        for srv in servers:
            try:
                import subprocess
                cmd = [srv.get("command", "python")] + list(srv.get("args", []))
                proc = subprocess.Popen(
                    cmd,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                print(f"[orchestrator] MCP server '{srv.get('name')}' started (pid={proc.pid})")
            except Exception as exc:
                print(f"[orchestrator] MCP server '{srv.get('name')}' failed to start: {exc}")

    def _scan_cycle_ralph_check(self) -> None:
        """Detect plans with requires_ralph: true and delegate to RalphLoop."""
        if not _RALPH_AVAILABLE or RalphLoop is None:
            return
        plans_dir = os.path.join(self._vault_root, "Plans")
        if not os.path.isdir(plans_dir):
            return
        for fname in os.listdir(plans_dir):
            if not fname.endswith(".md"):
                continue
            plan_path = os.path.join(plans_dir, fname)
            try:
                with open(plan_path, encoding="utf-8") as f:
                    content = f.read()
            except OSError:
                continue
            # Parse frontmatter
            if not content.startswith("---"):
                continue
            parts = content.split("---", 2)
            if len(parts) < 2:
                continue
            try:
                import yaml as _yaml
                meta = _yaml.safe_load(parts[1]) or {}
            except Exception:
                continue
            if not meta.get("requires_ralph"):
                continue
            # Found a plan requiring Ralph — delegate to RalphLoop
            max_iter = self._config.get("ralph_loop", {}).get("max_iterations", 10)
            loop = RalphLoop(
                vault_root=self._vault_root,
                task_file=plan_path,
                prompt=meta.get("prompt", ""),
                max_iterations=max_iter,
            )
            try:
                result = loop.run()
                if result.get("status") == "done":
                    print(f"  [ralph]     {fname} → done in {result.get('iterations', '?')} iterations")
            except Exception as exc:
                print(f"  [ralph]     ERROR running RalphLoop for {fname}: {exc}")

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
