"""
Tests for src.core.audit_logger.log_action

Covers:
  1. Creates AUDIT_*.md file inside Logs/ directory
  2. File contains correct YAML frontmatter fields with proper values
  3. Return value is the filename (not full path)
  4. All parameters (including optional) are populated when supplied
  5. Empty optional params (details, related_item) still produce a valid file
  6. Multiple calls produce separate, independent files
  7. Logs/ directory is auto-created when it does not exist beforehand
"""

import os
import re
from pathlib import Path

import pytest
import yaml

from src.core.audit_logger import log_action


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

VALID_RISK_TIERS = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
VALID_STATUSES = {"success", "failure", "skipped", "expired"}

# Pattern that every AUDIT filename must satisfy
_AUDIT_FILENAME_RE = re.compile(r"^AUDIT_\d{8}T\d{6}_[^/\\]+\.md$")


def _parse_frontmatter(text: str) -> dict:
    """Extract and parse YAML frontmatter from a Markdown file's content.

    Raises AssertionError if the file does not open/close with '---'.
    """
    lines = text.splitlines()
    assert lines[0].strip() == "---", "File must start with '---'"
    end = lines.index("---", 1)
    yaml_block = "\n".join(lines[1:end])
    return yaml.safe_load(yaml_block)


def _read_audit_file(logs_dir: Path, filename: str) -> tuple[dict, str]:
    """Read an audit file; return (frontmatter_dict, full_text)."""
    file_path = logs_dir / filename
    assert file_path.exists(), f"Expected file not found: {file_path}"
    full_text = file_path.read_text(encoding="utf-8")
    frontmatter = _parse_frontmatter(full_text)
    return frontmatter, full_text


# ---------------------------------------------------------------------------
# Test 1 – log_action creates AUDIT_*.md inside Logs/
# ---------------------------------------------------------------------------

class TestFileCreation:
    def test_creates_audit_file_in_logs_folder(self, tmp_path):
        """log_action must create exactly one AUDIT_*.md file inside Logs/."""
        logs_dir = tmp_path / "Logs"
        logs_dir.mkdir()

        filename = log_action(
            vault_root=str(tmp_path),
            agent="triage_inbox",
            action="classified item",
            risk_tier="LOW",
            status="success",
        )

        # The file should live in Logs/
        assert (logs_dir / filename).exists(), (
            f"Expected {filename} to exist inside {logs_dir}"
        )

    def test_filename_matches_expected_pattern(self, tmp_path):
        """Returned filename must match AUDIT_<timestamp>_<agent>.md."""
        (tmp_path / "Logs").mkdir()

        filename = log_action(
            vault_root=str(tmp_path),
            agent="finance_agent",
            action="recorded expense",
            risk_tier="HIGH",
            status="success",
        )

        assert _AUDIT_FILENAME_RE.match(filename), (
            f"Filename '{filename}' does not match expected pattern"
        )

    def test_file_has_md_extension(self, tmp_path):
        """Returned filename must end with .md."""
        (tmp_path / "Logs").mkdir()

        filename = log_action(
            vault_root=str(tmp_path),
            agent="social_agent",
            action="drafted post",
            risk_tier="MEDIUM",
            status="skipped",
        )

        assert filename.endswith(".md"), f"Expected .md extension, got: {filename}"


# ---------------------------------------------------------------------------
# Test 2 – YAML frontmatter contains all required fields with correct values
# ---------------------------------------------------------------------------

