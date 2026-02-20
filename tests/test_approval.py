"""
Tests for src.core.approval module.

Covers:
  - create_approval_request: file creation, UUID return, frontmatter correctness
  - check_approval_status: pending / approved / rejected / expired states
  - UUID uniqueness across multiple requests
"""

from __future__ import annotations

import shutil
import uuid as uuid_module
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from src.core.approval import check_approval_status, create_approval_request

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

VAULT_DIRS = ("Pending_Approval", "Approved", "Rejected")


def _make_vault(tmp_path: Path) -> Path:
    """Create a minimal vault directory structure and return its root."""
    vault_root = tmp_path / "vault"
    for folder in VAULT_DIRS:
        (vault_root / folder).mkdir(parents=True, exist_ok=True)
    return vault_root


def _find_approval_file(vault_root: Path, approval_id: str) -> Path | None:
    """Search all vault sub-folders for the approval file by ID."""
    for folder in VAULT_DIRS:
        candidate = vault_root / folder / f"APPROVAL_REQUIRED_{approval_id}.md"
        if candidate.exists():
            return candidate
    return None


def _parse_frontmatter(file_path: Path) -> dict:
    """
    Parse YAML frontmatter delimited by ``---`` lines.

    Returns the parsed dict.  Raises AssertionError if frontmatter is absent.
    """
    text = file_path.read_text(encoding="utf-8")
    lines = text.splitlines()

    assert lines[0].strip() == "---", "File must start with '---' (opening frontmatter delimiter)"

    # Find closing delimiter
    close_idx = None
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            close_idx = i
            break

    assert close_idx is not None, "No closing '---' found in frontmatter"

    yaml_block = "\n".join(lines[1:close_idx])
    return yaml.safe_load(yaml_block)


# ---------------------------------------------------------------------------
# Test 1 — create_approval_request creates a file in Pending_Approval/
# ---------------------------------------------------------------------------


def test_create_approval_request_creates_file_in_pending_approval(tmp_path: Path) -> None:
    """
    After calling create_approval_request the approval file must exist
    inside the Pending_Approval/ sub-directory of vault_root.
    """
    vault_root = _make_vault(tmp_path)

    approval_id = create_approval_request(
        vault_root=str(vault_root),
        plan_id="PLAN_20260217_invoice",
        step_number=1,
        action_type="create_invoice",
        action_description="Create invoice for $500",
        risk_level="HIGH",
    )

    expected_file = vault_root / "Pending_Approval" / f"APPROVAL_REQUIRED_{approval_id}.md"
    assert expected_file.exists(), (
        f"Expected file not found: {expected_file}\n"
        f"Pending_Approval contents: {list((vault_root / 'Pending_Approval').iterdir())}"
    )


# ---------------------------------------------------------------------------
# Test 2 — create_approval_request returns a valid UUID v4
# ---------------------------------------------------------------------------


def test_create_approval_request_returns_valid_uuid(tmp_path: Path) -> None:
    """
    The return value of create_approval_request must be a valid UUID v4 string.
    """
    vault_root = _make_vault(tmp_path)

    approval_id = create_approval_request(
        vault_root=str(vault_root),
        plan_id="PLAN_20260217_invoice",
        step_number=2,
        action_type="send_email",
        action_description="Send payment reminder",
        risk_level="MEDIUM",
    )

    # Must be parseable as UUID
    parsed = uuid_module.UUID(approval_id, version=4)
    assert str(parsed) == approval_id, (
        f"Returned string '{approval_id}' is not a canonical UUID v4 representation"
    )


# ---------------------------------------------------------------------------
# Test 3 — create_approval_request file has correct frontmatter
# ---------------------------------------------------------------------------


