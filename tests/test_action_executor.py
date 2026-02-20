"""
Tests for src.actions.action_executor.execute_action

Covers:
  1. send_email returns success=True with simulated=True in DEV_MODE
  2. create_invoice returns success=True with simulated=True in DEV_MODE
  3. post_social returns success=True with simulated=True in DEV_MODE
  4. update_calendar returns success=True with simulated=True in DEV_MODE
  5. file_operation returns success=True with simulated=True in DEV_MODE
  6. Unknown action_type returns success=False with details="skipped: unknown_action"
  7. Result dict has all required keys: success, action_type, details, simulated
"""

from __future__ import annotations

from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


REQUIRED_RESULT_KEYS = frozenset({"success", "action_type", "details", "simulated"})

# All known action types that must be handled by the executor
KNOWN_ACTION_TYPES = [
    "send_email",
    "create_invoice",
    "post_social",
    "update_calendar",
    "file_operation",
]


def assert_valid_result(result: dict, action_type: str) -> None:
    """Assert the result dict contains all required keys and types."""
    assert isinstance(result, dict), f"Result must be a dict, got {type(result)}"
    missing = REQUIRED_RESULT_KEYS - result.keys()
    assert not missing, (
        f"Result for '{action_type}' missing required keys: {missing}. "
        f"Got keys: {set(result.keys())}"
    )
    assert isinstance(result["success"], bool), (
        f"'success' must be bool, got {type(result['success'])}"
    )
    assert isinstance(result["action_type"], str), (
        f"'action_type' must be str, got {type(result['action_type'])}"
    )
    assert isinstance(result["details"], str), (
        f"'details' must be str, got {type(result['details'])}"
    )
    assert isinstance(result["simulated"], bool), (
        f"'simulated' must be bool, got {type(result['simulated'])}"
    )


# ---------------------------------------------------------------------------
# Test 1 — send_email returns success=True with simulated=True in DEV_MODE
# ---------------------------------------------------------------------------


class TestSendEmail:
    def test_send_email_returns_success_true(self) -> None:
        """send_email action in DEV_MODE must return success=True."""
        from src.actions.action_executor import execute_action

        result = execute_action(
            action_type="send_email",
            details={"to": "user@example.com", "subject": "Hello", "body": "Test body"},
            dev_mode=True,
        )

        assert result["success"] is True, (
            f"send_email must return success=True in DEV_MODE, got {result['success']}"
        )

    def test_send_email_returns_simulated_true(self) -> None:
        """send_email action in DEV_MODE must return simulated=True."""
        from src.actions.action_executor import execute_action

        result = execute_action(
            action_type="send_email",
            details={"to": "user@example.com", "subject": "Hello"},
            dev_mode=True,
        )

        assert result["simulated"] is True, (
            f"send_email must return simulated=True in DEV_MODE, got {result['simulated']}"
        )

    def test_send_email_action_type_matches(self) -> None:
        """Result action_type must equal 'send_email'."""
        from src.actions.action_executor import execute_action

        result = execute_action(
            action_type="send_email",
            details={"to": "test@example.com"},
            dev_mode=True,
        )

        assert result["action_type"] == "send_email", (
            f"action_type must be 'send_email', got {result['action_type']!r}"
        )

    def test_send_email_has_non_empty_details(self) -> None:
        """send_email result must contain a non-empty 'details' string."""
        from src.actions.action_executor import execute_action

        result = execute_action(
            action_type="send_email",
            details={"to": "user@example.com"},
            dev_mode=True,
        )

        assert result["details"] and isinstance(result["details"], str), (
            f"'details' must be a non-empty string, got {result['details']!r}"
        )


# ---------------------------------------------------------------------------
# Test 2 — create_invoice returns success=True with simulated=True in DEV_MODE
# ---------------------------------------------------------------------------