class TestFrontmatterFields:
    def test_frontmatter_contains_all_required_keys(self, tmp_path):
        """All required frontmatter keys must be present."""
        logs_dir = tmp_path / "Logs"
        logs_dir.mkdir()

        filename = log_action(
            vault_root=str(tmp_path),
            agent="audit_agent",
            action="compliance check",
            risk_tier="MEDIUM",
            status="success",
            details="All policies met",
            related_item="POLICY_001",
        )

        fm, _ = _read_audit_file(logs_dir, filename)
        required_keys = {"id", "timestamp", "agent", "action", "risk_tier", "status",
                         "related_item", "details"}
        missing = required_keys - fm.keys()
        assert not missing, f"Missing frontmatter keys: {missing}"

    def test_frontmatter_agent_matches_input(self, tmp_path):
        """frontmatter 'agent' must equal the agent argument passed in."""
        logs_dir = tmp_path / "Logs"
        logs_dir.mkdir()

        filename = log_action(
            vault_root=str(tmp_path),
            agent="communication_agent",
            action="sent email",
            risk_tier="HIGH",
            status="success",
        )
        fm, _ = _read_audit_file(logs_dir, filename)
        assert fm["agent"] == "communication_agent"

    def test_frontmatter_action_matches_input(self, tmp_path):
        """frontmatter 'action' must equal the action argument passed in."""
        logs_dir = tmp_path / "Logs"
        logs_dir.mkdir()

        filename = log_action(
            vault_root=str(tmp_path),
            agent="triage_inbox",
            action="classified item",
            risk_tier="LOW",
            status="success",
        )
        fm, _ = _read_audit_file(logs_dir, filename)
        assert fm["action"] == "classified item"

    def test_frontmatter_risk_tier_matches_input(self, tmp_path):
        """frontmatter 'risk_tier' must equal the risk_tier argument."""
        logs_dir = tmp_path / "Logs"
        logs_dir.mkdir()

        for tier in VALID_RISK_TIERS:
            filename = log_action(
                vault_root=str(tmp_path),
                agent="monitor",
                action="health check",
                risk_tier=tier,
                status="success",
            )
            fm, _ = _read_audit_file(logs_dir, filename)
            assert fm["risk_tier"] == tier, (
                f"Expected risk_tier '{tier}', got '{fm['risk_tier']}'"
            )

    def test_frontmatter_status_matches_input(self, tmp_path):
        """frontmatter 'status' must equal the status argument."""
        logs_dir = tmp_path / "Logs"
        logs_dir.mkdir()

        for status in VALID_STATUSES:
            filename = log_action(
                vault_root=str(tmp_path),
                agent="monitor",
                action="health check",
                risk_tier="LOW",
                status=status,
            )
            fm, _ = _read_audit_file(logs_dir, filename)
            assert fm["status"] == status, (
                f"Expected status '{status}', got '{fm['status']}'"
            )

    def test_frontmatter_id_is_non_empty_string(self, tmp_path):
        """frontmatter 'id' must be a non-empty string."""
        logs_dir = tmp_path / "Logs"
        logs_dir.mkdir()

        filename = log_action(
            vault_root=str(tmp_path),
            agent="triage_inbox",
            action="classified item",
            risk_tier="LOW",
            status="success",
        )
        fm, _ = _read_audit_file(logs_dir, filename)
        assert isinstance(fm["id"], str) and fm["id"].strip(), (
            "frontmatter 'id' must be a non-empty string"
        )

    def test_frontmatter_id_starts_with_AUDIT(self, tmp_path):
        """frontmatter 'id' must start with 'AUDIT_'."""
        logs_dir = tmp_path / "Logs"
        logs_dir.mkdir()

        filename = log_action(
            vault_root=str(tmp_path),
            agent="triage_inbox",
            action="classified item",
            risk_tier="LOW",
            status="success",
        )
        fm, _ = _read_audit_file(logs_dir, filename)
        assert fm["id"].startswith("AUDIT_"), (
            f"'id' should start with 'AUDIT_', got: {fm['id']}"
        )

    def test_frontmatter_timestamp_is_iso8601(self, tmp_path):
        """frontmatter 'timestamp' must be a valid ISO-8601 datetime string."""
        logs_dir = tmp_path / "Logs"
        logs_dir.mkdir()

        filename = log_action(
            vault_root=str(tmp_path),
            agent="triage_inbox",
            action="classified item",
            risk_tier="LOW",
            status="success",
        )
        fm, _ = _read_audit_file(logs_dir, filename)
        timestamp = fm["timestamp"]
        # Accept either a string or a datetime object (PyYAML may parse it)
        timestamp_str = str(timestamp)
        iso_re = re.compile(r"^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}")
        assert iso_re.match(timestamp_str), (
            f"Timestamp '{timestamp_str}' does not match ISO-8601"
        )


