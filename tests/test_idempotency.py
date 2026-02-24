"""
Tests for src.core.idempotency

TDD red phase: all tests MUST FAIL before implementation.

Covers:
  1. test_generate_key_format
  2. test_generate_key_deterministic
  3. test_new_key_stored
  4. test_existing_key_returns_cached
  5. test_expired_key_treated_as_new
  6. test_prunes_expired_entries
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


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestIdempotencyKeyGeneration:

    def test_generate_key_format(self, tmp_path: Path) -> None:
        """Key must match format: agent:action:sha256[:8]:epoch_day."""
        from src.core.idempotency import generate_key

        key = generate_key("triage_inbox", "triage", {"file": "test.md"})
        parts = key.split(":")
        assert len(parts) == 4, f"Key must have 4 colon-separated parts, got: {key}"
        assert parts[0] == "triage_inbox"
        assert parts[1] == "triage"
        assert len(parts[2]) == 8, "Hash segment must be 8 hex chars."
        assert parts[3].isdigit(), "Epoch-day must be numeric."

    def test_generate_key_deterministic(self, tmp_path: Path) -> None:
        """Same inputs must produce the same key."""
        from src.core.idempotency import generate_key

        details = {"to": "client@example.com", "subject": "Invoice"}
        key1 = generate_key("execute_plan", "send_email", details)
        key2 = generate_key("execute_plan", "send_email", details)
        assert key1 == key2, "generate_key must be deterministic."

    def test_different_details_different_key(self, tmp_path: Path) -> None:
        """Different details must produce different keys."""
        from src.core.idempotency import generate_key

        key1 = generate_key("agent", "action", {"x": 1})
        key2 = generate_key("agent", "action", {"x": 2})
        assert key1 != key2, "Different details must produce different keys."


class TestIdempotencyCheckAndStore:

    def test_new_key_stored(self, tmp_path: Path) -> None:
        """First call with a new key must store result and return (False, None)."""
        from src.core.idempotency import check_and_store

        vault = _make_vault(tmp_path)
        found, cached = check_and_store(
            vault, "agent:action:abc12345:19000",
            result={"success": True}, ttl_hours=24,
        )
        assert found is False, "New key: found must be False."
        assert cached is None, "New key: cached must be None."

    def test_existing_key_returns_cached(self, tmp_path: Path) -> None:
        """Second call with same key must return (True, <cached result>)."""
        from src.core.idempotency import check_and_store

        vault = _make_vault(tmp_path)
        key = "agent:action:abc12345:19000"
        result = {"success": True, "details": "sent"}

        check_and_store(vault, key, result=result, ttl_hours=24)
        found, cached = check_and_store(vault, key, result={}, ttl_hours=24)

        assert found is True, "Second call: found must be True."
        assert cached == result, f"Cached result mismatch: {cached}"

    def test_expired_key_treated_as_new(self, tmp_path: Path) -> None:
        """Key past its TTL must be treated as a new key (found=False)."""
        from src.core.idempotency import check_and_store

        vault = _make_vault(tmp_path)
        key = "agent:action:abc12345:19000"
        base_time = 1_700_000_000.0

        with patch("time.time", return_value=base_time):
            check_and_store(vault, key, result={"ok": True}, ttl_hours=1)

        # Advance 2 hours — TTL of 1h has expired
        with patch("time.time", return_value=base_time + 2 * 3600):
            found, cached = check_and_store(vault, key, result={}, ttl_hours=1)

        assert found is False, "Expired key must be treated as new."
        assert cached is None

    def test_prunes_expired_entries(self, tmp_path: Path) -> None:
        """check_and_store must remove expired keys from the state file on each call."""
        from src.core.idempotency import check_and_store

        vault = _make_vault(tmp_path)
        base_time = 1_700_000_000.0

        with patch("time.time", return_value=base_time):
            check_and_store(vault, "agent:a:aabb1122:19000", result={"x": 1}, ttl_hours=1)

        # Advance beyond TTL; make a second call with a different key
        with patch("time.time", return_value=base_time + 2 * 3600):
            check_and_store(vault, "agent:b:ccdd3344:19000", result={"y": 2}, ttl_hours=24)

        state_path = Path(vault) / "state" / "idempotency.json"
        data = json.loads(state_path.read_text())
        assert "agent:a:aabb1122:19000" not in data, "Expired entry must be pruned."
        assert "agent:b:ccdd3344:19000" in data, "Non-expired entry must remain."

    def test_thread_safety_no_crash(self, tmp_path: Path) -> None:
        """Concurrent calls must not raise or corrupt state."""
        import threading
        from src.core.idempotency import check_and_store

        vault = _make_vault(tmp_path)
        errors: list[Exception] = []

        def worker(i: int) -> None:
            try:
                check_and_store(vault, f"a:b:hash{i:04d}:19000", {"i": i}, ttl_hours=1)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"Thread-safety errors: {errors}"