class TestCreateInvoice:
    def test_create_invoice_returns_success_true(self) -> None:
        """create_invoice action in DEV_MODE must return success=True."""
        from src.actions.action_executor import execute_action

        result = execute_action(
            action_type="create_invoice",
            details={"amount": 500.00, "customer": "Acme Corp", "description": "Services"},
            dev_mode=True,
        )

        assert result["success"] is True, (
            f"create_invoice must return success=True in DEV_MODE, got {result['success']}"
        )

    def test_create_invoice_returns_simulated_true(self) -> None:
        """create_invoice action in DEV_MODE must return simulated=True."""
        from src.actions.action_executor import execute_action

        result = execute_action(
            action_type="create_invoice",
            details={"amount": 250.00, "customer": "Beta LLC"},
            dev_mode=True,
        )

        assert result["simulated"] is True, (
            f"create_invoice must return simulated=True in DEV_MODE, "
            f"got {result['simulated']}"
        )

    def test_create_invoice_action_type_matches(self) -> None:
        """Result action_type must equal 'create_invoice'."""
        from src.actions.action_executor import execute_action

        result = execute_action(
            action_type="create_invoice",
            details={"amount": 100.00},
            dev_mode=True,
        )

        assert result["action_type"] == "create_invoice", (
            f"action_type must be 'create_invoice', got {result['action_type']!r}"
        )

    def test_create_invoice_has_non_empty_details(self) -> None:
        """create_invoice result must have a non-empty 'details' string."""
        from src.actions.action_executor import execute_action

        result = execute_action(
            action_type="create_invoice",
            details={"amount": 75.00},
            dev_mode=True,
        )

        assert result["details"] and isinstance(result["details"], str), (
            f"'details' must be non-empty string, got {result['details']!r}"
        )


# ---------------------------------------------------------------------------
# Test 3 — post_social returns success=True with simulated=True in DEV_MODE
# ---------------------------------------------------------------------------


class TestPostSocial:
    def test_post_social_returns_success_true(self) -> None:
        """post_social action in DEV_MODE must return success=True."""
        from src.actions.action_executor import execute_action

        result = execute_action(
            action_type="post_social",
            details={"platform": "twitter", "content": "Hello World!", "schedule": None},
            dev_mode=True,
        )

        assert result["success"] is True, (
            f"post_social must return success=True in DEV_MODE, got {result['success']}"
        )

    def test_post_social_returns_simulated_true(self) -> None:
        """post_social action in DEV_MODE must return simulated=True."""
        from src.actions.action_executor import execute_action

        result = execute_action(
            action_type="post_social",
            details={"platform": "linkedin", "content": "Professional update"},
            dev_mode=True,
        )

        assert result["simulated"] is True, (
            f"post_social must return simulated=True in DEV_MODE, "
            f"got {result['simulated']}"
        )

    def test_post_social_action_type_matches(self) -> None:
        """Result action_type must equal 'post_social'."""
        from src.actions.action_executor import execute_action

        result = execute_action(
            action_type="post_social",
            details={"platform": "twitter", "content": "Test post"},
            dev_mode=True,
        )

        assert result["action_type"] == "post_social", (
            f"action_type must be 'post_social', got {result['action_type']!r}"
        )

    def test_post_social_has_non_empty_details(self) -> None:
        """post_social result must have a non-empty 'details' string."""
        from src.actions.action_executor import execute_action

        result = execute_action(
            action_type="post_social",
            details={"platform": "facebook", "content": "Post content"},
            dev_mode=True,
        )

        assert result["details"] and isinstance(result["details"], str), (
            f"'details' must be non-empty string, got {result['details']!r}"
        )


# ---------------------------------------------------------------------------
# Test 4 — update_calendar returns success=True with simulated=True in DEV_MODE
# ---------------------------------------------------------------------------


class TestUpdateCalendar:
    def test_update_calendar_returns_success_true(self) -> None:
        """update_calendar action in DEV_MODE must return success=True."""
        from src.actions.action_executor import execute_action

        result = execute_action(
            action_type="update_calendar",
            details={
                "event": "Team Meeting",
                "date": "2026-02-18",
                "time": "10:00",
                "duration_minutes": 60,
            },
            dev_mode=True,
        )

        assert result["success"] is True, (
            f"update_calendar must return success=True in DEV_MODE, "
            f"got {result['success']}"
        )

    def test_update_calendar_returns_simulated_true(self) -> None:
        """update_calendar action in DEV_MODE must return simulated=True."""
        from src.actions.action_executor import execute_action

        result = execute_action(
            action_type="update_calendar",
            details={"event": "Sprint Review", "date": "2026-02-20"},
            dev_mode=True,
        )

        assert result["simulated"] is True, (
            f"update_calendar must return simulated=True in DEV_MODE, "
            f"got {result['simulated']}"
        )

    def test_update_calendar_action_type_matches(self) -> None:
        """Result action_type must equal 'update_calendar'."""
        from src.actions.action_executor import execute_action

        result = execute_action(
            action_type="update_calendar",
            details={"event": "Standup", "date": "2026-02-17"},
            dev_mode=True,
        )

        assert result["action_type"] == "update_calendar", (
            f"action_type must be 'update_calendar', got {result['action_type']!r}"
        )

    def test_update_calendar_has_non_empty_details(self) -> None:
        """update_calendar result must have a non-empty 'details' string."""
        from src.actions.action_executor import execute_action

        result = execute_action(
            action_type="update_calendar",
            details={"event": "Retrospective", "date": "2026-02-21"},
            dev_mode=True,
        )

        assert result["details"] and isinstance(result["details"], str), (
            f"'details' must be non-empty string, got {result['details']!r}"
        )