# ---------------------------------------------------------------------------
# Test 3 – Return value is the filename
# ---------------------------------------------------------------------------

class TestReturnValue:
    def test_returns_string(self, tmp_path):
        """log_action must return a string."""
        (tmp_path / "Logs").mkdir()

        result = log_action(
            vault_root=str(tmp_path),
            agent="triage_inbox",
            action="classified item",
            risk_tier="LOW",
            status="success",
        )
        assert isinstance(result, str), f"Expected str, got {type(result)}"

    def test_return_value_is_filename_not_full_path(self, tmp_path):
        """Returned value must be just the filename, no directory separators."""
        (tmp_path / "Logs").mkdir()

        filename = log_action(
            vault_root=str(tmp_path),
            agent="triage_inbox",
            action="classified item",
            risk_tier="LOW",
            status="success",
        )
        assert os.sep not in filename and "/" not in filename, (
            f"Return value should be a plain filename, not a path: {filename}"
        )

    def test_returned_filename_corresponds_to_real_file(self, tmp_path):
        """The returned filename must point to a real file inside Logs/."""
        logs_dir = tmp_path / "Logs"
        logs_dir.mkdir()

        filename = log_action(
            vault_root=str(tmp_path),
            agent="triage_inbox",
            action="classified item",
            risk_tier="LOW",
            status="success",
        )
        assert (logs_dir / filename).is_file(), (
            f"Logs/{filename} does not exist or is not a regular file"
        )


# ---------------------------------------------------------------------------
# Test 4 – All parameters populate all fields
# ---------------------------------------------------------------------------

class TestAllParameters:
    def test_all_parameters_appear_in_frontmatter(self, tmp_path):
        """When all parameters are provided, every frontmatter field is populated."""
        logs_dir = tmp_path / "Logs"
        logs_dir.mkdir()

        filename = log_action(
            vault_root=str(tmp_path),
            agent="finance_agent",
            action="reconcile transaction",
            risk_tier="CRITICAL",
            status="failure",
            details="Bank feed mismatch on 2026-02-17",
            related_item="FILE_20260217_invoice",
        )
        fm, _ = _read_audit_file(logs_dir, filename)

        assert fm["agent"] == "finance_agent"
        assert fm["action"] == "reconcile transaction"
        assert fm["risk_tier"] == "CRITICAL"
        assert fm["status"] == "failure"
        assert fm["details"] == "Bank feed mismatch on 2026-02-17"
        assert fm["related_item"] == "FILE_20260217_invoice"

    def test_details_value_stored_verbatim(self, tmp_path):
        """details string must be stored exactly as supplied."""
        logs_dir = tmp_path / "Logs"
        logs_dir.mkdir()

        long_detail = "Classified as financial, priority HIGH; routed to finance_agent"
        filename = log_action(
            vault_root=str(tmp_path),
            agent="triage_inbox",
            action="classified item",
            risk_tier="LOW",
            status="success",
            details=long_detail,
        )
        fm, _ = _read_audit_file(logs_dir, filename)
        assert fm["details"] == long_detail

    def test_related_item_value_stored_verbatim(self, tmp_path):
        """related_item string must be stored exactly as supplied."""
        logs_dir = tmp_path / "Logs"
        logs_dir.mkdir()

        filename = log_action(
            vault_root=str(tmp_path),
            agent="triage_inbox",
            action="classified item",
            risk_tier="LOW",
            status="success",
            related_item="FILE_20260217_invoice",
        )
        fm, _ = _read_audit_file(logs_dir, filename)
        assert fm["related_item"] == "FILE_20260217_invoice"


# ---------------------------------------------------------------------------
# Test 5 – Empty optional params still work
# ---------------------------------------------------------------------------

