"""Tests for GmailWatcher — TDD Red Phase (Phase 3, T015)."""

from __future__ import annotations

import json
import os
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def vault_root(tmp_path):
    """Minimal vault structure for tests."""
    (tmp_path / "Watch" / "gmail_mock").mkdir(parents=True)
    (tmp_path / "Inbox").mkdir()
    (tmp_path / "state").mkdir()
    return str(tmp_path)


@pytest.fixture()
def sample_flat_email():
    """Flat mock schema (as stored in gmail_mock/)."""
    return {
        "id": "gmail_mock_001",
        "source": "gmail",
        "subject": "Interested in your pricing",
        "from_address": "client@example.com",
        "to_address": "owner@business.com",
        "message_id": "<abc123@mail.gmail.com>",
        "received_at": "2026-02-22T10:00:00Z",
        "thread_id": "thread_001",
        "body": "Hi, I would like to learn more about your services.",
        "type": "email",
        "priority": "HIGH",
        "filename": "gmail_mock_001.json",
        "tags": ["lead", "inquiry"],
    }


@pytest.fixture()
def real_api_message():
    """Nested payload as returned by Gmail REST API."""
    return {
        "id": "msg_real_001",
        "threadId": "thread_real_001",
        "payload": {
            "headers": [
                {"name": "Subject", "value": "Partnership Opportunity"},
                {"name": "From", "value": "partner@company.com"},
                {"name": "To", "value": "me@business.com"},
                {"name": "Message-ID", "value": "<xyz789@mail.gmail.com>"},
                {"name": "Date", "value": "Sat, 22 Feb 2026 09:30:00 +0000"},
            ],
            "parts": [
                {
                    "mimeType": "text/plain",
                    "body": {"data": "SGVsbG8sIEkgd2FudCB0byBwYXJ0bmVyLg=="},
                }
            ],
        },
    }


# ---------------------------------------------------------------------------
# T015.1  dry-run returns mock items
# ---------------------------------------------------------------------------


def test_dry_run_returns_mock_items(vault_root, sample_flat_email, tmp_path):
    """With DRY_RUN=true, check_for_updates() returns items from gmail_mock/."""
    from src.watchers.gmail_watcher import GmailWatcher

    mock_path = os.path.join(vault_root, "Watch", "gmail_mock", "email1.json")
    with open(mock_path, "w") as f:
        json.dump(sample_flat_email, f)

    with patch.dict(os.environ, {"DRY_RUN": "true"}):
        watcher = GmailWatcher(vault_root=vault_root, gmail_mock_dir=os.path.join(vault_root, "Watch", "gmail_mock"))
        items = watcher.check_for_updates()

    assert len(items) == 1
    assert items[0]["id"] == "gmail_mock_001"


# ---------------------------------------------------------------------------
# T015.2  parse flat mock schema
# ---------------------------------------------------------------------------


def test_parse_message_flat_mock_schema(vault_root, sample_flat_email):
    """_parse_message() handles flat mock dict (no 'payload' key)."""
    from src.watchers.gmail_watcher import GmailWatcher

    watcher = GmailWatcher(vault_root=vault_root)
    result = watcher._parse_message(sample_flat_email)

    assert result["id"] == "gmail_mock_001"
    assert result["source"] == "gmail"
    assert result["subject"] == "Interested in your pricing"
    assert result["from_address"] == "client@example.com"
    assert result["body"] == "Hi, I would like to learn more about your services."
    assert result["type"] == "email"


# ---------------------------------------------------------------------------
# T015.3  parse real API schema (nested payload)
# ---------------------------------------------------------------------------


def test_parse_message_real_api_schema(vault_root, real_api_message):
    """_parse_message() handles nested Gmail API payload structure."""
    from src.watchers.gmail_watcher import GmailWatcher

    watcher = GmailWatcher(vault_root=vault_root)
    result = watcher._parse_message(real_api_message)

    assert result["id"] == "msg_real_001"
    assert result["source"] == "gmail"
    assert result["subject"] == "Partnership Opportunity"
    assert result["from_address"] == "partner@company.com"
    assert result["thread_id"] == "thread_real_001"
    assert "Hello" in result["body"]  # decoded from base64


# ---------------------------------------------------------------------------
# T015.4  dedup skips already-processed IDs
# ---------------------------------------------------------------------------


def test_dedup_skips_processed_ids(vault_root, sample_flat_email, tmp_path):
    """check_for_updates() does not return items whose IDs are in _processed_ids."""
    from src.watchers.gmail_watcher import GmailWatcher

    mock_path = os.path.join(vault_root, "Watch", "gmail_mock", "email1.json")
    with open(mock_path, "w") as f:
        json.dump(sample_flat_email, f)

    with patch.dict(os.environ, {"DRY_RUN": "true"}):
        watcher = GmailWatcher(vault_root=vault_root, gmail_mock_dir=os.path.join(vault_root, "Watch", "gmail_mock"))
        watcher._processed_ids.add("gmail_mock_001")
        items = watcher.check_for_updates()

    assert items == []