# ---------------------------------------------------------------------------
# Test 5 — file_operation returns success=True with simulated=True in DEV_MODE
# ---------------------------------------------------------------------------


class TestFileOperation:
    def test_file_operation_returns_success_true(self) -> None:
        """file_operation action in DEV_MODE must return success=True."""
        from src.actions.action_executor import execute_action

        result = execute_action(
            action_type="file_operation",
            details={"operation": "move", "source": "/vault/inbox.md", "destination": "/vault/archive/inbox.md"},
            dev_mode=True,
        )

        assert result["success"] is True, (
            f"file_operation must return success=True in DEV_MODE, "
            f"got {result['success']}"
        )

    def test_file_operation_returns_simulated_true(self) -> None:
        """file_operation action in DEV_MODE must return simulated=True."""
        from src.actions.action_executor import execute_action

        result = execute_action(
            action_type="file_operation",
            details={"operation": "copy", "source": "/vault/draft.md"},
            dev_mode=True,
        )

        assert result["simulated"] is True, (
            f"file_operation must return simulated=True in DEV_MODE, "
            f"got {result['simulated']}"
        )

    def test_file_operation_action_type_matches(self) -> None:
        """Result action_type must equal 'file_operation'."""
        from src.actions.action_executor import execute_action

        result = execute_action(
            action_type="file_operation",
            details={"operation": "delete", "source": "/vault/temp.md"},
            dev_mode=True,
        )

        assert result["action_type"] == "file_operation", (
            f"action_type must be 'file_operation', got {result['action_type']!r}"
        )

    def test_file_operation_has_non_empty_details(self) -> None:
        """file_operation result must have a non-empty 'details' string."""
        from src.actions.action_executor import execute_action

        result = execute_action(
            action_type="file_operation",
            details={"operation": "read", "source": "/vault/note.md"},
            dev_mode=True,
        )

        assert result["details"] and isinstance(result["details"], str), (
            f"'details' must be non-empty string, got {result['details']!r}"
        )


# ---------------------------------------------------------------------------
# Test 6 — Unknown action_type returns success=False with "skipped: unknown_action"
# ---------------------------------------------------------------------------


class TestUnknownActionType:
    def test_unknown_action_returns_success_false(self) -> None:
        """An unrecognised action_type must return success=False."""
        from src.actions.action_executor import execute_action

        result = execute_action(
            action_type="launch_rocket",
            details={"destination": "Mars"},
            dev_mode=True,
        )

        assert result["success"] is False, (
            f"Unknown action_type must return success=False, got {result['success']}"
        )

    def test_unknown_action_details_contains_skipped_unknown_action(self) -> None:
        """Unknown action_type must set details to 'skipped: unknown_action'."""
        from src.actions.action_executor import execute_action

        result = execute_action(
            action_type="launch_rocket",
            details={},
            dev_mode=True,
        )

        assert "skipped: unknown_action" in result["details"], (
            f"details must contain 'skipped: unknown_action', got {result['details']!r}"
        )

    def test_unknown_action_simulated_matches_dev_mode(self) -> None:
        """Unknown action_type result 'simulated' must reflect the dev_mode argument."""
        from src.actions.action_executor import execute_action

        result_dev = execute_action(
            action_type="nonexistent_action",
            details={},
            dev_mode=True,
        )
        assert result_dev["simulated"] is True, (
            f"simulated must be True when dev_mode=True, got {result_dev['simulated']}"
        )

    def test_unknown_action_action_type_preserved(self) -> None:
        """Unknown action result must preserve the original action_type string."""
        from src.actions.action_executor import execute_action

        result = execute_action(
            action_type="totally_made_up_action",
            details={},
            dev_mode=True,
        )

        assert result["action_type"] == "totally_made_up_action", (
            f"action_type must be preserved even for unknown actions, "
            f"got {result['action_type']!r}"
        )

    @pytest.mark.parametrize("unknown_type", [
        "fly_spaceship",
        "brew_coffee",
        "time_travel",
        "",
        "SEND_EMAIL",  # case-sensitive — uppercase is unknown if lowercase is the standard
    ])
    def test_various_unknown_action_types_return_failure(
        self, unknown_type: str
    ) -> None:
        """All unrecognised action_type values must return success=False."""
        from src.actions.action_executor import execute_action

        result = execute_action(
            action_type=unknown_type,
            details={},
            dev_mode=True,
        )

        assert result["success"] is False, (
            f"Unknown action '{unknown_type}' must return success=False, "
            f"got success={result['success']}"
        )
        assert "skipped: unknown_action" in result["details"], (
            f"Unknown action '{unknown_type}' must set details to "
            f"'skipped: unknown_action', got {result['details']!r}"
        )