class TestEmptyOptionalParams:
    def test_empty_details_and_related_item_produce_valid_file(self, tmp_path):
        """Calling log_action without optional params must not raise and
        must still create a parseable file."""
        logs_dir = tmp_path / "Logs"
        logs_dir.mkdir()

        filename = log_action(
            vault_root=str(tmp_path),
            agent="monitor",
            action="health check",
            risk_tier="LOW",
            status="success",
            # details and related_item intentionally omitted
        )
        fm, full_text = _read_audit_file(logs_dir, filename)

        # Required identity fields must still be present
        assert fm["agent"] == "monitor"
        assert fm["action"] == "health check"
        assert fm["risk_tier"] == "LOW"
        assert fm["status"] == "success"

    def test_empty_details_field_is_present_in_frontmatter(self, tmp_path):
        """frontmatter 'details' key must exist even when not supplied."""
        logs_dir = tmp_path / "Logs"
        logs_dir.mkdir()

        filename = log_action(
            vault_root=str(tmp_path),
            agent="monitor",
            action="health check",
            risk_tier="LOW",
            status="success",
        )
        fm, _ = _read_audit_file(logs_dir, filename)
        assert "details" in fm, "frontmatter must include 'details' key"

    def test_empty_related_item_field_is_present_in_frontmatter(self, tmp_path):
        """frontmatter 'related_item' key must exist even when not supplied."""
        logs_dir = tmp_path / "Logs"
        logs_dir.mkdir()

        filename = log_action(
            vault_root=str(tmp_path),
            agent="monitor",
            action="health check",
            risk_tier="LOW",
            status="success",
        )
        fm, _ = _read_audit_file(logs_dir, filename)
        assert "related_item" in fm, "frontmatter must include 'related_item' key"

    def test_explicit_empty_string_for_optional_params(self, tmp_path):
        """Explicit empty string for optional params must not raise."""
        logs_dir = tmp_path / "Logs"
        logs_dir.mkdir()

        filename = log_action(
            vault_root=str(tmp_path),
            agent="monitor",
            action="health check",
            risk_tier="LOW",
            status="success",
            details="",
            related_item="",
        )
        assert (logs_dir / filename).exists()


# ---------------------------------------------------------------------------
# Test 6 – Multiple calls create separate files
# ---------------------------------------------------------------------------

class TestMultipleCalls:
    def test_two_calls_produce_two_distinct_files(self, tmp_path):
        """Each log_action invocation must produce a unique file."""
        logs_dir = tmp_path / "Logs"
        logs_dir.mkdir()

        f1 = log_action(
            vault_root=str(tmp_path),
            agent="triage_inbox",
            action="classified item",
            risk_tier="LOW",
            status="success",
        )
        f2 = log_action(
            vault_root=str(tmp_path),
            agent="triage_inbox",
            action="classified item",
            risk_tier="LOW",
            status="success",
        )

        assert f1 != f2, "Two separate calls must not return the same filename"
        assert (logs_dir / f1).exists()
        assert (logs_dir / f2).exists()

    def test_many_calls_each_file_is_independent(self, tmp_path):
        """Ten consecutive calls must produce ten independent files."""
        logs_dir = tmp_path / "Logs"
        logs_dir.mkdir()

        filenames = []
        for i in range(10):
            name = log_action(
                vault_root=str(tmp_path),
                agent=f"agent_{i}",
                action=f"action {i}",
                risk_tier="LOW",
                status="success",
                details=f"detail {i}",
            )
            filenames.append(name)

        # All filenames are unique
        assert len(set(filenames)) == 10, "All 10 filenames must be unique"
        # All files exist
        for name in filenames:
            assert (logs_dir / name).exists(), f"{name} does not exist"

    def test_separate_calls_have_independent_content(self, tmp_path):
        """Two calls with different agents must not share content."""
        logs_dir = tmp_path / "Logs"
        logs_dir.mkdir()

        f1 = log_action(
            vault_root=str(tmp_path),
            agent="agent_alpha",
            action="alpha action",
            risk_tier="LOW",
            status="success",
            details="alpha details",
        )
        f2 = log_action(
            vault_root=str(tmp_path),
            agent="agent_beta",
            action="beta action",
            risk_tier="HIGH",
            status="failure",
            details="beta details",
        )

        fm1, _ = _read_audit_file(logs_dir, f1)
        fm2, _ = _read_audit_file(logs_dir, f2)

        assert fm1["agent"] == "agent_alpha"
        assert fm1["action"] == "alpha action"
        assert fm1["details"] == "alpha details"

        assert fm2["agent"] == "agent_beta"
        assert fm2["action"] == "beta action"
        assert fm2["details"] == "beta details"


