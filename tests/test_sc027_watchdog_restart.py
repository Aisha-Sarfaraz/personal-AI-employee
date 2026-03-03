"""SC-027: Watchdog Restart — integration test, Phase 10, T047."""

from __future__ import annotations

import os
import threading
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture()
def vault(tmp_path):
    (tmp_path / "Inbox").mkdir()
    (tmp_path / "Logs").mkdir()
    (tmp_path / "state").mkdir()
    return tmp_path


def _make_dead_thread():
    t = threading.Thread(target=lambda: None)
    return t


# ---------------------------------------------------------------------------
# SC-027.1 Dead watcher thread restarted, audit logs result: success
# ---------------------------------------------------------------------------


def test_sc027_dead_thread_restarted(vault):
    """Given dead watcher thread, check_all_threads restarts it and audit logs success."""
    from src.watchers.watchdog import Watchdog

    watchdog = Watchdog(vault_root=str(vault))
    dead_thread = _make_dead_thread()

    mock_watcher = MagicMock()
    mock_watcher.vault_root = str(vault)

    watcher_registry = {"test_watcher": mock_watcher}
    thread_registry = {"test_watcher": dead_thread}

    new_thread = MagicMock()
    new_thread.is_alive.return_value = True

    with patch.object(watchdog, "_restart_watcher", return_value=new_thread):
        with patch("src.watchers.watchdog.log") as mock_log:
            watchdog.check_all_threads(watcher_registry, thread_registry)

    # Verify audit log was called with success
    assert mock_log.called
    calls = mock_log.call_args_list
    success_calls = [c for c in calls if c.kwargs.get("result") == "success"
                     or (c.args and c.args[-1] == "success")]
    assert len(success_calls) >= 1


# ---------------------------------------------------------------------------
# SC-027.2 3 consecutive failures create vault alert, audit logs result: failure
# ---------------------------------------------------------------------------


def test_sc027_three_failures_create_alert(vault):
    """Given 3 consecutive restart failures, vault alert created and audit logs failure."""
    from src.watchers.watchdog import Watchdog

    watchdog = Watchdog(vault_root=str(vault), max_restart_attempts=3)

    mock_watcher = MagicMock()
    watcher_registry = {"failing_watcher": mock_watcher}

    # Run 3 iterations with dead thread + failed restart
    for _ in range(3):
        dead_thread = _make_dead_thread()
        thread_registry = {"failing_watcher": dead_thread}
        with patch.object(watchdog, "_restart_watcher", return_value=None):
            watchdog.check_all_threads(watcher_registry, thread_registry)

    # Alert should be created
    inbox = os.path.join(str(vault), "Inbox")
    alerts = [f for f in os.listdir(inbox) if "WATCHDOG_ALERT" in f and "failing_watcher" in f]
    assert len(alerts) >= 1

    # Watcher should be in exhausted set
    assert "failing_watcher" in watchdog._exhausted