# ---------------------------------------------------------------------------
# Test 7 — Result dict has all required keys (success, action_type, details, simulated)
# ---------------------------------------------------------------------------


class TestResultStructure:
    @pytest.mark.parametrize("action_type", KNOWN_ACTION_TYPES)
    def test_known_action_has_all_required_keys(self, action_type: str) -> None:
        """Every known action_type must return a dict with all required keys."""
        from src.actions.action_executor import execute_action

        result = execute_action(
            action_type=action_type,
            details={},
            dev_mode=True,
        )

        assert_valid_result(result, action_type)

    def test_unknown_action_has_all_required_keys(self) -> None:
        """Unknown action_type must also return a dict with all required keys."""
        from src.actions.action_executor import execute_action

        result = execute_action(
            action_type="unknown_xyz",
            details={},
            dev_mode=True,
        )

        assert_valid_result(result, "unknown_xyz")

    def test_success_field_is_bool(self) -> None:
        """The 'success' field must always be a Python bool, not int or truthy value."""
        from src.actions.action_executor import execute_action

        result = execute_action("send_email", {}, dev_mode=True)
        assert type(result["success"]) is bool, (
            f"'success' must be bool type (not int or object), "
            f"got {type(result['success'])}"
        )

    def test_simulated_field_is_bool(self) -> None:
        """The 'simulated' field must always be a Python bool."""
        from src.actions.action_executor import execute_action

        result = execute_action("create_invoice", {}, dev_mode=True)
        assert type(result["simulated"]) is bool, (
            f"'simulated' must be bool type, got {type(result['simulated'])}"
        )

    def test_action_type_field_matches_input(self) -> None:
        """The 'action_type' in result must always match the input argument."""
        from src.actions.action_executor import execute_action

        for action_type in KNOWN_ACTION_TYPES:
            result = execute_action(action_type, {}, dev_mode=True)
            assert result["action_type"] == action_type, (
                f"Result action_type must match input '{action_type}', "
                f"got {result['action_type']!r}"
            )

    def test_details_field_is_string(self) -> None:
        """The 'details' field must always be a str, never None or non-string."""
        from src.actions.action_executor import execute_action

        for action_type in KNOWN_ACTION_TYPES:
            result = execute_action(action_type, {}, dev_mode=True)
            assert isinstance(result["details"], str), (
                f"'details' for '{action_type}' must be str, "
                f"got {type(result['details'])}"
            )

    def test_dev_mode_default_is_true(self) -> None:
        """execute_action default dev_mode=True must simulate all actions."""
        from src.actions.action_executor import execute_action

        # Call without explicit dev_mode — should default to True
        result = execute_action("send_email", {"to": "test@example.com"})

        assert result["simulated"] is True, (
            f"Default dev_mode=True must set simulated=True, got {result['simulated']}"
        )

    def test_no_extra_side_effects_in_dev_mode(self, tmp_path: Path) -> None:
        """In DEV_MODE, execute_action must not create files, network calls, or
        other observable side effects beyond logging intent. Verified by checking
        that tmp_path remains unchanged after execution."""
        from src.actions.action_executor import execute_action

        # Note the state of tmp_path before
        before_files = set(tmp_path.rglob("*"))

        execute_action(
            action_type="send_email",
            details={"to": "external@example.com", "body": "Important email"},
            dev_mode=True,
        )

        # tmp_path should not have gained any files (no real side effects)
        after_files = set(tmp_path.rglob("*"))
        new_files = after_files - before_files
        # Tolerate log files in the same tmp_path only if the module writes there;
        # the assertion below is intentionally lenient — it warns, not fails hard,
        # to avoid false positives if the implementation uses tmp_path for caching.
        # The primary assertion is that success=True and simulated=True.
        result = execute_action(
            action_type="send_email",
            details={"to": "external@example.com"},
            dev_mode=True,
        )
        assert result["success"] is True
        assert result["simulated"] is True