def test_create_approval_request_file_has_correct_frontmatter(tmp_path: Path) -> None:
    """
    The approval file's YAML frontmatter must contain all required fields
    with values that match the arguments supplied to create_approval_request.

    Checks:
      id, plan_id, step_number, action_type, action_description, risk_level,
      status == "pending", created (parseable ISO-8601),
      expires == created + 24 hours.
    """
    vault_root = _make_vault(tmp_path)

    plan_id = "PLAN_20260217_test"
    step_number = 3
    action_type = "delete_record"
    action_description = "Permanently delete customer record #42"
    risk_level = "CRITICAL"

    # Capture the time window around the call so we can verify `created`
    before_call = datetime.now(tz=timezone.utc).replace(microsecond=0)
    approval_id = create_approval_request(
        vault_root=str(vault_root),
        plan_id=plan_id,
        step_number=step_number,
        action_type=action_type,
        action_description=action_description,
        risk_level=risk_level,
    )
    after_call = datetime.now(tz=timezone.utc).replace(microsecond=0) + timedelta(seconds=1)

    approval_file = vault_root / "Pending_Approval" / f"APPROVAL_REQUIRED_{approval_id}.md"
    fm = _parse_frontmatter(approval_file)

    # --- id ---
    assert fm["id"] == approval_id, f"Frontmatter id '{fm['id']}' != returned id '{approval_id}'"

    # --- plan_id ---
    assert fm["plan_id"] == plan_id, f"plan_id mismatch: {fm['plan_id']!r}"

    # --- step_number ---
    assert fm["step_number"] == step_number, f"step_number mismatch: {fm['step_number']}"

    # --- action_type ---
    assert fm["action_type"] == action_type, f"action_type mismatch: {fm['action_type']!r}"

    # --- action_description ---
    assert fm["action_description"] == action_description, (
        f"action_description mismatch: {fm['action_description']!r}"
    )

    # --- risk_level ---
    assert fm["risk_level"] == risk_level, f"risk_level mismatch: {fm['risk_level']!r}"

    # --- status ---
    assert fm["status"] == "pending", f"status must be 'pending', got {fm['status']!r}"

    # --- created (ISO-8601, within the call window) ---
    created_raw = fm["created"]
    if isinstance(created_raw, datetime):
        created_dt = created_raw.replace(tzinfo=timezone.utc)
    else:
        created_dt = datetime.fromisoformat(str(created_raw)).replace(tzinfo=timezone.utc)

    assert before_call <= created_dt <= after_call, (
        f"created '{created_dt}' is outside the expected window [{before_call}, {after_call}]"
    )

    # --- expires == created + 24 hours ---
    expires_raw = fm["expires"]
    if isinstance(expires_raw, datetime):
        expires_dt = expires_raw.replace(tzinfo=timezone.utc)
    else:
        expires_dt = datetime.fromisoformat(str(expires_raw)).replace(tzinfo=timezone.utc)

    expected_expires = created_dt + timedelta(hours=24)
    # Allow up to 1-second tolerance for sub-second rounding
    assert abs((expires_dt - expected_expires).total_seconds()) <= 1, (
        f"expires '{expires_dt}' does not equal created + 24 h ('{expected_expires}')"
    )


# ---------------------------------------------------------------------------
# Test 4 — check_approval_status returns "pending" when file is in Pending_Approval/
# ---------------------------------------------------------------------------


def test_check_approval_status_returns_pending_when_in_pending_approval(tmp_path: Path) -> None:
    """
    A freshly created (not moved) approval request must have status "pending".
    """
    vault_root = _make_vault(tmp_path)

    approval_id = create_approval_request(
        vault_root=str(vault_root),
        plan_id="PLAN_20260217_invoice",
        step_number=1,
        action_type="create_invoice",
        action_description="Create invoice for $500",
        risk_level="HIGH",
    )

    status = check_approval_status(vault_root=str(vault_root), approval_id=approval_id)
    assert status == "pending", f"Expected 'pending', got {status!r}"


# ---------------------------------------------------------------------------
# Test 5 — check_approval_status returns "approved" when file is in Approved/
# ---------------------------------------------------------------------------


def test_check_approval_status_returns_approved_when_file_in_approved(tmp_path: Path) -> None:
    """
    Moving the approval file to Approved/ must make check_approval_status
    return "approved".
    """
    vault_root = _make_vault(tmp_path)

    approval_id = create_approval_request(
        vault_root=str(vault_root),
        plan_id="PLAN_20260217_invoice",
        step_number=1,
        action_type="post_invoice",
        action_description="Post invoice #INV-001",
        risk_level="HIGH",
    )

    filename = f"APPROVAL_REQUIRED_{approval_id}.md"
    src_file = vault_root / "Pending_Approval" / filename
    dst_file = vault_root / "Approved" / filename
    shutil.move(str(src_file), str(dst_file))

    status = check_approval_status(vault_root=str(vault_root), approval_id=approval_id)
    assert status == "approved", f"Expected 'approved', got {status!r}"


# ---------------------------------------------------------------------------
# Test 6 — check_approval_status returns "rejected" when file is in Rejected/
# ---------------------------------------------------------------------------


