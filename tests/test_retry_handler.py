"""Tests for Gold Tier retry_handler — @with_retry decorator and ErrorCategory enum."""
import logging
import time
from unittest.mock import MagicMock, patch

import pytest

from src.core.retry_handler import ErrorCategory, with_retry


def test_retry_succeeds_on_third_attempt():
    """Function that fails twice then succeeds returns the success result."""
    call_count = [0]

    @with_retry(max_attempts=3, base_delay=0.01, max_delay=0.1)
    def flaky():
        call_count[0] += 1
        if call_count[0] < 3:
            raise ConnectionError("transient")
        return "ok"

    result = flaky()
    assert result == "ok"
    assert call_count[0] == 3


def test_all_attempts_fail_re_raises():
    """When all attempts fail, the original exception is re-raised."""
    @with_retry(max_attempts=3, base_delay=0.01, max_delay=0.1)
    def always_fails():
        raise ConnectionError("always fails")

    with pytest.raises(ConnectionError, match="always fails"):
        always_fails()


def test_auth_error_no_retry():
    """AUTH category error should not be retried — raise immediately."""
    call_count = [0]

    @with_retry(max_attempts=3, base_delay=0.01, max_delay=0.1)
    def auth_fail():
        call_count[0] += 1
        err = PermissionError("401 Unauthorized")
        err.error_category = ErrorCategory.AUTH
        raise err

    with pytest.raises(PermissionError):
        auth_fail()
    assert call_count[0] == 1


def test_logic_error_no_retry():
    """LOGIC category error should not be retried."""
    call_count = [0]

    @with_retry(max_attempts=3, base_delay=0.01, max_delay=0.1)
    def logic_fail():
        call_count[0] += 1
        err = ValueError("unexpected response")
        err.error_category = ErrorCategory.LOGIC
        raise err

    with pytest.raises(ValueError):
        logic_fail()
    assert call_count[0] == 1


def test_jitter_produces_nonnegative_delay():
    """Computed delay values should always be >= 0."""
    from src.core.retry_handler import _compute_delay
    for attempt in range(5):
        delay = _compute_delay(attempt, base_delay=1.0, max_delay=60.0)
        assert delay >= 0


def test_max_delay_cap_respected():
    """Delay should never exceed max_delay + 0.5 (jitter)."""
    from src.core.retry_handler import _compute_delay
    for attempt in range(10):
        delay = _compute_delay(attempt, base_delay=1.0, max_delay=2.0)
        assert delay <= 2.5  # max_delay + max jitter


def test_warning_logged_on_each_retry(caplog):
    """A WARNING log entry should be emitted on each retry attempt."""
    @with_retry(max_attempts=3, base_delay=0.01, max_delay=0.1)
    def flaky():
        raise ConnectionError("retry me")

    with caplog.at_level(logging.WARNING):
        with pytest.raises(ConnectionError):
            flaky()

    warning_records = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warning_records) == 2  # 2 retries (attempts 1 and 2 fail)


def test_decorated_function_signature_preserved():
    """The decorator should not destroy the function name/docstring."""
    @with_retry()
    def my_func():
        """My docstring."""
        return 42

    assert my_func.__name__ == "my_func"
    assert my_func.__doc__ == "My docstring."
