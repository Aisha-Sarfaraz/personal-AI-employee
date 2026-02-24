"""
Tests for src.core.opt_out — is_opted_out(vault_root, email_address) -> bool

TDD red phase: all tests MUST FAIL before implementation.

Covers:
  1. test_opted_out_email_blocked
  2. test_not_opted_out_allowed
  3. test_case_insensitive
  4. test_missing_file_returns_false
  5. test_ignores_headings_and_blanks
  6. test_multiple_entries
"""

from __future__ import annotations

from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_vault(tmp_path: Path, opt_out_content: str | None = None) -> str:
    vault = tmp_path / "vault"
    vault.mkdir(parents=True)
    if opt_out_content is not None:
        (vault / "Opt_Out_List.md").write_text(opt_out_content, encoding="utf-8")
    return str(vault)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestOptOut:

    def test_opted_out_email_blocked(self, tmp_path: Path) -> None:
        """Email in opt-out list must return True (opted out)."""
        from src.core.opt_out import is_opted_out

        vault = _make_vault(tmp_path, "# Opt-Out\n- blocked@example.com\n")
        assert is_opted_out(vault, "blocked@example.com") is True

    def test_not_opted_out_allowed(self, tmp_path: Path) -> None:
        """Email NOT in opt-out list must return False."""
        from src.core.opt_out import is_opted_out

        vault = _make_vault(tmp_path, "# Opt-Out\n- blocked@example.com\n")
        assert is_opted_out(vault, "allowed@example.com") is False

    def test_case_insensitive(self, tmp_path: Path) -> None:
        """Matching must be case-insensitive."""
        from src.core.opt_out import is_opted_out

        vault = _make_vault(tmp_path, "- User@EXAMPLE.COM\n")
        assert is_opted_out(vault, "user@example.com") is True
        assert is_opted_out(vault, "USER@EXAMPLE.COM") is True

    def test_missing_file_returns_false(self, tmp_path: Path) -> None:
        """Missing Opt_Out_List.md must return False (not opted out)."""
        from src.core.opt_out import is_opted_out

        vault = _make_vault(tmp_path, opt_out_content=None)  # no file created
        assert is_opted_out(vault, "anyone@example.com") is False

    def test_ignores_headings_and_blanks(self, tmp_path: Path) -> None:
        """Headings (#), blank lines, and comments must not cause false positives."""
        from src.core.opt_out import is_opted_out

        content = (
            "# Email Opt-Out List\n"
            "\n"
            "## Section\n"
            "<!-- comment -->\n"
            "- real@blocked.com\n"
        )
        vault = _make_vault(tmp_path, content)
        assert is_opted_out(vault, "real@blocked.com") is True
        assert is_opted_out(vault, "section") is False
        assert is_opted_out(vault, "email opt-out list") is False

    def test_multiple_entries(self, tmp_path: Path) -> None:
        """All entries in list must be checked."""
        from src.core.opt_out import is_opted_out

        content = "- alice@example.com\n- bob@example.com\n- charlie@example.com\n"
        vault = _make_vault(tmp_path, content)
        assert is_opted_out(vault, "alice@example.com") is True
        assert is_opted_out(vault, "bob@example.com") is True
        assert is_opted_out(vault, "charlie@example.com") is True
        assert is_opted_out(vault, "dave@example.com") is False