def test_check_approval_status_returns_rejected_when_file_in_rejected(tmp_path: Path) -> None:
    """
    Moving the approval file to Rejected/ must make check_approval_status
    return "rejected".
    """
    vault_root = _make_vault(tmp_path)

    approval_id = create_approval_request(
        vault_root=str(vault_root),
        plan_id="PLAN_20260217_invoice",
        step_number=1,
        action_type="send_email",
        action_description="Send bulk marketing email",
        risk_level="HIGH",
    )

    filename = f"APPROVAL_REQUIRED_{approval_id}.md"
    src_file = vault_root / "Pending_Approval" / filename
    dst_file = vault_root / "Rejected" / filename
    shutil.move(str(src_file), str(dst_file))

    status = check_approval_status(vault_root=str(vault_root), approval_id=approval_id)
    assert status == "rejected", f"Expected 'rejected', got {status!r}"


# ---------------------------------------------------------------------------
# Test 7 — check_approval_status returns "expired" when file is older than 24 h
# ---------------------------------------------------------------------------


def test_check_approval_status_returns_expired_when_past_24_hours(tmp_path: Path) -> None:
    """
    When the current time is past the ``expires`` timestamp stored in the
    frontmatter the status must be "expired", even though the file is still
    sitting in Pending_Approval/ (i.e., no human has acted on it).

    Strategy: create the request normally, then re-read the file and rewrite
    the frontmatter so that ``expires`` is set to 25 hours ago.  Finally,
    mock ``datetime.now`` inside the module under test so it returns a time
    that is definitively past the (patched) expiry timestamp.
    """
    vault_root = _make_vault(tmp_path)

    approval_id = create_approval_request(
        vault_root=str(vault_root),
        plan_id="PLAN_20260217_invoice",
        step_number=4,
        action_type="delete_invoice",
        action_description="Delete posted invoice #INV-999",
        risk_level="CRITICAL",
    )

    approval_file = vault_root / "Pending_Approval" / f"APPROVAL_REQUIRED_{approval_id}.md"

    # --- Patch the file so expires is 25 hours in the past ---
    now = datetime.now(timezone.utc)
    past_created = now - timedelta(hours=26)
    past_expires = now - timedelta(hours=2)  # definitely in the past

    text = approval_file.read_text(encoding="utf-8")
    lines = text.splitlines()

    # Locate frontmatter block
    assert lines[0].strip() == "---"
    close_idx = next(i for i, l in enumerate(lines[1:], 1) if l.strip() == "---")
    yaml_block = "\n".join(lines[1:close_idx])
    fm = yaml.safe_load(yaml_block)

    fm["created"] = past_created.strftime("%Y-%m-%dT%H:%M:%S")
    fm["expires"] = past_expires.strftime("%Y-%m-%dT%H:%M:%S")

    new_yaml = yaml.dump(fm, default_flow_style=False, allow_unicode=True).rstrip()
    new_content = "---\n" + new_yaml + "\n---\n" + "\n".join(lines[close_idx + 1:])
    approval_file.write_text(new_content, encoding="utf-8")

    # No mocking needed — the expires time is already in the past relative to now
    status = check_approval_status(vault_root=str(vault_root), approval_id=approval_id)

    assert status == "expired", f"Expected 'expired', got {status!r}"


# ---------------------------------------------------------------------------
# Test 8 — Multiple approval requests have unique UUIDs
# ---------------------------------------------------------------------------


def test_multiple_approval_requests_have_unique_uuids(tmp_path: Path) -> None:
    """
    Creating N approval requests in sequence must yield N distinct UUID strings.
    """
    vault_root = _make_vault(tmp_path)
    n_requests = 20
    ids: list[str] = []

    for i in range(n_requests):
        approval_id = create_approval_request(
            vault_root=str(vault_root),
            plan_id=f"PLAN_2026_{i:04d}",
            step_number=i,
            action_type="create_invoice",
            action_description=f"Create invoice #{i}",
            risk_level="LOW",
        )
        ids.append(approval_id)

    unique_ids = set(ids)
    assert len(unique_ids) == n_requests, (
        f"Expected {n_requests} unique UUIDs, but only {len(unique_ids)} were unique.\n"
        f"Duplicates: {[uid for uid in ids if ids.count(uid) > 1]}"
    )

    # Bonus: every ID must be a valid UUID v4
    for uid in ids:
        parsed = uuid_module.UUID(uid, version=4)
        assert str(parsed) == uid, f"'{uid}' is not a canonical UUID v4 string"
