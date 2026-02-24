"""Rate limiter — epoch-hour window, JSON state, thread-safe."""

from __future__ import annotations

import json
import os
import threading
import time
from pathlib import Path

_LOCK = threading.Lock()
_STATE_FILE = "state/rate_limits.json"
_PRUNE_AFTER_HOURS = 2


def _state_path(vault_root: str) -> Path:
    return Path(vault_root) / _STATE_FILE


def _current_hour() -> int:
    return int(time.time() // 3600)


def _load(path: Path) -> dict:
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def _save(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _prune(data: dict, current_hour: int) -> dict:
    """Remove entries older than _PRUNE_AFTER_HOURS."""
    cutoff = current_hour - _PRUNE_AFTER_HOURS
    return {k: v for k, v in data.items() if _hour_from_key(k) > cutoff}


def _hour_from_key(key: str) -> int:
    """Extract epoch-hour from a key like 'send_email:1700278'."""
    try:
        return int(key.rsplit(":", 1)[-1])
    except (ValueError, IndexError):
        return 0


def _make_key(action_type: str, hour: int) -> str:
    return f"{action_type}:{hour}"


def check_and_increment(
    vault_root: str,
    action_type: str,
    limit_per_hour: int,
) -> bool:
    """Check rate limit and increment counter if allowed.

    Args:
        vault_root: Path to vault root directory.
        action_type: Action identifier (e.g. 'send_email').
        limit_per_hour: Maximum allowed calls in the current hour window.

    Returns:
        True if the action is allowed; False if rate limit exceeded.
    """
    path = _state_path(vault_root)
    current_hour = _current_hour()
    key = _make_key(action_type, current_hour)

    with _LOCK:
        data = _load(path)
        data = _prune(data, current_hour)

        count = data.get(key, 0)
        if count >= limit_per_hour:
            _save(path, data)
            return False

        data[key] = count + 1
        _save(path, data)
        return True
