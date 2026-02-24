"""
Tests for src.skills.install_schedule and src.skills.uninstall_schedule.

TDD red phase: these MUST FAIL before implementation exists.

Covers:
  1. test_windows_creates_orchestrator_task
  2. test_windows_creates_briefing_task
  3. test_windows_idempotent_no_duplicates
  4. test_posix_adds_two_crontab_entries
  5. test_posix_idempotent_still_two_entries
  6. test_uninstall_removes_all_fte_tasks
  7. test_returns_correct_platform_in_result
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, call, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

REQUIRED_RESULT_KEYS = frozenset(
    {"processed", "platform", "tasks_created", "tasks_updated", "errors", "skipped"}
)

FTE_TASK_NAMES = ("FTE-Orchestrator", "FTE-WeeklyBriefing")

# Mock successful schtasks subprocess results
_WIN_SUCCESS = MagicMock(returncode=0, stdout="", stderr="")
_WIN_DELETE_SUCCESS = MagicMock(returncode=0, stdout="", stderr="")


def _make_crontab_output(*lines: str) -> MagicMock:
    """Return a mock subprocess.CompletedProcess with crontab -l output."""
    return MagicMock(
        returncode=0,
        stdout="\n".join(lines) + ("\n" if lines else ""),
        stderr="",
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def tmp_vault(tmp_path: Path) -> str:
    """Create a minimal temp vault with state dir."""
    (tmp_path / "state").mkdir(parents=True)
    (tmp_path / "Logs").mkdir(parents=True)
    return str(tmp_path)


# ---------------------------------------------------------------------------
# Windows tests
# ---------------------------------------------------------------------------


@pytest.mark.skipif(sys.platform != "win32", reason="Windows-only")
class TestWindowsScheduling:
    """Tests that run only on Windows (use schtasks.exe)."""

    def test_windows_creates_orchestrator_task(self, tmp_vault: str) -> None:
        """install_schedule must call schtasks /create for FTE-Orchestrator."""
        from src.skills.install_schedule import run as install_run

        with patch("subprocess.run", return_value=_WIN_SUCCESS) as mock_sub:
            result = install_run(tmp_vault)

        called_args = [" ".join(c.args[0]) for c in mock_sub.call_args_list]
        assert any("FTE-Orchestrator" in a for a in called_args), (
            f"Expected schtasks call for FTE-Orchestrator. Got: {called_args}"
        )

    def test_windows_creates_briefing_task(self, tmp_vault: str) -> None:
        """install_schedule must call schtasks /create for FTE-WeeklyBriefing."""
        from src.skills.install_schedule import run as install_run

        with patch("subprocess.run", return_value=_WIN_SUCCESS) as mock_sub:
            result = install_run(tmp_vault)

        called_args = [" ".join(c.args[0]) for c in mock_sub.call_args_list]
        assert any("FTE-WeeklyBriefing" in a for a in called_args), (
            f"Expected schtasks call for FTE-WeeklyBriefing. Got: {called_args}"
        )

    def test_windows_idempotent_no_duplicates(self, tmp_vault: str) -> None:
        """Running install twice must delete-then-create (not double-create)."""
        from src.skills.install_schedule import run as install_run

        with patch("subprocess.run", return_value=_WIN_SUCCESS) as mock_sub:
            install_run(tmp_vault)
            call_count_first = mock_sub.call_count
            install_run(tmp_vault)
            call_count_second = mock_sub.call_count

        # Second run should have same number of calls as first (not accumulating)
        assert call_count_second == call_count_first * 2, (
            "Second install should make same number of subprocess calls as first."
        )

    def test_returns_correct_platform_in_result_windows(self, tmp_vault: str) -> None:
        """Result dict must contain platform='windows' on win32."""
        from src.skills.install_schedule import run as install_run

        with patch("subprocess.run", return_value=_WIN_SUCCESS):
            result = install_run(tmp_vault)

        assert result.get("platform") in ("windows", "win32"), (
            f"Expected platform='windows', got: {result.get('platform')}"
        )

    def test_windows_uninstall_removes_tasks(self, tmp_vault: str) -> None:
        """uninstall must call schtasks /delete for both FTE tasks."""
        from src.skills.uninstall_schedule import run as uninstall_run

        with patch("subprocess.run", return_value=_WIN_DELETE_SUCCESS) as mock_sub:
            result = uninstall_run(tmp_vault)

        called_args = [" ".join(c.args[0]) for c in mock_sub.call_args_list]
        for task_name in FTE_TASK_NAMES:
            assert any(task_name in a for a in called_args), (
                f"Expected schtasks /delete for {task_name}. Got: {called_args}"
            )


# ---------------------------------------------------------------------------
# POSIX tests (Linux / macOS)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX-only")
class TestPosixScheduling:
    """Tests that run only on POSIX (use crontab)."""

    def test_posix_adds_two_crontab_entries(self, tmp_vault: str) -> None:
        """install on POSIX must add exactly 2 # FTE crontab entries."""
        from src.skills.install_schedule import run as install_run

        # Start with empty crontab
        empty_crontab = _make_crontab_output()
        captured_stdin: list[str] = []

        def fake_run(cmd: list[str], **kwargs: Any) -> MagicMock:
            if "crontab" in cmd and "-l" in cmd:
                return empty_crontab
            if "crontab" in cmd and "-" in cmd:
                captured_stdin.append(kwargs.get("input", ""))
                return MagicMock(returncode=0, stdout="", stderr="")
            return MagicMock(returncode=0, stdout="", stderr="")

        with patch("subprocess.run", side_effect=fake_run):
            install_run(tmp_vault)

        assert captured_stdin, "Expected crontab - to be called with new content."
        written = captured_stdin[-1]
        fte_lines = [ln for ln in written.splitlines() if "# FTE" in ln]
        assert len(fte_lines) == 2, (
            f"Expected exactly 2 # FTE entries, got {len(fte_lines)}: {fte_lines}"
        )

    def test_posix_idempotent_still_two_entries(self, tmp_vault: str) -> None:
        """Running install twice on POSIX must still result in exactly 2 entries."""
        from src.skills.install_schedule import run as install_run

        # Simulate crontab already having FTE entries from first run
        existing_crontab = _make_crontab_output(
            "0 0 * * * some_other_job",
            "@reboot python src/orchestrator.py # FTE",
            "0 8 * * 1 python src/skills/weekly_briefing.py # FTE",
        )
        captured_stdin: list[str] = []

        def fake_run(cmd: list[str], **kwargs: Any) -> MagicMock:
            if "crontab" in cmd and "-l" in cmd:
                return existing_crontab
            if "crontab" in cmd and "-" in cmd:
                captured_stdin.append(kwargs.get("input", ""))
                return MagicMock(returncode=0, stdout="", stderr="")
            return MagicMock(returncode=0, stdout="", stderr="")

        with patch("subprocess.run", side_effect=fake_run):
            install_run(tmp_vault)

        assert captured_stdin, "Expected crontab - to be called."
        written = captured_stdin[-1]
        fte_lines = [ln for ln in written.splitlines() if "# FTE" in ln]
        assert len(fte_lines) == 2, (
            f"Expected exactly 2 # FTE entries after idempotent run, got {len(fte_lines)}: {fte_lines}"
        )

    def test_posix_uninstall_removes_fte_lines(self, tmp_vault: str) -> None:
        """uninstall on POSIX must strip # FTE lines and write back clean crontab."""
        from src.skills.uninstall_schedule import run as uninstall_run

        existing_crontab = _make_crontab_output(
            "0 0 * * * some_other_job",
            "@reboot python src/orchestrator.py # FTE",
            "0 8 * * 1 python src/skills/weekly_briefing.py # FTE",
        )
        captured_stdin: list[str] = []

        def fake_run(cmd: list[str], **kwargs: Any) -> MagicMock:
            if "crontab" in cmd and "-l" in cmd:
                return existing_crontab
            if "crontab" in cmd and "-" in cmd:
                captured_stdin.append(kwargs.get("input", ""))
                return MagicMock(returncode=0, stdout="", stderr="")
            return MagicMock(returncode=0, stdout="", stderr="")

        with patch("subprocess.run", side_effect=fake_run):
            uninstall_run(tmp_vault)

        assert captured_stdin, "Expected crontab - to be called on uninstall."
        written = captured_stdin[-1]
        fte_lines = [ln for ln in written.splitlines() if "# FTE" in ln]
        assert len(fte_lines) == 0, (
            f"Expected 0 # FTE entries after uninstall, got {len(fte_lines)}: {fte_lines}"
        )
        assert "some_other_job" in written, (
            "Uninstall must preserve non-FTE crontab lines."
        )

    def test_returns_correct_platform_in_result_posix(self, tmp_vault: str) -> None:
        """Result dict must contain platform='posix' on Linux/macOS."""
        from src.skills.install_schedule import run as install_run

        def fake_run(cmd: list[str], **kwargs: Any) -> MagicMock:
            if "crontab" in cmd and "-l" in cmd:
                return _make_crontab_output()
            return MagicMock(returncode=0, stdout="", stderr="")

        with patch("subprocess.run", side_effect=fake_run):
            result = install_run(tmp_vault)

        assert result.get("platform") == "posix", (
            f"Expected platform='posix', got: {result.get('platform')}"
        )


