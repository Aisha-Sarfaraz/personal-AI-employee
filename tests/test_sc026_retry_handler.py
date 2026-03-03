"""Integration tests for @with_retry — SC-026 Gold Tier T032."""

from __future__ import annotations

import logging
from unittest.mock import patch

import pytest

from src.core.retry_handler import ErrorCategory, with_retry


# Patch sleep so tests run fast
@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr("src.core.retry_handler.time.sleep", lambda _: None)


# ---------------------------------------------------------------------------
# SC-026.1  Function that fails twice then succeeds on 3rd call
# ---------------------------------------------------------------------------

def test_retry_succeeds_on_third_attempt():
    call_count = [0]

    @with_retry(max_attempts=3, base_delay=0.001, max_delay=0.01)
    def flaky():
        call_count[0] += 1
        if call_count[0] < 3:
            raise ConnectionError("transient")
        return "ok"

    result = flaky()
    assert result == "ok"
    assert call_count[0] == 3


# ---------------------------------------------------------------------------
# SC-026.2  All 3 attempts fail → exception re-raised
# ---------------------------------------------------------------------------

def test_all_attempts_fail_reraises():
    call_count = [0]

    @with_retry(max_attempts=3, base_delay=0.001, max_delay=0.01)
    def always_fails():
        call_count[0] += 1
        raise ConnectionError("always transient")

    with pytest.raises(ConnectionError, match="always transient"):
        always_fails()

    assert call_count[0] == 3


# ---------------------------------------------------------------------------
# SC-026.3  AUTH error → raised immediately, no retry
# ---------------------------------------------------------------------------

def test_auth_error_no_retry():
    call_count = [0]

    @with_retry(max_attempts=3, base_delay=0.001, max_delay=0.01)
    def auth_fail():
        call_count[0] += 1
        exc = PermissionError("401 Unauthorized")
        exc.error_category = ErrorCategory.AUTH  # type: ignore[attr-defined]
        raise exc

    with pytest.raises(PermissionError, match="401"):
        auth_fail()

    assert call_count[0] == 1  # No retry for AUTH


# ---------------------------------------------------------------------------
# SC-026.4  LOGIC error → raised immediately, no retry
# ---------------------------------------------------------------------------

def test_logic_error_no_retry():
    call_count = [0]

    @with_retry(max_attempts=3, base_delay=0.001, max_delay=0.01)
    def logic_fail():
        call_count[0] += 1
        exc = ValueError("unexpected response")
        exc.error_category = ErrorCategory.LOGIC  # type: ignore[attr-defined]
        raise exc

    with pytest.raises(ValueError):
        logic_fail()

    assert call_count[0] == 1  # No retry for LOGIC


# ---------------------------------------------------------------------------
# SC-026.5  logging.warning emitted on each retry attempt
# ---------------------------------------------------------------------------

def test_warning_logged_on_each_retry(caplog):
    call_count = [0]

    @with_retry(max_attempts=3, base_delay=0.001, max_delay=0.01)
    def two_retries():
        call_count[0] += 1
        if call_count[0] < 3:
            raise ConnectionError("oops")
        return "done"

    with caplog.at_level(logging.WARNING):
        result = two_retries()

    assert result == "done"
    # Should have logged 2 warning messages (attempt 1 and attempt 2 failed)
    warning_msgs = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warning_msgs) == 2


# ---------------------------------------------------------------------------
# SC-026.6  Decorated function preserves its name (functools.wraps)
# ---------------------------------------------------------------------------

def test_decorated_function_preserves_name():
    @with_retry(max_attempts=3)
    def my_special_function():
        return 42

    assert my_special_function.__name__ == "my_special_function"


# ---------------------------------------------------------------------------
# SC-026.7  Retry with OdooMCPClient mock — real decorator on real method
# ---------------------------------------------------------------------------

def test_odoo_client_retries_on_connection_error(tmp_path):
    """OdooMCPClient._execute_kw is decorated; mock requests.post to fail twice."""
    from src.mcp_servers.odoo_mcp.client import OdooMCPClient

    client = OdooMCPClient(
        url="http://localhost:9999",
        db="testdb",
        uid=1,
        password="testpw",
        dev_mode=False,
    )

    call_count = [0]

    def fake_post(*args, **kwargs):
        call_count[0] += 1
        if call_count[0] < 3:
            raise ConnectionError("simulated connection failure")
        # Return success on 3rd attempt
        import json as _json
        from unittest.mock import MagicMock
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"result": [{"id": 1, "name": "INV001"}]}
        mock_resp.raise_for_status.return_value = None
        return mock_resp

    with patch("requests.post", side_effect=fake_post):
        result = client._execute_kw("account.move", "search_read", [[]], {"limit": 1})

    assert call_count[0] == 3
    assert isinstance(result, list)
