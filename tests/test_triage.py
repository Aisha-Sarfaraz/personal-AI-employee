"""
Comprehensive tests for src.skills.triage_inbox.run()

Module under test: src/skills/triage_inbox.py

run(vault_root: str) -> dict
  - Scans /Inbox, classifies each .md file by type and priority using keyword
    analysis, updates frontmatter, moves to /Needs_Action, logs via audit_logger.
  - Returns {"processed": int, "errors": list[str], "skipped": int}

Keyword Classification Rules
-----------------------------
Type (by keyword scoring):
  financial     : invoice, payment, $, expense, budget, refund
  communication : email, message, reply, letter, correspondence
  task          : todo, assign, deadline, task, action item
  document      : report, summary, pdf, analysis
  general       : default if no keywords match
  unknown       : for items whose frontmatter already has type:unknown

Priority (by keyword scoring):
  CRITICAL : urgent, emergency, critical, immediately
  HIGH     : important, deadline, asap, priority
  MEDIUM   : default (no priority keywords matched)
  LOW      : info, fyi, optional, informational

Test coverage (14 tests):
  1.  financial keywords → type "financial"
  2.  communication keywords → type "communication"
  3.  task keywords → type "task"
  4.  document keywords → type "document"
  5.  no keywords → type "general"
  6.  type:unknown in frontmatter → type stays "unknown"
  7.  CRITICAL keywords → priority "CRITICAL"
  8.  HIGH keywords → priority "HIGH"
  9.  no priority keywords → priority "MEDIUM"
  10. LOW keywords → priority "LOW"
  11. Item moved from Inbox/ to Needs_Action/
  12. Frontmatter status updated to "triaged"
  13. Empty Inbox → {processed: 0, errors: [], skipped: 0}
  14. Multiple items processed in one run
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
import yaml

from src.core.vault import read_frontmatter_file, write_frontmatter_file
from src.skills import triage_inbox


# ---------------------------------------------------------------------------
# Vault factory helpers
# ---------------------------------------------------------------------------

def make_vault(tmp_path: Path) -> str:
    """
    Create a minimal vault directory structure under tmp_path.

    Layout:
        <tmp_path>/vault/
            Inbox/
            Needs_Action/
            Logs/

    Returns the vault root as an absolute string path.
    """
    vault_root = tmp_path / "vault"
    (vault_root / "Inbox").mkdir(parents=True)
    (vault_root / "Needs_Action").mkdir(parents=True)
    (vault_root / "Logs").mkdir(parents=True)
    return str(vault_root)


def seed_inbox_item(
    vault_root: str,
    filename: str,
    *,
    item_type: str = "general",
    priority: str = "MEDIUM",
    status: str = "new",
    body: str = "",
    extra_meta: dict[str, Any] | None = None,
) -> None:
    """
    Write a .md file into Inbox/ with standard frontmatter using
    src.core.vault.write_frontmatter_file, exactly as real watchers do.

    Args:
        vault_root:  Absolute path to the vault root.
        filename:    Filename (with .md extension) inside Inbox/.
        item_type:   The 'type' frontmatter field.
        priority:    The 'priority' frontmatter field.
        status:      The 'status' frontmatter field.
        body:        Markdown body text (used for keyword detection).
        extra_meta:  Any additional frontmatter fields to merge in.
    """
    metadata: dict[str, Any] = {
        "type": item_type,
        "source": "test_seeder",
        "priority": priority,
        "status": status,
    }
    if extra_meta:
        metadata.update(extra_meta)
    write_frontmatter_file(vault_root, f"Inbox/{filename}", metadata, body)


def read_triaged_item(vault_root: str, filename: str) -> tuple[dict[str, Any], str]:
    """
    Read a file from Needs_Action/ and return (frontmatter_dict, body).
    Thin wrapper around vault.read_frontmatter_file for readability.
    """
    return read_frontmatter_file(vault_root, f"Needs_Action/{filename}")


def _patch_audit(vault_root: str):
    """
    Return a context-manager that patches audit_logger.log_action inside the
    triage_inbox module so tests do not need a functioning Logs/ directory for
    every assertion — the Logs/ dir is still created by make_vault() but the
    mock keeps tests deterministic and fast.
    """
    return patch("src.skills.triage_inbox.log_action")


# ---------------------------------------------------------------------------
# Test 1: financial keywords → type "financial"
# ---------------------------------------------------------------------------

class TestTypeClassificationFinancial:
    """run() with financial keywords in the body classifies type as 'financial'."""

    def test_invoice_keyword_classifies_as_financial(self, tmp_path):
        vault_root = make_vault(tmp_path)
        seed_inbox_item(
            vault_root,
            "invoice_item.md",
            body="Please review the attached invoice for services rendered.",
        )

        with _patch_audit(vault_root):
            result = triage_inbox.run(vault_root)

        assert result["processed"] >= 1
        meta, _ = read_triaged_item(vault_root, "invoice_item.md")
        assert meta["type"] == "financial"

    def test_payment_keyword_classifies_as_financial(self, tmp_path):
        vault_root = make_vault(tmp_path)
        seed_inbox_item(
            vault_root,
            "payment_item.md",
            body="A payment of $500 has been received.",
        )

        with _patch_audit(vault_root):
            result = triage_inbox.run(vault_root)

        assert result["processed"] >= 1
        meta, _ = read_triaged_item(vault_root, "payment_item.md")
        assert meta["type"] == "financial"

    def test_dollar_sign_keyword_classifies_as_financial(self, tmp_path):
        vault_root = make_vault(tmp_path)
        seed_inbox_item(
            vault_root,
            "dollar_item.md",
            body="The total budget is $1,200 for this quarter.",
        )

        with _patch_audit(vault_root):
            triage_inbox.run(vault_root)

        meta, _ = read_triaged_item(vault_root, "dollar_item.md")
        assert meta["type"] == "financial"

    def test_expense_keyword_classifies_as_financial(self, tmp_path):
        vault_root = make_vault(tmp_path)
        seed_inbox_item(
            vault_root,
            "expense_item.md",
            body="Submit your expense report by end of month.",
        )

        with _patch_audit(vault_root):
            triage_inbox.run(vault_root)

        meta, _ = read_triaged_item(vault_root, "expense_item.md")
        assert meta["type"] == "financial"

    def test_refund_keyword_classifies_as_financial(self, tmp_path):
        vault_root = make_vault(tmp_path)
        seed_inbox_item(
            vault_root,
            "refund_item.md",
            body="Customer requested a refund for order #4567.",
        )

        with _patch_audit(vault_root):
            triage_inbox.run(vault_root)

        meta, _ = read_triaged_item(vault_root, "refund_item.md")
        assert meta["type"] == "financial"


# ---------------------------------------------------------------------------
# Test 2: communication keywords → type "communication"
# ---------------------------------------------------------------------------

class TestTypeClassificationCommunication:
    """run() with communication keywords classifies type as 'communication'."""

    def test_email_keyword_classifies_as_communication(self, tmp_path):
        vault_root = make_vault(tmp_path)
        seed_inbox_item(
            vault_root,
            "email_item.md",
            body="An email from the client arrived this morning.",
        )

        with _patch_audit(vault_root):
            triage_inbox.run(vault_root)

        meta, _ = read_triaged_item(vault_root, "email_item.md")
        assert meta["type"] == "communication"

    def test_message_keyword_classifies_as_communication(self, tmp_path):
        vault_root = make_vault(tmp_path)
        seed_inbox_item(
            vault_root,
            "message_item.md",
            body="New message received from the support team.",
        )

        with _patch_audit(vault_root):
            triage_inbox.run(vault_root)

        meta, _ = read_triaged_item(vault_root, "message_item.md")
        assert meta["type"] == "communication"

    def test_reply_keyword_classifies_as_communication(self, tmp_path):
        vault_root = make_vault(tmp_path)
        seed_inbox_item(
            vault_root,
            "reply_item.md",
            body="Please draft a reply to the partner inquiry.",
        )

        with _patch_audit(vault_root):
            triage_inbox.run(vault_root)

        meta, _ = read_triaged_item(vault_root, "reply_item.md")
        assert meta["type"] == "communication"

    def test_letter_keyword_classifies_as_communication(self, tmp_path):
        vault_root = make_vault(tmp_path)
        seed_inbox_item(
            vault_root,
            "letter_item.md",
            body="Received a formal letter from the regulatory body.",
        )

        with _patch_audit(vault_root):
            triage_inbox.run(vault_root)

        meta, _ = read_triaged_item(vault_root, "letter_item.md")
        assert meta["type"] == "communication"

    def test_correspondence_keyword_classifies_as_communication(self, tmp_path):
        vault_root = make_vault(tmp_path)
        seed_inbox_item(
            vault_root,
            "correspondence_item.md",
            body="This correspondence should be archived after review.",
        )

        with _patch_audit(vault_root):
            triage_inbox.run(vault_root)

        meta, _ = read_triaged_item(vault_root, "correspondence_item.md")
        assert meta["type"] == "communication"


# ---------------------------------------------------------------------------
# Test 3: task keywords → type "task"
# ---------------------------------------------------------------------------

class TestTypeClassificationTask:
    """run() with task keywords classifies type as 'task'."""

    def test_todo_keyword_classifies_as_task(self, tmp_path):
        vault_root = make_vault(tmp_path)
        seed_inbox_item(
            vault_root,
            "todo_item.md",
            body="TODO: update the configuration file before release.",
        )

        with _patch_audit(vault_root):
            triage_inbox.run(vault_root)

        meta, _ = read_triaged_item(vault_root, "todo_item.md")
        assert meta["type"] == "task"

    def test_assign_keyword_classifies_as_task(self, tmp_path):
        vault_root = make_vault(tmp_path)
        seed_inbox_item(
            vault_root,
            "assign_item.md",
            body="Please assign this to the engineering team.",
        )

        with _patch_audit(vault_root):
            triage_inbox.run(vault_root)

        meta, _ = read_triaged_item(vault_root, "assign_item.md")
        assert meta["type"] == "task"

    def test_deadline_keyword_classifies_as_task(self, tmp_path):
        vault_root = make_vault(tmp_path)
        seed_inbox_item(
            vault_root,
            "deadline_item.md",
            body="The deadline for submissions is next Friday.",
        )

        with _patch_audit(vault_root):
            triage_inbox.run(vault_root)

        meta, _ = read_triaged_item(vault_root, "deadline_item.md")
        assert meta["type"] == "task"

    def test_task_keyword_classifies_as_task(self, tmp_path):
        vault_root = make_vault(tmp_path)
        seed_inbox_item(
            vault_root,
            "task_item.md",
            body="This task needs to be completed before the sprint ends.",
        )

        with _patch_audit(vault_root):
            triage_inbox.run(vault_root)

        meta, _ = read_triaged_item(vault_root, "task_item.md")
        assert meta["type"] == "task"

    def test_action_item_keyword_classifies_as_task(self, tmp_path):
        vault_root = make_vault(tmp_path)
        seed_inbox_item(
            vault_root,
            "action_item.md",
            body="Action item from yesterday's meeting: update the roadmap.",
        )

        with _patch_audit(vault_root):
            triage_inbox.run(vault_root)

        meta, _ = read_triaged_item(vault_root, "action_item.md")
        assert meta["type"] == "task"


# ---------------------------------------------------------------------------
# Test 4: document keywords → type "document"
# ---------------------------------------------------------------------------

class TestTypeClassificationDocument:
    """run() with document keywords classifies type as 'document'."""

    def test_report_keyword_classifies_as_document(self, tmp_path):
        vault_root = make_vault(tmp_path)
        seed_inbox_item(
            vault_root,
            "report_item.md",
            body="The quarterly report is ready for review.",
        )

        with _patch_audit(vault_root):
            triage_inbox.run(vault_root)

        meta, _ = read_triaged_item(vault_root, "report_item.md")
        assert meta["type"] == "document"

    def test_summary_keyword_classifies_as_document(self, tmp_path):
        vault_root = make_vault(tmp_path)
        seed_inbox_item(
            vault_root,
            "summary_item.md",
            body="Here is a summary of the key findings from the study.",
        )

        with _patch_audit(vault_root):
            triage_inbox.run(vault_root)

        meta, _ = read_triaged_item(vault_root, "summary_item.md")
        assert meta["type"] == "document"

    def test_pdf_keyword_classifies_as_document(self, tmp_path):
        vault_root = make_vault(tmp_path)
        seed_inbox_item(
            vault_root,
            "pdf_item.md",
            body="Attached is the pdf version of the contract.",
        )

        with _patch_audit(vault_root):
            triage_inbox.run(vault_root)

        meta, _ = read_triaged_item(vault_root, "pdf_item.md")
        assert meta["type"] == "document"

    def test_analysis_keyword_classifies_as_document(self, tmp_path):
        vault_root = make_vault(tmp_path)
        seed_inbox_item(
            vault_root,
            "analysis_item.md",
            body="The analysis of market data shows an upward trend.",
        )

        with _patch_audit(vault_root):
            triage_inbox.run(vault_root)

        meta, _ = read_triaged_item(vault_root, "analysis_item.md")
        assert meta["type"] == "document"


# ---------------------------------------------------------------------------
# Test 5: no keywords → type "general"
# ---------------------------------------------------------------------------

class TestTypeClassificationGeneral:
    """run() with no matching keywords classifies type as 'general'."""

    def test_empty_body_classifies_as_general(self, tmp_path):
        vault_root = make_vault(tmp_path)
        seed_inbox_item(
            vault_root,
            "empty_body.md",
            body="",
        )

        with _patch_audit(vault_root):
            result = triage_inbox.run(vault_root)

        assert result["processed"] >= 1
        meta, _ = read_triaged_item(vault_root, "empty_body.md")
        assert meta["type"] == "general"

    def test_neutral_body_no_keywords_classifies_as_general(self, tmp_path):
        vault_root = make_vault(tmp_path)
        seed_inbox_item(
            vault_root,
            "neutral_item.md",
            body="Nothing specific here. Just some random content with no signals.",
        )

        with _patch_audit(vault_root):
            triage_inbox.run(vault_root)

        meta, _ = read_triaged_item(vault_root, "neutral_item.md")
        assert meta["type"] == "general"


# ---------------------------------------------------------------------------
# Test 6: type:unknown in frontmatter → type stays "unknown"
# ---------------------------------------------------------------------------

class TestTypeUnknownPreserved:
    """Items with type:unknown in frontmatter keep type as 'unknown' after triage."""

    def test_type_unknown_frontmatter_is_preserved(self, tmp_path):
        vault_root = make_vault(tmp_path)
        # Seed with type:unknown — simulates binary/malformed items flagged by the watcher
        seed_inbox_item(
            vault_root,
            "unknown_item.md",
            item_type="unknown",
            body="Some body text with invoice and email keywords that should be ignored.",
        )

        with _patch_audit(vault_root):
            result = triage_inbox.run(vault_root)

        assert result["skipped"] >= 1 or result["processed"] >= 1
        # Whether skipped or processed, type must remain unknown
        # Try Needs_Action first; if skipped it may still be in Inbox
        needs_action_path = os.path.join(vault_root, "Needs_Action", "unknown_item.md")
        inbox_path = os.path.join(vault_root, "Inbox", "unknown_item.md")

        if os.path.exists(needs_action_path):
            meta, _ = read_triaged_item(vault_root, "unknown_item.md")
        else:
            assert os.path.exists(inbox_path), (
                "unknown item must remain in Inbox/ when skipped"
            )
            meta, _ = read_frontmatter_file(vault_root, "Inbox/unknown_item.md")

        assert meta["type"] == "unknown", (
            f"type:unknown must be preserved, got: {meta['type']!r}"
        )

    def test_type_unknown_counted_as_skipped(self, tmp_path):
        """Items with type:unknown must increment the skipped counter."""
        vault_root = make_vault(tmp_path)
        seed_inbox_item(
            vault_root,
            "skip_unknown.md",
            item_type="unknown",
            body="binary content placeholder",
        )

        with _patch_audit(vault_root):
            result = triage_inbox.run(vault_root)

        assert result["skipped"] >= 1, (
            f"Expected skipped >= 1 for type:unknown item, got: {result}"
        )


# ---------------------------------------------------------------------------
# Test 7: CRITICAL keywords → priority "CRITICAL"
# ---------------------------------------------------------------------------

class TestPriorityCritical:
    """Keywords urgent, emergency, critical, immediately → priority CRITICAL."""

    def test_urgent_keyword_yields_critical_priority(self, tmp_path):
        vault_root = make_vault(tmp_path)
        seed_inbox_item(
            vault_root,
            "urgent_item.md",
            body="This is urgent and needs immediate attention from the team.",
        )

        with _patch_audit(vault_root):
            triage_inbox.run(vault_root)

        meta, _ = read_triaged_item(vault_root, "urgent_item.md")
        assert meta["priority"] == "CRITICAL"

    def test_emergency_keyword_yields_critical_priority(self, tmp_path):
        vault_root = make_vault(tmp_path)
        seed_inbox_item(
            vault_root,
            "emergency_item.md",
            body="Emergency: server is down and clients are impacted.",
        )

        with _patch_audit(vault_root):
            triage_inbox.run(vault_root)

        meta, _ = read_triaged_item(vault_root, "emergency_item.md")
        assert meta["priority"] == "CRITICAL"

    def test_critical_keyword_yields_critical_priority(self, tmp_path):
        vault_root = make_vault(tmp_path)
        seed_inbox_item(
            vault_root,
            "critical_item.md",
            body="This is a critical security vulnerability that must be patched.",
        )

        with _patch_audit(vault_root):
            triage_inbox.run(vault_root)

        meta, _ = read_triaged_item(vault_root, "critical_item.md")
        assert meta["priority"] == "CRITICAL"

    def test_immediately_keyword_yields_critical_priority(self, tmp_path):
        vault_root = make_vault(tmp_path)
        seed_inbox_item(
            vault_root,
            "immediately_item.md",
            body="Please respond immediately to avoid contract breach.",
        )

        with _patch_audit(vault_root):
            triage_inbox.run(vault_root)

        meta, _ = read_triaged_item(vault_root, "immediately_item.md")
        assert meta["priority"] == "CRITICAL"


# ---------------------------------------------------------------------------
# Test 8: HIGH keywords → priority "HIGH"
# ---------------------------------------------------------------------------

class TestPriorityHigh:
    """Keywords important, deadline, asap, priority → priority HIGH."""

    def test_important_keyword_yields_high_priority(self, tmp_path):
        vault_root = make_vault(tmp_path)
        seed_inbox_item(
            vault_root,
            "important_item.md",
            body="This is important and should be reviewed by Monday.",
        )

        with _patch_audit(vault_root):
            triage_inbox.run(vault_root)

        meta, _ = read_triaged_item(vault_root, "important_item.md")
        assert meta["priority"] == "HIGH"

    def test_asap_keyword_yields_high_priority(self, tmp_path):
        vault_root = make_vault(tmp_path)
        seed_inbox_item(
            vault_root,
            "asap_item.md",
            body="Please complete this ASAP before the client follow-up.",
        )

        with _patch_audit(vault_root):
            triage_inbox.run(vault_root)

        meta, _ = read_triaged_item(vault_root, "asap_item.md")
        assert meta["priority"] == "HIGH"

    def test_priority_keyword_yields_high_priority(self, tmp_path):
        vault_root = make_vault(tmp_path)
        seed_inbox_item(
            vault_root,
            "priority_item.md",
            body="This is a priority request from the executive team.",
        )

        with _patch_audit(vault_root):
            triage_inbox.run(vault_root)

        meta, _ = read_triaged_item(vault_root, "priority_item.md")
        assert meta["priority"] == "HIGH"

    def test_deadline_keyword_yields_high_priority(self, tmp_path):
        """deadline drives both type:task AND priority:HIGH — verify priority only."""
        vault_root = make_vault(tmp_path)
        seed_inbox_item(
            vault_root,
            "deadline_priority_item.md",
            body="The project deadline is in 48 hours; please act accordingly.",
        )

        with _patch_audit(vault_root):
            triage_inbox.run(vault_root)

        meta, _ = read_triaged_item(vault_root, "deadline_priority_item.md")
        assert meta["priority"] == "HIGH"


# ---------------------------------------------------------------------------
# Test 9: no priority keywords → priority "MEDIUM" (default)
# ---------------------------------------------------------------------------

class TestPriorityMediumDefault:
    """Items with no priority keywords get the default priority of MEDIUM."""

    def test_no_priority_keywords_yields_medium(self, tmp_path):
        vault_root = make_vault(tmp_path)
        seed_inbox_item(
            vault_root,
            "medium_item.md",
            body="Some routine content with no urgency signals at all.",
        )

        with _patch_audit(vault_root):
            triage_inbox.run(vault_root)

        meta, _ = read_triaged_item(vault_root, "medium_item.md")
        assert meta["priority"] == "MEDIUM"

    def test_empty_body_default_priority_is_medium(self, tmp_path):
        vault_root = make_vault(tmp_path)
        seed_inbox_item(vault_root, "empty_priority.md", body="")

        with _patch_audit(vault_root):
            triage_inbox.run(vault_root)

        meta, _ = read_triaged_item(vault_root, "empty_priority.md")
        assert meta["priority"] == "MEDIUM"


# ---------------------------------------------------------------------------
# Test 10: LOW keywords → priority "LOW"
# ---------------------------------------------------------------------------

class TestPriorityLow:
    """Keywords info, fyi, optional, informational → priority LOW."""

    def test_fyi_keyword_yields_low_priority(self, tmp_path):
        vault_root = make_vault(tmp_path)
        seed_inbox_item(
            vault_root,
            "fyi_item.md",
            body="FYI: the office will be closed on the public holiday.",
        )

        with _patch_audit(vault_root):
            triage_inbox.run(vault_root)

        meta, _ = read_triaged_item(vault_root, "fyi_item.md")
        assert meta["priority"] == "LOW"

    def test_optional_keyword_yields_low_priority(self, tmp_path):
        vault_root = make_vault(tmp_path)
        seed_inbox_item(
            vault_root,
            "optional_item.md",
            body="Attending the workshop is optional; join if you can.",
        )

        with _patch_audit(vault_root):
            triage_inbox.run(vault_root)

        meta, _ = read_triaged_item(vault_root, "optional_item.md")
        assert meta["priority"] == "LOW"

    def test_info_keyword_yields_low_priority(self, tmp_path):
        vault_root = make_vault(tmp_path)
        seed_inbox_item(
            vault_root,
            "info_item.md",
            body="For your info, the new policy takes effect next quarter.",
        )

        with _patch_audit(vault_root):
            triage_inbox.run(vault_root)

        meta, _ = read_triaged_item(vault_root, "info_item.md")
        assert meta["priority"] == "LOW"

    def test_informational_keyword_yields_low_priority(self, tmp_path):
        vault_root = make_vault(tmp_path)
        seed_inbox_item(
            vault_root,
            "informational_item.md",
            body="This notice is informational only and requires no action.",
        )

        with _patch_audit(vault_root):
            triage_inbox.run(vault_root)

        meta, _ = read_triaged_item(vault_root, "informational_item.md")
        assert meta["priority"] == "LOW"


# ---------------------------------------------------------------------------
# Test 11: Item moved from Inbox/ to Needs_Action/
# ---------------------------------------------------------------------------

class TestFileMoved:
    """After triage, the .md file must be absent from Inbox/ and present in Needs_Action/."""

    def test_processed_item_is_removed_from_inbox(self, tmp_path):
        vault_root = make_vault(tmp_path)
        seed_inbox_item(
            vault_root,
            "move_me.md",
            body="Invoice for services in March.",
        )

        inbox_full = os.path.join(vault_root, "Inbox", "move_me.md")
        assert os.path.exists(inbox_full), "Pre-condition: file must exist in Inbox/"

        with _patch_audit(vault_root):
            triage_inbox.run(vault_root)

        assert not os.path.exists(inbox_full), (
            "Processed file must be removed from Inbox/"
        )

    def test_processed_item_is_present_in_needs_action(self, tmp_path):
        vault_root = make_vault(tmp_path)
        seed_inbox_item(
            vault_root,
            "arrive_here.md",
            body="Invoice for services in March.",
        )

        with _patch_audit(vault_root):
            triage_inbox.run(vault_root)

        needs_action_full = os.path.join(vault_root, "Needs_Action", "arrive_here.md")
        assert os.path.exists(needs_action_full), (
            "Processed file must exist in Needs_Action/"
        )

    def test_moved_file_is_a_regular_file(self, tmp_path):
        vault_root = make_vault(tmp_path)
        seed_inbox_item(vault_root, "is_file.md", body="payment received.")

        with _patch_audit(vault_root):
            triage_inbox.run(vault_root)

        needs_action_full = os.path.join(vault_root, "Needs_Action", "is_file.md")
        assert os.path.isfile(needs_action_full), (
            "Destination must be a regular file, not a directory or symlink"
        )

    def test_file_content_is_not_corrupted_after_move(self, tmp_path):
        """Frontmatter in the moved file must be parseable YAML."""
        vault_root = make_vault(tmp_path)
        seed_inbox_item(
            vault_root,
            "intact.md",
            body="Summary of Q1 financial analysis report.",
        )

        with _patch_audit(vault_root):
            triage_inbox.run(vault_root)

        needs_action_full = os.path.join(vault_root, "Needs_Action", "intact.md")
        with open(needs_action_full, "r", encoding="utf-8") as fh:
            content = fh.read()

        assert content.startswith("---"), "Moved file must still have YAML frontmatter"
        parts = content.split("---", 2)
        assert len(parts) >= 3, "Moved file must have opening and closing --- delimiters"
        parsed = yaml.safe_load(parts[1].strip())
        assert isinstance(parsed, dict), "Frontmatter block must parse to a dict"


# ---------------------------------------------------------------------------
# Test 12: Frontmatter status updated to "triaged"
# ---------------------------------------------------------------------------

class TestStatusUpdatedToTriaged:
    """After run(), the frontmatter 'status' field of processed items must be 'triaged'."""

    def test_status_set_to_triaged_for_financial_item(self, tmp_path):
        vault_root = make_vault(tmp_path)
        seed_inbox_item(
            vault_root,
            "triaged_financial.md",
            status="new",
            body="invoice attached for payment.",
        )

        with _patch_audit(vault_root):
            triage_inbox.run(vault_root)

        meta, _ = read_triaged_item(vault_root, "triaged_financial.md")
        assert meta["status"] == "triaged", (
            f"Expected status='triaged', got: {meta['status']!r}"
        )

    def test_status_set_to_triaged_for_task_item(self, tmp_path):
        vault_root = make_vault(tmp_path)
        seed_inbox_item(
            vault_root,
            "triaged_task.md",
            status="new",
            body="TODO: complete the onboarding documentation.",
        )

        with _patch_audit(vault_root):
            triage_inbox.run(vault_root)

        meta, _ = read_triaged_item(vault_root, "triaged_task.md")
        assert meta["status"] == "triaged"

    def test_status_set_to_triaged_for_general_item(self, tmp_path):
        vault_root = make_vault(tmp_path)
        seed_inbox_item(
            vault_root,
            "triaged_general.md",
            status="new",
            body="Just a generic note with no keywords.",
        )

        with _patch_audit(vault_root):
            triage_inbox.run(vault_root)

        meta, _ = read_triaged_item(vault_root, "triaged_general.md")
        assert meta["status"] == "triaged"

    def test_original_status_new_is_overwritten(self, tmp_path):
        """The pre-existing status value 'new' must be replaced, not appended."""
        vault_root = make_vault(tmp_path)
        seed_inbox_item(
            vault_root,
            "overwrite_status.md",
            status="new",
            body="email from client.",
        )

        with _patch_audit(vault_root):
            triage_inbox.run(vault_root)

        meta, _ = read_triaged_item(vault_root, "overwrite_status.md")
        assert meta["status"] == "triaged"
        assert meta["status"] != "new"


# ---------------------------------------------------------------------------
# Test 13: Empty Inbox → {processed: 0, errors: [], skipped: 0}
# ---------------------------------------------------------------------------

class TestEmptyInbox:
    """run() on an empty Inbox returns zero counts and no errors."""

    def test_empty_inbox_returns_zero_processed(self, tmp_path):
        vault_root = make_vault(tmp_path)
        # Inbox/ exists but has no .md files

        with _patch_audit(vault_root):
            result = triage_inbox.run(vault_root)

        assert result["processed"] == 0, (
            f"Expected processed=0 for empty Inbox, got: {result['processed']}"
        )

    def test_empty_inbox_returns_empty_errors_list(self, tmp_path):
        vault_root = make_vault(tmp_path)

        with _patch_audit(vault_root):
            result = triage_inbox.run(vault_root)

        assert result["errors"] == [], (
            f"Expected errors=[] for empty Inbox, got: {result['errors']}"
        )

    def test_empty_inbox_returns_zero_skipped(self, tmp_path):
        vault_root = make_vault(tmp_path)

        with _patch_audit(vault_root):
            result = triage_inbox.run(vault_root)

        assert result["skipped"] == 0, (
            f"Expected skipped=0 for empty Inbox, got: {result['skipped']}"
        )

    def test_empty_inbox_exact_return_shape(self, tmp_path):
        """Return value must be exactly {processed: 0, errors: [], skipped: 0}."""
        vault_root = make_vault(tmp_path)

        with _patch_audit(vault_root):
            result = triage_inbox.run(vault_root)

        assert result == {"processed": 0, "errors": [], "skipped": 0}, (
            f"Expected zero-state dict, got: {result}"
        )

    def test_empty_inbox_does_not_create_files_in_needs_action(self, tmp_path):
        """No files must appear in Needs_Action/ when Inbox/ is empty."""
        vault_root = make_vault(tmp_path)

        with _patch_audit(vault_root):
            triage_inbox.run(vault_root)

        needs_action = os.path.join(vault_root, "Needs_Action")
        files = [f for f in os.listdir(needs_action) if f.endswith(".md")]
        assert files == [], (
            f"Needs_Action/ should be empty after empty-Inbox run, found: {files}"
        )

    def test_inbox_dir_missing_does_not_crash(self, tmp_path):
        """run() must not raise when Inbox/ directory does not exist at all."""
        vault_root = str(tmp_path / "vault_no_inbox")
        os.makedirs(os.path.join(vault_root, "Needs_Action"), exist_ok=True)
        os.makedirs(os.path.join(vault_root, "Logs"), exist_ok=True)

        with _patch_audit(vault_root):
            result = triage_inbox.run(vault_root)

        assert result["processed"] == 0
        assert result["errors"] == []
        assert result["skipped"] == 0


# ---------------------------------------------------------------------------
# Test 14: Multiple items processed in one run
# ---------------------------------------------------------------------------

class TestMultipleItemsProcessed:
    """run() must handle multiple items in Inbox/ in a single invocation."""

    def test_three_items_all_processed(self, tmp_path):
        vault_root = make_vault(tmp_path)
        seed_inbox_item(vault_root, "item_a.md", body="invoice for March services.")
        seed_inbox_item(vault_root, "item_b.md", body="email from the finance team.")
        seed_inbox_item(vault_root, "item_c.md", body="TODO: update the project plan.")

        with _patch_audit(vault_root):
            result = triage_inbox.run(vault_root)

        assert result["processed"] == 3, (
            f"Expected 3 processed items, got: {result['processed']}"
        )
        assert result["errors"] == []

    def test_three_items_all_moved_to_needs_action(self, tmp_path):
        vault_root = make_vault(tmp_path)
        filenames = ["multi_a.md", "multi_b.md", "multi_c.md"]
        bodies = [
            "payment due this week.",
            "summary of the quarterly review.",
            "please reply to the client message.",
        ]
        for name, body in zip(filenames, bodies):
            seed_inbox_item(vault_root, name, body=body)

        with _patch_audit(vault_root):
            triage_inbox.run(vault_root)

        for name in filenames:
            assert os.path.exists(os.path.join(vault_root, "Needs_Action", name)), (
                f"{name} should be in Needs_Action/"
            )
            assert not os.path.exists(os.path.join(vault_root, "Inbox", name)), (
                f"{name} should be removed from Inbox/"
            )

    def test_inbox_empty_after_full_run(self, tmp_path):
        """After processing all items, Inbox/ should contain no .md files."""
        vault_root = make_vault(tmp_path)
        for i in range(4):
            seed_inbox_item(
                vault_root,
                f"batch_{i}.md",
                body=f"email from client {i} about invoice {i}.",
            )

        with _patch_audit(vault_root):
            triage_inbox.run(vault_root)

        remaining = [
            f for f in os.listdir(os.path.join(vault_root, "Inbox"))
            if f.endswith(".md")
        ]
        assert remaining == [], (
            f"Inbox/ should be empty after full run, found: {remaining}"
        )

    def test_mixed_types_each_classified_correctly(self, tmp_path):
        """Multiple items with different keyword types each get the correct classification."""
        vault_root = make_vault(tmp_path)
        cases: list[tuple[str, str, str]] = [
            ("fin.md",   "invoice received for Q1.",           "financial"),
            ("comm.md",  "email from the partner team.",        "communication"),
            ("task.md",  "TODO: finish the integration tests.", "task"),
            ("doc.md",   "here is the analysis report.",        "document"),
            ("gen.md",   "just a note with no signals.",        "general"),
        ]
        for name, body, _ in cases:
            seed_inbox_item(vault_root, name, body=body)

        with _patch_audit(vault_root):
            result = triage_inbox.run(vault_root)

        assert result["processed"] == 5
        for name, _, expected_type in cases:
            meta, _ = read_triaged_item(vault_root, name)
            assert meta["type"] == expected_type, (
                f"{name}: expected type={expected_type!r}, got={meta['type']!r}"
            )

    def test_mixed_priorities_each_classified_correctly(self, tmp_path):
        """Multiple items with different priority keywords each get the correct priority."""
        vault_root = make_vault(tmp_path)
        cases: list[tuple[str, str, str]] = [
            ("crit.md",   "this is urgent and needs attention now.", "CRITICAL"),
            ("high.md",   "important: please review asap.",          "HIGH"),
            ("medium.md", "routine update with no urgency.",         "MEDIUM"),
            ("low.md",    "FYI only, no action required.",           "LOW"),
        ]
        for name, body, _ in cases:
            seed_inbox_item(vault_root, name, body=body)

        with _patch_audit(vault_root):
            result = triage_inbox.run(vault_root)

        assert result["processed"] == 4
        for name, _, expected_prio in cases:
            meta, _ = read_triaged_item(vault_root, name)
            assert meta["priority"] == expected_prio, (
                f"{name}: expected priority={expected_prio!r}, got={meta['priority']!r}"
            )

    def test_return_dict_has_correct_keys(self, tmp_path):
        """Return value must always contain exactly the keys: processed, errors, skipped."""
        vault_root = make_vault(tmp_path)
        seed_inbox_item(vault_root, "key_check.md", body="invoice from supplier.")

        with _patch_audit(vault_root):
            result = triage_inbox.run(vault_root)

        assert set(result.keys()) == {"processed", "errors", "skipped"}, (
            f"Unexpected keys in result: {set(result.keys())}"
        )

    def test_processed_is_int(self, tmp_path):
        vault_root = make_vault(tmp_path)
        seed_inbox_item(vault_root, "type_check.md", body="email from team.")

        with _patch_audit(vault_root):
            result = triage_inbox.run(vault_root)

        assert isinstance(result["processed"], int)

    def test_errors_is_list(self, tmp_path):
        vault_root = make_vault(tmp_path)
        seed_inbox_item(vault_root, "errors_check.md", body="task deadline tomorrow.")

        with _patch_audit(vault_root):
            result = triage_inbox.run(vault_root)

        assert isinstance(result["errors"], list)

    def test_skipped_is_int(self, tmp_path):
        vault_root = make_vault(tmp_path)
        seed_inbox_item(vault_root, "skipped_check.md", body="summary report attached.")

        with _patch_audit(vault_root):
            result = triage_inbox.run(vault_root)

        assert isinstance(result["skipped"], int)


# ---------------------------------------------------------------------------
# Supplemental: audit_logger is called during processing
# ---------------------------------------------------------------------------

class TestAuditLoggerInvocation:
    """run() must call audit_logger.log_action for each processed item."""

    def test_audit_logger_called_once_per_processed_item(self, tmp_path):
        vault_root = make_vault(tmp_path)
        seed_inbox_item(vault_root, "audit_a.md", body="invoice for services.")
        seed_inbox_item(vault_root, "audit_b.md", body="email from client.")

        with patch("src.skills.triage_inbox.log_action") as mock_log:
            triage_inbox.run(vault_root)

        # At minimum two calls — one per item (implementation may log more)
        assert mock_log.call_count >= 2, (
            f"Expected at least 2 audit log calls for 2 items, got: {mock_log.call_count}"
        )

    def test_audit_logger_called_with_vault_root(self, tmp_path):
        vault_root = make_vault(tmp_path)
        seed_inbox_item(vault_root, "audit_vault.md", body="urgent payment needed.")

        with patch("src.skills.triage_inbox.log_action") as mock_log:
            triage_inbox.run(vault_root)

        # vault_root must be the first positional argument on every call
        for call in mock_log.call_args_list:
            args, kwargs = call
            vault_arg = args[0] if args else kwargs.get("vault_root")
            assert vault_arg == vault_root, (
                f"log_action must receive vault_root={vault_root!r}, got: {vault_arg!r}"
            )
