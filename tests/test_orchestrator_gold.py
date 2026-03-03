"""Gold Tier orchestrator integration tests — T055 (Phase 12)."""

from __future__ import annotations

import os
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml


VAULT_DIRS = (
    "Inbox", "Watch", "Plans", "Done", "Rejected", "Quarantine",
    "Logs", "state", "Pending_Approval", "Needs_Action", "Accounting",
    os.path.join("Watch", "finance_mock"),
    os.path.join("Watch", "facebook_mock"),
    os.path.join("Watch", "twitter_mock"),
)


def make_vault(tmp_path: Path) -> str:
    vault = tmp_path / "vault"
    for folder in VAULT_DIRS:
        (vault / folder).mkdir(parents=True, exist_ok=True)
    return str(vault)


def make_config(tmp_path: Path, vault_root: str) -> str:
    cfg = {
        "vault": {
            "root": vault_root,
            "folders": {"inbox": "Inbox", "watch": "Watch", "plans": "Plans",
                        "done": "Done", "rejected": "Rejected", "quarantine": "Quarantine",
                        "logs": "Logs", "pending_approval": "Pending_Approval"},
            "state_dir": "state",
        },
        "orchestrator": {"scan_interval": 1, "max_plan_age_hours": 48},
        "dev_mode": True,
        "watchers": {
            "filesystem": {"enabled": False},
            "gmail": {"enabled": False},
            "whatsapp": {"enabled": False},
            "linkedin": {"enabled": False},
            "finance": {"enabled": True, "poll_interval": 300},
            "facebook": {"enabled": False},
            "twitter": {"enabled": False},
        },
        "facebook": {"enabled": False, "frequency_days": 3},
        "twitter": {"enabled": False, "tweets_per_day": 1},
        "ralph_loop": {"max_iterations": 10},
        "audit": {"retention_days": 90},
    }
    config_path = tmp_path / "settings.yaml"
    config_path.write_text(yaml.dump(cfg), encoding="utf-8")
    return str(config_path)


def make_mcp_servers_yaml(tmp_path: Path) -> str:
    """Create minimal config/mcp_servers.yaml."""
    cfg = {"mcp_servers": [{"name": "odoo-mcp", "command": "python",
                             "args": ["-m", "src.mcp_servers.odoo_mcp.server"],
                             "transport": "stdio", "health_check_interval_s": 60}]}
    path = tmp_path / "mcp_servers.yaml"
    path.write_text(yaml.dump(cfg), encoding="utf-8")
    return str(path)


# ---------------------------------------------------------------------------
# T055.1  Orchestrator startup reads config/mcp_servers.yaml
# ---------------------------------------------------------------------------

def test_orchestrator_reads_mcp_servers_yaml(tmp_path):
    vault = make_vault(tmp_path)
    config_path = make_config(tmp_path, vault)
    mcp_yaml = make_mcp_servers_yaml(tmp_path)

    from src.orchestrator import Orchestrator
    orch = Orchestrator(config_path=config_path)

    # _start_mcp_servers reads and stores the server configs
    # Pass the mcp_yaml path so it knows where to look
    mcp_servers = orch._load_mcp_servers(mcp_yaml)
    assert isinstance(mcp_servers, list)
    assert len(mcp_servers) >= 1
    assert mcp_servers[0]["name"] == "odoo-mcp"


# ---------------------------------------------------------------------------
# T055.2  FinanceWatcher daemon thread created on startup (finance.enabled=True)
# ---------------------------------------------------------------------------

def test_finance_watcher_thread_created(tmp_path):
    vault = make_vault(tmp_path)
    config_path = make_config(tmp_path, vault)

    from src.orchestrator import Orchestrator
    orch = Orchestrator(config_path=config_path)
    orch._vault_root = vault

    with patch("src.watchers.finance_watcher.FinanceWatcher.check_for_updates",
               return_value=[]):
        orch._init_watchers()

    assert "finance_watcher" in orch._watchers


# ---------------------------------------------------------------------------
# T055.3  FacebookWatcher thread would be created if enabled
# ---------------------------------------------------------------------------

def test_facebook_watcher_not_created_when_disabled(tmp_path):
    vault = make_vault(tmp_path)
    config_path = make_config(tmp_path, vault)

    from src.orchestrator import Orchestrator
    orch = Orchestrator(config_path=config_path)
    orch._vault_root = vault
    orch._init_watchers()

    # facebook.enabled = False in config → not instantiated
    assert "facebook_watcher" not in orch._watchers


# ---------------------------------------------------------------------------
# T055.4  TwitterWatcher thread would be created if enabled
# ---------------------------------------------------------------------------

def test_twitter_watcher_not_created_when_disabled(tmp_path):
    vault = make_vault(tmp_path)
    config_path = make_config(tmp_path, vault)

    from src.orchestrator import Orchestrator
    orch = Orchestrator(config_path=config_path)
    orch._vault_root = vault
    orch._init_watchers()

    assert "twitter_watcher" not in orch._watchers


# ---------------------------------------------------------------------------
# T055.5  Watchdog daemon component integrated (Watchdog imported + constructed)
# ---------------------------------------------------------------------------

def test_watchdog_class_importable_and_constructable(tmp_path):
    vault = make_vault(tmp_path)
    from src.watchers.watchdog import Watchdog

    wd = Watchdog(vault_root=vault, check_interval_s=60, max_restart_attempts=3)
    assert wd.vault_root == vault
    assert wd.check_interval_s == 60


# ---------------------------------------------------------------------------
# T055.6  Plan with requires_ralph:true triggers RalphLoop.run()
# ---------------------------------------------------------------------------

def test_requires_ralph_triggers_ralph_loop(tmp_path):
    vault = make_vault(tmp_path)
    config_path = make_config(tmp_path, vault)

    # Write a plan file with requires_ralph: true
    plan_content = (
        "---\n"
        "id: PLAN_ralph_test\n"
        "status: approved\n"
        "requires_ralph: true\n"
        "---\n\n"
        "## Steps\n1. Do step A\n2. Do step B\n"
    )
    plan_path = os.path.join(vault, "Plans", "PLAN_ralph_test.md")
    with open(plan_path, "w", encoding="utf-8") as f:
        f.write(plan_content)

    from src.orchestrator import Orchestrator

    ralph_run_called = []

    def mock_ralph_run(self):
        ralph_run_called.append(self.task_file)
        # Move task_file to Done/ so loop considers it done
        import shutil
        done_path = os.path.join(vault, "Done", os.path.basename(self.task_file))
        shutil.copy(self.task_file, done_path)
        return {"status": "done", "iterations": 1}

    with patch("src.core.ralph_loop.RalphLoop.run", mock_ralph_run):
        orch = Orchestrator(config_path=config_path)
        orch._vault_root = vault
        orch._scan_cycle_ralph_check()

    assert len(ralph_run_called) >= 1
