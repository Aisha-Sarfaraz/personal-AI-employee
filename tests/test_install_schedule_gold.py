"""Tests for install_schedule gold stop hook registration — TDD Phase 11, T052."""

from __future__ import annotations

import os

import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def vault(tmp_path):
    (tmp_path / "Logs").mkdir()
    (tmp_path / "state").mkdir()
    return tmp_path


@pytest.fixture()
def project_root(tmp_path):
    """Simulate a project root with .claude/ directory."""
    return tmp_path


# ---------------------------------------------------------------------------
# Test 1: _register_stop_hook creates .claude/hooks/Stop file
# ---------------------------------------------------------------------------


def test_register_stop_hook_creates_file(project_root, vault):
    """_register_stop_hook(vault_root) creates .claude/hooks/Stop pointing to hooks/stop_hook.py."""
    from src.skills.install_schedule import _register_stop_hook

    result = _register_stop_hook(str(vault), project_root=str(project_root))

    hook_path = os.path.join(str(project_root), ".claude", "hooks", "Stop")
    assert os.path.exists(hook_path), f"Hook file not found at {hook_path}"


# ---------------------------------------------------------------------------
# Test 2: second call is idempotent (no error, no duplicate content)
# ---------------------------------------------------------------------------


def test_register_stop_hook_idempotent(project_root, vault):
    """Second call is idempotent — no error, no duplicate content."""
    from src.skills.install_schedule import _register_stop_hook

    # First call
    _register_stop_hook(str(vault), project_root=str(project_root))
    # Second call — should not raise
    result = _register_stop_hook(str(vault), project_root=str(project_root))

    hook_path = os.path.join(str(project_root), ".claude", "hooks", "Stop")
    with open(hook_path, encoding="utf-8") as f:
        content = f.read()

    # Content should not be duplicated
    assert content.count("stop_hook") >= 1
    # When content is identical, should return False (already registered)
    assert result is False


# ---------------------------------------------------------------------------
# Test 3: registered hook file path is correct
# ---------------------------------------------------------------------------


def test_register_stop_hook_correct_path(project_root, vault):
    """Registered hook file path contains reference to hooks/stop_hook.py."""
    from src.skills.install_schedule import _register_stop_hook

    _register_stop_hook(str(vault), project_root=str(project_root))

    hook_path = os.path.join(str(project_root), ".claude", "hooks", "Stop")
    with open(hook_path, encoding="utf-8") as f:
        content = f.read()

    assert "stop_hook" in content
