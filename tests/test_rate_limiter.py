"""
Tests for src.core.rate_limiter — check_and_increment(vault_root, action_type, limit_per_hour) -> bool

TDD red phase: all tests MUST FAIL before implementation.

Covers:
  1. test_allows_within_limit
  2. test_blocks_at_limit
  3. test_resets_after_hour
  4. test_different_action_types_independent
  5. test_prunes_old_keys
  6. test_creates_state_file_if_absent
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from unittest.mock import patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_vault(tmp_path: Path) -> str:
    vault = tmp_path / "vault"
    (vault / "state").mkdir(parents=True)
    return str(vault)


STATE_FILE = "state/rate_limits.json"


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestRateLimiter:

    def test_allows_within_limit(self, tmp_path: Path) -> None:
        """First call must return True (allowed) when under the hourly limit."""
        from src.core.rate_limiter import check_and_increment

        vault = _make_vault(tmp_path)
        result = check_and_increment(vault, "send_email", limit_per_hour=10)
        assert result is True, "First call should be allowed."

    def test_blocks_at_limit(self, tmp_path: Path) -> None:
        """After limit_per_hour calls, the next must return False (blocked)."""
        from src.core.rate_limiter import check_and_increment

        vault = _make_vault(tmp_path)
        limit = 3
        for _ in range(limit):
            check_and_increment(vault, "send_email", limit_per_hour=limit)

        result = check_and_increment(vault, "send_email", limit_per_hour=limit)
        assert result is False, f"Call #{limit+1} should be blocked."

    def test_resets_after_hour(self, tmp_path: Path) -> None:
        """Calls from a prior epoch-hour window must not count toward current limit."""
        from src.core.rate_limiter import check_and_increment

        vault = _make_vault(tmp_path)
        limit = 2

        # Fill limit at hour H
        base_time = 1_700_000_000.0  # arbitrary epoch second
        with patch("time.time", return_value=base_time):
            for _ in range(limit):
                check_and_increment(vault, "send_email", limit_per_hour=limit)

        # One hour later — limit should reset
        with patch("time.time", return_value=base_time + 3600):
            result = check_and_increment(vault, "send_email", limit_per_hour=limit)

        assert result is True, "After a full hour, the rate window should reset."

    def test_different_action_types_independent(self, tmp_path: Path) -> None:
        """Rate limit for 'send_email' must not affect 'create_invoice'."""
        from src.core.rate_limiter import check_and_increment

        vault = _make_vault(tmp_path)
        limit = 1

        check_and_increment(vault, "send_email", limit_per_hour=limit)
        blocked = check_and_increment(vault, "send_email", limit_per_hour=limit)
        assert blocked is False

        # Different type — should still be allowed
        other = check_and_increment(vault, "create_invoice", limit_per_hour=limit)
        assert other is True, "Different action types must have independent counters."

    def test_prunes_old_keys(self, tmp_path: Path) -> None:
        """State entries older than 2 hours must be pruned from the state file."""
        from src.core.rate_limiter import check_and_increment

        vault = _make_vault(tmp_path)
        base_time = 1_700_000_000.0

        with patch("time.time", return_value=base_time):
            check_and_increment(vault, "send_email", limit_per_hour=10)

        # Advance 3 hours — old key should be pruned
        with patch("time.time", return_value=base_time + 3 * 3600):
            check_and_increment(vault, "send_email", limit_per_hour=10)

        state_path = Path(vault) / STATE_FILE
        data = json.loads(state_path.read_text())
        old_hour_key = str(int(base_time // 3600))
        matching = [k for k in data if old_hour_key in k]
        assert not matching, "Keys older than 2 hours must be pruned."

    def test_creates_state_file_if_absent(self, tmp_path: Path) -> None:
        """check_and_increment must create state/rate_limits.json if it doesn't exist."""
        from src.core.rate_limiter import check_and_increment

        vault = _make_vault(tmp_path)
        state_path = Path(vault) / STATE_FILE
        assert not state_path.exists()

        check_and_increment(vault, "send_email", limit_per_hour=10)

        assert state_path.exists(), "State file must be created on first call."

    def test_thread_safety_no_crash(self, tmp_path: Path) -> None:
        """Concurrent calls must not raise exceptions or corrupt state."""
        import threading
        from src.core.rate_limiter import check_and_increment

        vault = _make_vault(tmp_path)
        errors: list[Exception] = []

        def worker() -> None:
            try:
                check_and_increment(vault, "send_email", limit_per_hour=100)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"Thread-safety errors: {errors}"
