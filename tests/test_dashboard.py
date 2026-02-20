"""Tests for src.skills.update_dashboard."""

import os
from pathlib import Path

import pytest
import yaml

from src.core.vault import write_frontmatter_file, read_frontmatter_file, list_folder
from src.skills import update_dashboard


VAULT_DIRS = ("Inbox", "Needs_Action", "Plans", "Done", "Logs",
              "Pending_Approval", "Approved", "Rejected", "Watch", "state")


def make_vault(tmp_path: Path) -> str:
    vault_root = tmp_path / "vault"
    for folder in VAULT_DIRS:
        (vault_root / folder).mkdir(parents=True, exist_ok=True)
    return str(vault_root)


def seed_item(vault_root: str, folder: str, filename: str, **meta_overrides):
    metadata = {"id": filename, "type": "general", "status": "new", "source": "test",
                "timestamp": "2026-02-17T00:00:00", "priority": "MEDIUM"}
    metadata.update(meta_overrides)
    write_frontmatter_file(vault_root, f"{folder}/{filename}", metadata, "Test content")


class TestDashboardFolderCounting:
    def test_empty_vault_shows_zero_counts(self, tmp_path):
        vault_root = make_vault(tmp_path)
        result = update_dashboard.run(vault_root)
        assert result["processed"] == 1
        content = (Path(vault_root) / "Dashboard.md").read_text(encoding="utf-8")
        assert "| Inbox | 0 |" in content

    def test_counts_items_in_inbox(self, tmp_path):
        vault_root = make_vault(tmp_path)
        seed_item(vault_root, "Inbox", "item1.md")
        seed_item(vault_root, "Inbox", "item2.md")
        update_dashboard.run(vault_root)
        content = (Path(vault_root) / "Dashboard.md").read_text(encoding="utf-8")
        assert "| Inbox | 2 |" in content

    def test_counts_items_in_multiple_folders(self, tmp_path):
        vault_root = make_vault(tmp_path)
        seed_item(vault_root, "Inbox", "a.md")
        seed_item(vault_root, "Plans", "b.md")
        seed_item(vault_root, "Done", "c.md")
        seed_item(vault_root, "Done", "d.md")
        update_dashboard.run(vault_root)
        content = (Path(vault_root) / "Dashboard.md").read_text(encoding="utf-8")
        assert "| Inbox | 1 |" in content
        assert "| Plans | 1 |" in content
        assert "| Done | 2 |" in content


class TestDashboardWatcherHealth:
    def test_no_state_file_shows_not_started(self, tmp_path):
        vault_root = make_vault(tmp_path)
        update_dashboard.run(vault_root)
        content = (Path(vault_root) / "Dashboard.md").read_text(encoding="utf-8")
        assert "not started" in content or "unknown" in content

    def test_with_state_file_shows_running(self, tmp_path):
        import json
        vault_root = make_vault(tmp_path)
        state_file = os.path.join(vault_root, "state", "filesystem_watcher_state.json")
        with open(state_file, "w") as f:
            json.dump({"watcher_name": "filesystem_watcher",
                        "last_updated": "2026-02-17T12:00:00",
                        "processed_ids": []}, f)
        update_dashboard.run(vault_root)
        content = (Path(vault_root) / "Dashboard.md").read_text(encoding="utf-8")
        assert "running" in content


class TestDashboardPendingApprovals:
    def test_no_approvals_shows_message(self, tmp_path):
        vault_root = make_vault(tmp_path)
        update_dashboard.run(vault_root)
        content = (Path(vault_root) / "Dashboard.md").read_text(encoding="utf-8")
        assert "No pending approval requests" in content

    def test_with_approvals_shows_table(self, tmp_path):
        vault_root = make_vault(tmp_path)
        write_frontmatter_file(vault_root, "Pending_Approval/APPROVAL_test.md",
                                {"action_type": "create_invoice", "risk_level": "HIGH",
                                 "created": "2026-02-17T00:00:00"}, "Approve?")
        update_dashboard.run(vault_root)
        content = (Path(vault_root) / "Dashboard.md").read_text(encoding="utf-8")
        assert "create_invoice" in content
        assert "HIGH" in content


class TestDashboardRecentLogs:
    def test_no_logs_shows_message(self, tmp_path):
        vault_root = make_vault(tmp_path)
        update_dashboard.run(vault_root)
        content = (Path(vault_root) / "Dashboard.md").read_text(encoding="utf-8")
        assert "No recent actions" in content

    def test_with_logs_shows_entries(self, tmp_path):
        vault_root = make_vault(tmp_path)
        write_frontmatter_file(vault_root, "Logs/AUDIT_test.md",
                                {"timestamp": "2026-02-17T12:00:00", "agent": "triage",
                                 "action": "triaged item", "status": "success"}, "Log entry")
        update_dashboard.run(vault_root)
        content = (Path(vault_root) / "Dashboard.md").read_text(encoding="utf-8")
        assert "triage" in content


class TestDashboardReturnValue:
    def test_returns_correct_structure(self, tmp_path):
        vault_root = make_vault(tmp_path)
        result = update_dashboard.run(vault_root)
        assert result["processed"] == 1
        assert result["errors"] == []
        assert result["skipped"] == 0

    def test_dashboard_has_frontmatter(self, tmp_path):
        vault_root = make_vault(tmp_path)
        update_dashboard.run(vault_root)
        metadata, _ = read_frontmatter_file(vault_root, "Dashboard.md")
        assert metadata["type"] == "dashboard"
        assert metadata["auto_generated"] is True
