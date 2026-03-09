"""Integration tests: backward-compat audit logging — SC-031 (T034)."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest


def make_vault(tmp_path: Path) -> str:
    vault = tmp_path / "vault"
    for folder in ("Logs", "state"):
        (vault / folder).mkdir(parents=True)
    return str(vault)


def read_log_entries(vault_root: str) -> list[dict]:
    from datetime import datetime, timezone
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    log_file = os.path.join(vault_root, "Logs", f"{today}.json")
    if not os.path.exists(log_file):
        return []
    entries = []
    with open(log_file, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries


# ---------------------------------------------------------------------------
# SC-031.1  log_action(vault_root, agent, action, risk_tier, status) succeeds
# ---------------------------------------------------------------------------

def test_log_action_silver_signature_succeeds(tmp_path):
    vault = make_vault(tmp_path)
    from src.core.audit_logger import log_action

    # Silver signature — must not raise
    result = log_action(vault, "orchestrator", "test_action", "LOW", "success")
    assert result  # returns filename string


# ---------------------------------------------------------------------------
# SC-031.2  log_action produces JSON-Lines entry alongside Markdown file
# ---------------------------------------------------------------------------

def test_log_action_produces_json_lines_entry(tmp_path):
    vault = make_vault(tmp_path)
    from src.core.audit_logger import log_action

    log_action(vault, "orchestrator", "startup", "LOW", "success",
               details="Started with 3 watchers")

    entries = read_log_entries(vault)
    assert len(entries) >= 1

    # Find the entry just written
    startup_entries = [e for e in entries if e.get("actor") == "orchestrator"]
    assert len(startup_entries) >= 1


# ---------------------------------------------------------------------------
# SC-031.3  JSON-Lines entry has all 9 Gold mandatory fields
# ---------------------------------------------------------------------------

def test_log_action_json_entry_has_nine_fields(tmp_path):
    vault = make_vault(tmp_path)
    from src.core.audit_logger import log_action

    log_action(vault, "generate_invoice", "invoice_created", "HIGH", "success",
               related_item="WHATSAPP_001.md")

    entries = read_log_entries(vault)
    nine_fields = (
        "timestamp", "action_type", "actor", "target", "parameters",
        "approval_status", "approved_by", "result", "error",
    )
    for entry in entries:
        for field in nine_fields:
            assert field in entry, f"Missing '{field}' in JSON-Lines entry"


# ---------------------------------------------------------------------------
# SC-031.4  Silver 'failure' status maps to Gold result: failure
# ---------------------------------------------------------------------------

def test_silver_failure_maps_to_gold_failure(tmp_path):
    vault = make_vault(tmp_path)
    from src.core.audit_logger import log_action

    log_action(vault, "smtp_mailer", "send_email", "HIGH", "failure",
               details="SMTP timeout")

    entries = read_log_entries(vault)
    failure_entries = [e for e in entries if e.get("result") == "failure"]
    assert len(failure_entries) >= 1


# ---------------------------------------------------------------------------
# SC-031.5  Silver 'skipped' status maps to Gold result: skipped
# ---------------------------------------------------------------------------

def test_silver_skipped_maps_to_gold_skipped(tmp_path):
    vault = make_vault(tmp_path)
    from src.core.audit_logger import log_action

    log_action(vault, "triage_inbox", "triage", "LOW", "skipped",
               details="No new items")

    entries = read_log_entries(vault)
    skipped_entries = [e for e in entries if e.get("result") == "skipped"]
    assert len(skipped_entries) >= 1


# ---------------------------------------------------------------------------
# SC-031.6  log_action with no details/related_item still writes JSON-Lines
# ---------------------------------------------------------------------------

def test_log_action_minimal_call_writes_json_lines(tmp_path):
    vault = make_vault(tmp_path)
    from src.core.audit_logger import log_action

    log_action(vault, "watcher", "poll", "LOW", "success")
    entries = read_log_entries(vault)
    assert len(entries) >= 1


# ---------------------------------------------------------------------------
# SC-031.7  Markdown file also created (Silver compatibility)
# ---------------------------------------------------------------------------

def test_log_action_creates_markdown_file(tmp_path):
    vault = make_vault(tmp_path)
    from src.core.audit_logger import log_action

    filename = log_action(vault, "execute_plan", "plan_run", "MEDIUM", "success")
    logs_dir = os.path.join(vault, "Logs")
    md_files = [f for f in os.listdir(logs_dir) if f.endswith(".md")]
    assert len(md_files) >= 1
    assert filename  # Returns the filename
