"""install_schedule — register OS-level scheduled tasks for the FTE system.

Windows: uses schtasks.exe (idempotent: delete + recreate).
POSIX  : uses crontab (idempotent: strip # FTE lines + append fresh entries).

Entry point:
    python src/skills/install_schedule.py [vault_root]

Returns dict:
    {processed, platform, tasks_created, tasks_updated, errors, skipped}
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Any

# Ensure project root is importable when run directly
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from src.core.audit_logger import log_action

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Paths relative to project root (where orchestrator.py lives)
_ORCHESTRATOR_CMD = f'python "{os.path.join(_PROJECT_ROOT, "src", "orchestrator.py")}"'
_BRIEFING_CMD = f'python "{os.path.join(_PROJECT_ROOT, "src", "skills", "weekly_briefing.py")}"'

_WIN_TASKS: list[dict[str, str]] = [
    {
        "name": "FTE-Orchestrator",
        "cmd": _ORCHESTRATOR_CMD,
        "schedule": "/sc onstart",
        "extra": "",
    },
    {
        "name": "FTE-WeeklyBriefing",
        "cmd": _BRIEFING_CMD,
        "schedule": "/sc weekly /d MON /st 08:00",
        "extra": "",
    },
]

_FTE_TAG = "# FTE"

_POSIX_ENTRIES: list[str] = [
    f"@reboot {_ORCHESTRATOR_CMD} {_FTE_TAG}",
    f"0 8 * * 1 {_BRIEFING_CMD} {_FTE_TAG}",
]


# ---------------------------------------------------------------------------
# Windows helpers
# ---------------------------------------------------------------------------


def _win_delete(task_name: str) -> subprocess.CompletedProcess[str]:
    """Delete a Windows scheduled task (ignore errors — idempotent)."""
    return subprocess.run(
        ["schtasks", "/delete", "/tn", task_name, "/f"],
        capture_output=True,
        text=True,
    )


def _win_create(task: dict[str, str], python_exe: str) -> subprocess.CompletedProcess[str]:
    """Create a Windows scheduled task."""
    schedule_parts = task["schedule"].split()
    cmd_parts = ["schtasks", "/create", "/tn", task["name"]]
    cmd_parts += schedule_parts
    cmd_parts += ["/tr", f"{python_exe} {task['cmd']}"]
    if task.get("extra"):
        cmd_parts += task["extra"].split()
    return subprocess.run(cmd_parts, capture_output=True, text=True)


def _install_windows(vault_root: str) -> dict[str, Any]:
    """Register FTE tasks via schtasks.exe."""
    python_exe = sys.executable
    errors: list[str] = []
    tasks_created = 0

    for task in _WIN_TASKS:
        # Delete first (idempotent)
        _win_delete(task["name"])

        # Create
        result = _win_create(task, python_exe)
        if result.returncode != 0:
            errors.append(f"{task['name']}: {result.stderr.strip()}")
        else:
            tasks_created += 1
            print(f"  [OK] Scheduled task created: {task['name']}")

    return {
        "processed": len(_WIN_TASKS),
        "platform": "windows",
        "tasks_created": tasks_created,
        "tasks_updated": 0,
        "errors": errors,
        "skipped": 0,
    }


# ---------------------------------------------------------------------------
# POSIX helpers
# ---------------------------------------------------------------------------


def _read_crontab() -> str:
    """Read current crontab, return empty string if none."""
    result = subprocess.run(
        ["crontab", "-l"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return ""
    return result.stdout


def _write_crontab(content: str) -> subprocess.CompletedProcess[str]:
    """Write new crontab content."""
    return subprocess.run(
        ["crontab", "-"],
        input=content,
        capture_output=True,
        text=True,
    )


def _strip_fte_lines(crontab: str) -> str:
    """Remove all lines tagged with # FTE."""
    lines = [ln for ln in crontab.splitlines() if _FTE_TAG not in ln]
    return "\n".join(lines).strip()


def _install_posix(vault_root: str) -> dict[str, Any]:
    """Register FTE entries via crontab."""
    errors: list[str] = []
    existing = _read_crontab()
    stripped = _strip_fte_lines(existing)

    # Build new crontab: existing (without FTE) + fresh FTE entries
    new_lines = [stripped] if stripped else []
    new_lines.extend(_POSIX_ENTRIES)
    new_content = "\n".join(new_lines) + "\n"

    result = _write_crontab(new_content)
    if result.returncode != 0:
        errors.append(f"crontab write failed: {result.stderr.strip()}")
        return {
            "processed": len(_POSIX_ENTRIES),
            "platform": "posix",
            "tasks_created": 0,
            "tasks_updated": 0,
            "errors": errors,
            "skipped": 0,
        }

    for entry in _POSIX_ENTRIES:
        print(f"  [OK] Crontab entry added: {entry}")

    return {
        "processed": len(_POSIX_ENTRIES),
        "platform": "posix",
        "tasks_created": len(_POSIX_ENTRIES),
        "tasks_updated": 0,
        "errors": errors,
        "skipped": 0,
    }


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def run(vault_root: str) -> dict[str, Any]:
    """Install OS-level scheduled tasks for the FTE system.

    Args:
        vault_root: Absolute path to vault directory (for audit log).

    Returns:
        Result dict: {processed, platform, tasks_created, tasks_updated, errors, skipped}
    """
    print("[install_schedule] Registering scheduled tasks…")

    if sys.platform == "win32":
        result = _install_windows(vault_root)
    else:
        result = _install_posix(vault_root)

    status = "success" if not result["errors"] else "partial"
    detail = (
        f"platform={result['platform']} "
        f"tasks_created={result['tasks_created']} "
        f"errors={result['errors']}"
    )

    try:
        log_action(
            vault_root=vault_root,
            agent="install_schedule",
            action="schedule_installed",
            risk_tier="LOW",
            status=status,
            details=detail,
        )
    except Exception:
        pass  # Audit failure must not block scheduling

    print(f"[install_schedule] Done. Platform={result['platform']}, "
          f"tasks_created={result['tasks_created']}, errors={result['errors']}")
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
