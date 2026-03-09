"""Tests for Watchdog — TDD Phase 10, T045."""

from __future__ import annotations

import os
import threading
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def vault(tmp_path):
    (tmp_path / "Inbox").mkdir()
    (tmp_path / "Logs").mkdir()
    (tmp_path / "state").mkdir()
    return tmp_path


def _make_dead_thread():
    """Create a thread that is not alive (never started)."""
    t = threading.Thread(target=lambda: None)
    # Don't start it — is_alive() will be False
    return t


def _make_alive_thread():
    """Create a thread that is alive (running)."""
    import time
    t = threading.Thread(target=lambda: time.sleep(10), daemon=True)
    t.start()
    return t


# ---------------------------------------------------------------------------
# Test 1: detects dead thread and calls _restart_watcher
# ---------------------------------------------------------------------------


def test_detects_dead_thread_and_restarts(vault):
    """check_all_threads detects dead thread (is_alive()=False) and calls _restart_watcher."""
    from src.watchers.watchdog import Watchdog

    watchdog = Watchdog(vault_root=str(vault))
    dead_thread = _make_dead_thread()

    mock_watcher = MagicMock()
    watcher_registry = {"test_watcher": mock_watcher}
    thread_registry = {"test_watcher": dead_thread}

    new_thread = MagicMock()
    new_thread.is_alive.return_value = True

    with patch.object(watchdog, "_restart_watcher", return_value=new_thread) as mock_restart:
        watchdog.check_all_threads(watcher_registry, thread_registry)
        mock_restart.assert_called_once()


# ---------------------------------------------------------------------------
# Test 2: successful restart resets failure_count to 0
# ---------------------------------------------------------------------------


def test_successful_restart_resets_failure_count(vault):
    """Successful restart resets failure_count to 0."""
    from src.watchers.watchdog import Watchdog

    watchdog = Watchdog(vault_root=str(vault))
    watchdog._failure_counts["test_watcher"] = 2  # pre-existing failures

    dead_thread = _make_dead_thread()
    mock_watcher = MagicMock()
    watcher_registry = {"test_watcher": mock_watcher}
    thread_registry = {"test_watcher": dead_thread}

    new_thread = MagicMock()
    new_thread.is_alive.return_value = True

    with patch.object(watchdog, "_restart_watcher", return_value=new_thread):
        watchdog.check_all_threads(watcher_registry, thread_registry)

    assert watchdog._failure_counts.get("test_watcher", 0) == 0


# ---------------------------------------------------------------------------
# Test 3: failed restart increments failure_count
# ---------------------------------------------------------------------------


def test_failed_restart_increments_failure_count(vault):
    """Failed restart increments failure_count."""
    from src.watchers.watchdog import Watchdog

    watchdog = Watchdog(vault_root=str(vault))
    dead_thread = _make_dead_thread()
    mock_watcher = MagicMock()
    watcher_registry = {"test_watcher": mock_watcher}
    thread_registry = {"test_watcher": dead_thread}

    with patch.object(watchdog, "_restart_watcher", return_value=None):
        with patch.object(watchdog, "_create_alert"):
            watchdog.check_all_threads(watcher_registry, thread_registry)

    assert watchdog._failure_counts.get("test_watcher", 0) == 1


# ---------------------------------------------------------------------------
# Test 4: after 3 failures, _create_alert called
# ---------------------------------------------------------------------------


def test_three_failures_triggers_alert(vault):
    """After 3 failures, _create_alert called."""
    from src.watchers.watchdog import Watchdog

    watchdog = Watchdog(vault_root=str(vault), max_restart_attempts=3)
    watchdog._failure_counts["test_watcher"] = 2  # 2 previous failures

    dead_thread = _make_dead_thread()
    mock_watcher = MagicMock()
    watcher_registry = {"test_watcher": mock_watcher}
    thread_registry = {"test_watcher": dead_thread}

    with patch.object(watchdog, "_restart_watcher", return_value=None):
        with patch.object(watchdog, "_create_alert") as mock_alert:
            watchdog.check_all_threads(watcher_registry, thread_registry)
            mock_alert.assert_called_once_with("test_watcher")


# ---------------------------------------------------------------------------
# Test 5: alert creates WATCHDOG_ALERT file
# ---------------------------------------------------------------------------


def test_alert_creates_file(vault):
    """Alert creates vault/Inbox/WATCHDOG_ALERT_{name}_{ts}.md."""
    from src.watchers.watchdog import Watchdog

    watchdog = Watchdog(vault_root=str(vault))
    watchdog._create_alert("my_watcher")

    inbox = os.path.join(str(vault), "Inbox")
    alerts = [f for f in os.listdir(inbox) if f.startswith("WATCHDOG_ALERT_my_watcher")]
    assert len(alerts) >= 1


# ---------------------------------------------------------------------------
# Test 6: after 3 failures, that watcher not retried
# ---------------------------------------------------------------------------


def test_exhausted_watcher_not_retried(vault):
    """After 3 failures, that watcher not retried again."""
    from src.watchers.watchdog import Watchdog

    watchdog = Watchdog(vault_root=str(vault), max_restart_attempts=3)
    watchdog._exhausted.add("test_watcher")

    dead_thread = _make_dead_thread()
    mock_watcher = MagicMock()
    watcher_registry = {"test_watcher": mock_watcher}
    thread_registry = {"test_watcher": dead_thread}

    with patch.object(watchdog, "_restart_watcher") as mock_restart:
        watchdog.check_all_threads(watcher_registry, thread_registry)
        mock_restart.assert_not_called()


# ---------------------------------------------------------------------------
# Test 7: healthy thread not touched
# ---------------------------------------------------------------------------


def test_healthy_thread_not_touched(vault):
    """Healthy thread (is_alive()=True) not restarted."""
    from src.watchers.watchdog import Watchdog

    watchdog = Watchdog(vault_root=str(vault))
    alive_thread = _make_alive_thread()

    mock_watcher = MagicMock()
    watcher_registry = {"healthy_watcher": mock_watcher}
    thread_registry = {"healthy_watcher": alive_thread}

    with patch.object(watchdog, "_restart_watcher") as mock_restart:
        watchdog.check_all_threads(watcher_registry, thread_registry)
        mock_restart.assert_not_called()

    alive_thread.join(timeout=0.1)


# ---------------------------------------------------------------------------
# Test 8: audit_logger.log called with action_type: watchdog_restart
# ---------------------------------------------------------------------------


def test_audit_log_on_restart(vault):
    """audit_logger.log called with action_type: watchdog_restart."""
    from src.watchers.watchdog import Watchdog

    watchdog = Watchdog(vault_root=str(vault))
    dead_thread = _make_dead_thread()
    mock_watcher = MagicMock()
    watcher_registry = {"test_watcher": mock_watcher}
    thread_registry = {"test_watcher": dead_thread}

    new_thread = MagicMock()
    new_thread.is_alive.return_value = True

    with patch.object(watchdog, "_restart_watcher", return_value=new_thread):
        with patch("src.watchers.watchdog.log") as mock_log:
            watchdog.check_all_threads(watcher_registry, thread_registry)
            mock_log.assert_called()
            call_kwargs = mock_log.call_args
            assert call_kwargs is not None
            # Check action_type in positional or keyword args
            args, kwargs = call_kwargs
            action = kwargs.get("action_type", args[1] if len(args) > 1 else "")
            assert action == "watchdog_restart"
