"""uninstall_schedule — remove OS-level scheduled tasks for the FTE system.

Windows: schtasks /delete for FTE-Orchestrator and FTE-WeeklyBriefing.
POSIX  : strips all # FTE lines from crontab.

Entry point:
    python src/skills/uninstall_schedule.py [vault_root]

Returns dict:
    {processed, platform, tasks_created, tasks_updated, errors, skipped}
"""

from __future__ import annotations

import os
import subprocess
import sys
from typing import Any

# Ensure project root is importable when run directly
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from src.core.audit_logger import log_action

_WIN_TASK_NAMES = ("FTE-Orchestrator", "FTE-WeeklyBriefing")
_FTE_TAG = "# FTE"


# ---------------------------------------------------------------------------
# Windows
# ---------------------------------------------------------------------------


def _uninstall_windows(vault_root: str) -> dict[str, Any]:
    """Remove FTE tasks via schtasks /delete."""
    errors: list[str] = []
    removed = 0

    for task_name in _WIN_TASK_NAMES:
        result = subprocess.run(
            ["schtasks", "/delete", "/tn", task_name, "/f"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            # Task may not exist — treat as skipped, not error
            print(f"  [SKIP] {task_name}: not found or already removed.")
        else:
            removed += 1
            print(f"  [OK] Removed scheduled task: {task_name}")

    return {
        "processed": len(_WIN_TASK_NAMES),
        "platform": "windows",
        "tasks_created": 0,
        "tasks_updated": 0,
        "errors": errors,
        "skipped": len(_WIN_TASK_NAMES) - removed,
    }


# ---------------------------------------------------------------------------
# POSIX
# ---------------------------------------------------------------------------


def _read_crontab() -> str:
    result = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
    if result.returncode != 0:
        return ""
    return result.stdout


def _write_crontab(content: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["crontab", "-"], input=content, capture_output=True, text=True)


def _strip_fte_lines(crontab: str) -> str:
    lines = [ln for ln in crontab.splitlines() if _FTE_TAG not in ln]
    return "\n".join(lines).strip()


def _uninstall_posix(vault_root: str) -> dict[str, Any]:
    """Strip FTE entries from crontab."""
    errors: list[str] = []
    existing = _read_crontab()
    stripped = _strip_fte_lines(existing)

    # Count how many FTE lines were removed
    original_fte = [ln for ln in existing.splitlines() if _FTE_TAG in ln]
    removed_count = len(original_fte)

    new_content = stripped + ("\n" if stripped else "")
    result = _write_crontab(new_content)

    if result.returncode != 0:
        errors.append(f"crontab write failed: {result.stderr.strip()}")
    else:
        print(f"  [OK] Removed {removed_count} # FTE crontab entries.")

    return {
        "processed": removed_count,
        "platform": "posix",
        "tasks_created": 0,
        "tasks_updated": 0,
        "errors": errors,
        "skipped": 0,
    }


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def run(vault_root: str) -> dict[str, Any]:
    """Remove OS-level scheduled tasks for the FTE system.

    Args:
        vault_root: Absolute path to vault directory (for audit log).

    Returns:
        Result dict: {processed, platform, tasks_created, tasks_updated, errors, skipped}
    """
    print("[uninstall_schedule] Removing scheduled tasks…")

    if sys.platform == "win32":
        result = _uninstall_windows(vault_root)
    else:
        result = _uninstall_posix(vault_root)

    status = "success" if not result["errors"] else "partial"
    detail = (
        f"platform={result['platform']} "
        f"processed={result['processed']} "
        f"errors={result['errors']}"
    )

    try:
        log_action(
            vault_root=vault_root,
            agent="uninstall_schedule",
            action="schedule_uninstalled",
            risk_tier="LOW",
            status=status,
            details=detail,
        )
    except Exception:
        pass  # Audit failure must not block uninstall

    print(f"[uninstall_schedule] Done. Platform={result['platform']}, "
          f"processed={result['processed']}, errors={result['errors']}")
    return result


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    _vault = sys.argv[1] if len(sys.argv) > 1 else "vault"
    _vault = os.path.abspath(_vault)
    _result = run(_vault)
    if _result["errors"]:
        sys.exit(1)