# ---------------------------------------------------------------------------
# T015.5  OAuth failure returns empty list
# ---------------------------------------------------------------------------


def test_oauth_failure_returns_empty_list(vault_root):
    """If OAuth token missing and DRY_RUN=false, returns [] and logs audit entry."""
    from src.watchers.gmail_watcher import GmailWatcher

    with patch.dict(os.environ, {"DRY_RUN": "false"}, clear=False):
        watcher = GmailWatcher(vault_root=vault_root)
        # No token file — must return [] without raising
        items = watcher.check_for_updates()

    assert items == []


# ---------------------------------------------------------------------------
# T015.6  token refresh on expiry
# ---------------------------------------------------------------------------


def test_token_refresh_on_expiry(vault_root):
    """If token exists but is expired, the watcher attempts to refresh it."""
    from src.watchers.gmail_watcher import GmailWatcher

    token_path = os.path.join(vault_root, ".gmail_token.json")
    expired_token = {
        "token": "old_access_token",
        "refresh_token": "refresh_token_abc",
        "token_uri": "https://oauth2.googleapis.com/token",
        "client_id": "client_id_123",
        "client_secret": "client_secret_456",
        "expiry": "2020-01-01T00:00:00Z",
    }
    with open(token_path, "w") as f:
        json.dump(expired_token, f)

    mock_creds = MagicMock()
    mock_creds.valid = False
    mock_creds.expired = True
    mock_creds.refresh_token = "refresh_token_abc"

    with patch.dict(os.environ, {"DRY_RUN": "false"}, clear=False):
        with patch("src.watchers.gmail_watcher.Credentials.from_authorized_user_file", return_value=mock_creds):
            with patch.object(mock_creds, "refresh") as mock_refresh:
                with patch("src.watchers.gmail_watcher.build") as mock_build:
                    mock_service = MagicMock()
                    mock_build.return_value = mock_service
                    mock_service.users.return_value.messages.return_value.list.return_value.execute.return_value = {"messages": []}
                    watcher = GmailWatcher(vault_root=vault_root)
                    watcher.check_for_updates()
                    mock_refresh.assert_called_once()


# ---------------------------------------------------------------------------
# T015.7  marks message as read after processing
# ---------------------------------------------------------------------------


def test_marks_message_as_read(vault_root, real_api_message):
    """After processing a message in live mode, the watcher marks it as read."""
    from src.watchers.gmail_watcher import GmailWatcher

    token_path = os.path.join(vault_root, ".gmail_token.json")
    with open(token_path, "w") as f:
        json.dump({"token": "tok", "refresh_token": "rt", "token_uri": "https://oauth2.googleapis.com/token",
                   "client_id": "cid", "client_secret": "cs", "expiry": "2099-01-01T00:00:00Z"}, f)

    mock_creds = MagicMock()
    mock_creds.valid = True
    mock_creds.expired = False

    with patch.dict(os.environ, {"DRY_RUN": "false"}, clear=False):
        with patch("src.watchers.gmail_watcher.Credentials.from_authorized_user_file", return_value=mock_creds):
            with patch("src.watchers.gmail_watcher.build") as mock_build:
                mock_service = MagicMock()
                mock_build.return_value = mock_service
                msg_list = mock_service.users.return_value.messages.return_value
                msg_list.list.return_value.execute.return_value = {"messages": [{"id": real_api_message["id"]}]}
                msg_list.get.return_value.execute.return_value = real_api_message
                modify_mock = msg_list.modify

                watcher = GmailWatcher(vault_root=vault_root)
                watcher.check_for_updates()

                modify_mock.assert_called_once_with(
                    userId="me",
                    id=real_api_message["id"],
                    body={"removeLabelIds": ["UNREAD"]},
                )


# ---------------------------------------------------------------------------
# T015.8  dry-run uses BaseWatcher._load_mock_items
# ---------------------------------------------------------------------------


def test_uses_base_watcher_load_mock_items(vault_root, sample_flat_email):
    """GmailWatcher's dry-run path calls self._load_mock_items(), not its own logic."""
    from src.watchers.gmail_watcher import GmailWatcher

    mock_folder = os.path.join(vault_root, "Watch", "gmail_mock")
    mock_path = os.path.join(mock_folder, "email1.json")
    with open(mock_path, "w") as f:
        json.dump(sample_flat_email, f)

    with patch.dict(os.environ, {"DRY_RUN": "true"}):
        watcher = GmailWatcher(vault_root=vault_root, gmail_mock_dir=mock_folder)
        with patch.object(watcher, "_load_mock_items", wraps=watcher._load_mock_items) as spy:
            watcher.check_for_updates()
            spy.assert_called_once_with(mock_folder)
