"""Idempotency store — SHA-256 keyed, TTL-expiring, thread-safe."""

from __future__ import annotations

import hashlib
import json
import threading
import time
from pathlib import Path
from typing import Any

_LOCK = threading.Lock()
_STATE_FILE = "state/idempotency.json"


def _state_path(vault_root: str) -> Path:
    return Path(vault_root) / _STATE_FILE


def _now() -> float:
    return time.time()


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


def _prune(data: dict) -> dict:
    now = _now()
    return {k: v for k, v in data.items() if v.get("expires_at", 0) > now}


def generate_key(agent: str, action: str, details: dict[str, Any]) -> str:
    """Generate a deterministic idempotency key.

    Format: {agent}:{action}:{sha256[:8]}:{epoch_day}
    """
    details_str = json.dumps(details, sort_keys=True)
    sha = hashlib.sha256(details_str.encode()).hexdigest()[:8]
    epoch_day = int(_now() // 86400)
    return f"{agent}:{action}:{sha}:{epoch_day}"


def check_and_store(
    vault_root: str,
    key: str,
    result: dict[str, Any],
    ttl_hours: int = 24,
) -> tuple[bool, dict[str, Any] | None]:
    """Check if key exists; if not, store result with TTL.

    Args:
        vault_root: Path to vault root.
        key: Idempotency key (from generate_key).
        result: Result dict to cache if key is new.
        ttl_hours: How long to retain the cached result.

    Returns:
        (found, cached_result) — found=True means a cached result was returned.
    """
    path = _state_path(vault_root)
    now = _now()

    with _LOCK:
        data = _load(path)
        data = _prune(data)

        if key in data:
            cached = data[key].get("result")
            _save(path, data)
            return True, cached

        data[key] = {
            "result": result,
            "stored_at": now,
            "expires_at": now + ttl_hours * 3600,
        }
        _save(path, data)
        return False, None