# ---------------------------------------------------------------------------
# Platform-agnostic tests
# ---------------------------------------------------------------------------


class TestScheduleResultShape:
    """Tests that work on any platform (mock sys.platform)."""

    def _make_windows_fake(self) -> Any:
        def fake_run(cmd: list[str], **kwargs: Any) -> MagicMock:
            return MagicMock(returncode=0, stdout="", stderr="")
        return fake_run

    def _make_posix_fake(self) -> Any:
        def fake_run(cmd: list[str], **kwargs: Any) -> MagicMock:
            if "crontab" in cmd and "-l" in cmd:
                return _make_crontab_output()
            return MagicMock(returncode=0, stdout="", stderr="")
        return fake_run

    def test_returns_correct_platform_in_result(self, tmp_vault: str) -> None:
        """Result dict must contain 'platform' key matching the detected OS."""
        from src.skills import install_schedule

        if sys.platform == "win32":
            fake = self._make_windows_fake()
            expected_platforms = {"windows", "win32"}
        else:
            fake = self._make_posix_fake()
            expected_platforms = {"posix", "linux", "darwin"}

        with patch("subprocess.run", side_effect=fake):
            result = install_schedule.run(tmp_vault)

        assert isinstance(result, dict), f"run() must return dict, got {type(result)}"
        missing = REQUIRED_RESULT_KEYS - result.keys()
        assert not missing, f"Result missing required keys: {missing}"
        assert result["platform"] in expected_platforms, (
            f"Expected platform in {expected_platforms}, got {result['platform']!r}"
        )

    def test_uninstall_removes_all_fte_tasks(self, tmp_vault: str) -> None:
        """uninstall_schedule.run() must return dict with required keys and no errors."""
        from src.skills import uninstall_schedule

        if sys.platform == "win32":
            fake = self._make_windows_fake()
        else:
            existing = _make_crontab_output(
                "@reboot python src/orchestrator.py # FTE",
                "0 8 * * 1 python weekly # FTE",
            )
            captured: list[str] = []

            def posix_fake(cmd: list[str], **kwargs: Any) -> MagicMock:
                if "crontab" in cmd and "-l" in cmd:
                    return existing
                if "crontab" in cmd and "-" in cmd:
                    captured.append(kwargs.get("input", ""))
                    return MagicMock(returncode=0, stdout="", stderr="")
                return MagicMock(returncode=0, stdout="", stderr="")

            fake = posix_fake

        with patch("subprocess.run", side_effect=fake):
            result = uninstall_schedule.run(tmp_vault)

        assert isinstance(result, dict), f"run() must return dict, got {type(result)}"
        assert result.get("errors", []) == [], (
            f"Expected no errors from uninstall, got: {result.get('errors')}"
        )
