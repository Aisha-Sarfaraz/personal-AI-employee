"""Integration tests: Gold audit log schema validation — SC-030 (T033)."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from src.core.audit_logger import log as audit_log


NINE_FIELDS = (
    "timestamp",
    "action_type",
    "actor",
    "target",
    "parameters",
    "approval_status",
    "approved_by",
    "result",
    "error",
)


def make_vault(tmp_path: Path) -> str:
    vault = tmp_path / "vault"
    (vault / "Logs").mkdir(parents=True)
    return str(vault)


def read_log_entries(vault_root: str) -> list[dict]:
    """Read all JSON-Lines entries from today's log file."""
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
# SC-030.1  JSON-Lines entry written for action_type: post_tweet
# ---------------------------------------------------------------------------

def test_post_tweet_entry_written(tmp_path):
    vault = make_vault(tmp_path)
    audit_log(
        vault_root=vault,
        action_type="post_tweet",
        actor="post_twitter",
        target="vault/Pending_Approval/TWEET_001.md",
        parameters={"character_count": 240},
        approval_status="pending",
        result="success",
    )
    entries = read_log_entries(vault)
    assert any(e["action_type"] == "post_tweet" for e in entries)


# ---------------------------------------------------------------------------
# SC-030.2  All 9 mandatory fields present in each entry
# ---------------------------------------------------------------------------

def test_all_nine_fields_present(tmp_path):
    vault = make_vault(tmp_path)
    audit_log(
        vault_root=vault,
        action_type="create_invoice",
        actor="generate_invoice",
        target="vault/Pending_Approval/INVOICE_001.md",
        parameters={"partner": "ACME"},
        approval_status="pending",
        result="success",
    )
    entries = read_log_entries(vault)
    assert len(entries) >= 1
    for entry in entries:
        for field in NINE_FIELDS:
            assert field in entry, f"Missing field: {field}"


# ---------------------------------------------------------------------------
# SC-030.3  No null values for mandatory string fields
# ---------------------------------------------------------------------------

def test_no_null_for_mandatory_string_fields(tmp_path):
    vault = make_vault(tmp_path)
    audit_log(
        vault_root=vault,
        action_type="watchdog_restart",
        actor="watchdog",
        target="watcher:finance_watcher",
        approval_status="auto",
        result="success",
    )
    entries = read_log_entries(vault)
    mandatory_str = ("action_type", "actor", "target", "approval_status", "result")
    for entry in entries:
        for field in mandatory_str:
            assert entry.get(field) is not None
            assert entry[field] != ""


# ---------------------------------------------------------------------------
# SC-030.4  result: degraded is accepted
# ---------------------------------------------------------------------------

def test_result_degraded_accepted(tmp_path):
    vault = make_vault(tmp_path)
    audit_log(
        vault_root=vault,
        action_type="finance_poll",
        actor="finance_watcher",
        target="vault/Accounting/Current_Month.md",
        approval_status="auto",
        result="degraded",
        error="Odoo connection refused",
    )
    entries = read_log_entries(vault)
    degraded = [e for e in entries if e.get("result") == "degraded"]
    assert len(degraded) >= 1
    assert degraded[-1]["error"] == "Odoo connection refused"


# ---------------------------------------------------------------------------
# SC-030.5  Multiple entries: each validates independently
# ---------------------------------------------------------------------------

def test_multiple_entries_each_valid(tmp_path):
    vault = make_vault(tmp_path)
    action_types = ["post_tweet", "create_invoice", "watchdog_restart"]
    for action_type in action_types:
        audit_log(
            vault_root=vault,
            action_type=action_type,
            actor="test_actor",
            target="test_target",
            approval_status="auto",
            result="success",
        )

    entries = read_log_entries(vault)
    assert len(entries) >= 3
    for entry in entries:
        for field in NINE_FIELDS:
            assert field in entry


# ---------------------------------------------------------------------------
# SC-030.6  ValueError raised when mandatory field is empty
# ---------------------------------------------------------------------------

def test_value_error_on_empty_mandatory_field(tmp_path):
    vault = make_vault(tmp_path)
    with pytest.raises(ValueError, match="action_type"):
        audit_log(
            vault_root=vault,
            action_type="",  # empty = invalid
            actor="test",
            target="test",
            approval_status="auto",
            result="success",
        )


# ---------------------------------------------------------------------------
# SC-030.7  Timestamp is ISO8601 format
# ---------------------------------------------------------------------------

def test_timestamp_is_iso8601(tmp_path):
    vault = make_vault(tmp_path)
    audit_log(
        vault_root=vault,
        action_type="post_facebook",
        actor="post_facebook",
        target="vault/Pending_Approval/FB_POST_001.md",
        approval_status="pending",
        result="success",
    )
    entries = read_log_entries(vault)
    fb_entries = [e for e in entries if e.get("action_type") == "post_facebook"]
    assert len(fb_entries) >= 1
    ts = fb_entries[-1]["timestamp"]
    # Should parse as ISO8601 — ends with Z
    assert "T" in ts
    assert ts.endswith("Z") or "+" in ts or ts.count("-") >= 2
