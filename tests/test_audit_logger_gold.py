"""Tests for Gold Tier audit_logger — JSON-Lines schema and backward compat."""
import json
import os
from datetime import datetime, timedelta, timezone

import pytest


def _read_jsonl(path: str) -> list[dict]:
    entries = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries


def test_log_writes_jsonl_entry(tmp_path):
    """log() writes a JSON-Lines entry to vault/Logs/YYYY-MM-DD.json."""
    from src.core.audit_logger import log
    vault = str(tmp_path)
    log(
        vault_root=vault,
        action_type="test_action",
        actor="orchestrator",
        target="vault/test",
        parameters={"key": "value"},
        approval_status="auto",
        approved_by="system",
        result="success",
        error=None,
    )
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    log_file = os.path.join(vault, "Logs", f"{today}.json")
    assert os.path.exists(log_file)
    entries = _read_jsonl(log_file)
    assert len(entries) == 1


def test_log_entry_has_all_nine_fields(tmp_path):
    """Every JSON-Lines entry must have all 9 mandatory fields."""
    from src.core.audit_logger import log
    vault = str(tmp_path)
    log(
        vault_root=vault,
        action_type="post_tweet",
        actor="orchestrator",
        target="twitter",
        parameters={},
        approval_status="approved",
        approved_by="human",
        result="success",
        error=None,
    )
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    log_file = os.path.join(vault, "Logs", f"{today}.json")
    entry = _read_jsonl(log_file)[0]
    required = ["timestamp", "action_type", "actor", "target", "parameters",
                "approval_status", "approved_by", "result", "error"]
    for field in required:
        assert field in entry, f"Missing field: {field}"


def test_no_null_for_mandatory_string_fields(tmp_path):
    """Mandatory string fields must not be None."""
    from src.core.audit_logger import log
    vault = str(tmp_path)
    log(
        vault_root=vault,
        action_type="create_invoice",
        actor="mcp:odoo-mcp",
        target="odoo",
        parameters={"amount": 100},
        approval_status="pending",
        approved_by=None,
        result="success",
        error=None,
    )
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    log_file = os.path.join(vault, "Logs", f"{today}.json")
    entry = _read_jsonl(log_file)[0]
    for field in ["timestamp", "action_type", "actor", "target", "result"]:
        assert entry[field] is not None


def test_result_degraded_accepted(tmp_path):
    """result='degraded' is a valid value (not rejected)."""
    from src.core.audit_logger import log
    vault = str(tmp_path)
    log(
        vault_root=vault,
        action_type="finance_poll",
        actor="watcher:finance",
        target="odoo",
        parameters={},
        approval_status="auto",
        approved_by="system",
        result="degraded",
        error="Odoo offline",
    )
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    log_file = os.path.join(vault, "Logs", f"{today}.json")
    entry = _read_jsonl(log_file)[0]
    assert entry["result"] == "degraded"
    assert entry["error"] == "Odoo offline"


def test_backward_compat_log_action_succeeds(tmp_path):
    """Old log_action(vault_root, agent, action, risk_tier, status) must not raise."""
    from src.core.audit_logger import log_action
    vault = str(tmp_path)
    result = log_action(vault, "orchestrator", "test_action", "LOW", "success")
    assert result is not None


def test_backward_compat_writes_jsonl(tmp_path):
    """log_action() should also write a JSON-Lines entry."""
    from src.core.audit_logger import log_action
    vault = str(tmp_path)
    log_action(vault, "orchestrator", "test_action", "LOW", "success", details="detail text")
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    log_file = os.path.join(vault, "Logs", f"{today}.json")
    assert os.path.exists(log_file)
    entries = _read_jsonl(log_file)
    assert len(entries) >= 1


def test_archive_moves_old_file(tmp_path):
    """archive_old_logs() moves files older than retention_days to Archive/."""
    from src.core.audit_logger import archive_old_logs
    vault = str(tmp_path)
    logs_dir = os.path.join(vault, "Logs")
    archive_dir = os.path.join(vault, "Logs", "Archive")
    os.makedirs(logs_dir, exist_ok=True)
    # Create a log file with an old date
    old_date = (datetime.now(timezone.utc) - timedelta(days=91)).strftime("%Y-%m-%d")
    old_file = os.path.join(logs_dir, f"{old_date}.json")
    with open(old_file, "w") as f:
        f.write('{"test": 1}\n')
    archive_old_logs(vault, retention_days=90)
    assert not os.path.exists(old_file)
    assert os.path.exists(os.path.join(archive_dir, f"{old_date}.json"))


def test_archive_skips_recent_file(tmp_path):
    """archive_old_logs() does NOT move recent log files."""
    from src.core.audit_logger import archive_old_logs
    vault = str(tmp_path)
    logs_dir = os.path.join(vault, "Logs")
    os.makedirs(logs_dir, exist_ok=True)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    recent_file = os.path.join(logs_dir, f"{today}.json")
    with open(recent_file, "w") as f:
        f.write('{"test": 1}\n')
    archive_old_logs(vault, retention_days=90)
    assert os.path.exists(recent_file)


def test_valueerror_on_missing_mandatory_field(tmp_path):
    """log() raises ValueError if a mandatory field is empty string."""
    from src.core.audit_logger import log
    vault = str(tmp_path)
    with pytest.raises(ValueError, match="action_type"):
        log(
            vault_root=vault,
            action_type="",  # empty — should raise
            actor="orchestrator",
            target="test",
            parameters={},
            approval_status="auto",
            approved_by="system",
            result="success",
            error=None,
        )


def test_multiple_entries_in_same_file(tmp_path):
    """Multiple log() calls on the same day append to the same file."""
    from src.core.audit_logger import log
    vault = str(tmp_path)
    for i in range(3):
        log(
            vault_root=vault,
            action_type=f"action_{i}",
            actor="orchestrator",
            target="test",
            parameters={"i": i},
            approval_status="auto",
            approved_by="system",
            result="success",
            error=None,
        )
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    log_file = os.path.join(vault, "Logs", f"{today}.json")
    entries = _read_jsonl(log_file)
    assert len(entries) == 3