# ---------------------------------------------------------------------------
# Test 7 – Logs/ directory is auto-created if absent
# ---------------------------------------------------------------------------

class TestAutoCreateLogsDirectory:
    def test_creates_logs_dir_when_missing(self, tmp_path):
        """log_action must create Logs/ automatically if it does not exist."""
        logs_dir = tmp_path / "Logs"
        assert not logs_dir.exists(), "Pre-condition: Logs/ must not exist yet"

        filename = log_action(
            vault_root=str(tmp_path),
            agent="triage_inbox",
            action="classified item",
            risk_tier="LOW",
            status="success",
        )

        assert logs_dir.exists(), "Logs/ directory was not created"
        assert logs_dir.is_dir(), "Logs/ must be a directory"
        assert (logs_dir / filename).exists(), "Audit file must exist inside Logs/"

    def test_still_creates_valid_file_after_auto_creating_dir(self, tmp_path):
        """File created alongside the auto-created Logs/ dir must be parseable."""
        filename = log_action(
            vault_root=str(tmp_path),
            agent="triage_inbox",
            action="classified item",
            risk_tier="LOW",
            status="success",
        )
        logs_dir = tmp_path / "Logs"
        fm, _ = _read_audit_file(logs_dir, filename)

        assert fm["agent"] == "triage_inbox"
        assert fm["action"] == "classified item"
        assert fm["risk_tier"] == "LOW"
        assert fm["status"] == "success"

    def test_idempotent_when_logs_dir_already_exists(self, tmp_path):
        """log_action must succeed silently when Logs/ already exists."""
        logs_dir = tmp_path / "Logs"
        logs_dir.mkdir()  # pre-create

        # Should not raise even though directory already exists
        filename = log_action(
            vault_root=str(tmp_path),
            agent="triage_inbox",
            action="classified item",
            risk_tier="LOW",
            status="success",
        )
        assert (logs_dir / filename).exists()


# ---------------------------------------------------------------------------
# Test – File body contains human-readable summary
# ---------------------------------------------------------------------------

class TestFileBody:
    def test_file_has_content_after_frontmatter(self, tmp_path):
        """Audit file must contain content beyond the closing '---'."""
        logs_dir = tmp_path / "Logs"
        logs_dir.mkdir()

        filename = log_action(
            vault_root=str(tmp_path),
            agent="triage_inbox",
            action="classified item",
            risk_tier="LOW",
            status="success",
            details="Classified as financial",
        )
        _, full_text = _read_audit_file(logs_dir, filename)

        lines = full_text.splitlines()
        # Find closing '---'
        closing = lines.index("---", 1)
        body_lines = [l for l in lines[closing + 1:] if l.strip()]
        assert body_lines, "File should contain a human-readable body after frontmatter"

    def test_file_body_mentions_agent(self, tmp_path):
        """Body text should reference the agent name for human readability."""
        logs_dir = tmp_path / "Logs"
        logs_dir.mkdir()

        filename = log_action(
            vault_root=str(tmp_path),
            agent="finance_agent",
            action="generated invoice",
            risk_tier="HIGH",
            status="success",
            details="Invoice INV-042 created",
        )
        _, full_text = _read_audit_file(logs_dir, filename)
        assert "finance_agent" in full_text, (
            "Body should mention the agent name"
        )
