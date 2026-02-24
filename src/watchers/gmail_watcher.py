"""GmailWatcher — monitors Gmail inbox for new unread messages."""

from __future__ import annotations

import base64
import os
from typing import Any

from src.core.audit_logger import log_action
from src.watchers.base_watcher import BaseWatcher

# Optional imports — gracefully absent when google libs not installed
try:
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    _GOOGLE_LIBS_AVAILABLE = True
except ImportError:  # pragma: no cover
    _GOOGLE_LIBS_AVAILABLE = False
    Credentials = None  # type: ignore[assignment,misc]
    build = None  # type: ignore[assignment]


class GmailWatcher(BaseWatcher):
    """Polls Gmail inbox for unread messages; supports dry-run mock mode."""

    def __init__(
        self,
        name: str = "gmail_watcher",
        vault_root: str = "",
        poll_interval: int = 120,
        gmail_mock_dir: str = "",
    ) -> None:
        super().__init__(name=name, vault_root=vault_root, poll_interval=poll_interval)
        self.gmail_mock_dir = gmail_mock_dir or os.path.join(vault_root, "Watch", "gmail_mock")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def check_for_updates(self) -> list[dict[str, Any]]:
        """Return new unread messages; dedup against _processed_ids."""
        if self.dry_run:
            raw_items = self._load_mock_items(self.gmail_mock_dir)
            return [item for item in raw_items if item.get("id") and item["id"] not in self._processed_ids]

        return self._fetch_live()

    # ------------------------------------------------------------------
    # Internal: live Gmail API path
    # ------------------------------------------------------------------

    def _fetch_live(self) -> list[dict[str, Any]]:
        """Fetch unread messages from Gmail API."""
        if not _GOOGLE_LIBS_AVAILABLE:
            log_action(
                vault_root=self.vault_root,
                agent="gmail_watcher",
                action="gmail_api_unavailable",
                risk_tier="MEDIUM",
                status="warning",
                details="google-api-python-client not installed",
            )
            return []

        creds = self._load_credentials()
        if creds is None:
            log_action(
                vault_root=self.vault_root,
                agent="gmail_watcher",
                action="oauth_failure",
                risk_tier="MEDIUM",
                status="error",
                details="credentials unavailable",
            )
            return []

        try:
            service = build("gmail", "v1", credentials=creds)
            result = (
                service.users()
                .messages()
                .list(userId="me", labelIds=["UNREAD"], maxResults=50)
                .execute()
            )
            messages = result.get("messages", [])
        except Exception as exc:
            log_action(
                vault_root=self.vault_root,
                agent="gmail_watcher",
                action="gmail_list_error",
                risk_tier="MEDIUM",
                status="error",
                details=str(exc),
            )
            return []

        items: list[dict[str, Any]] = []
        for msg_ref in messages:
            msg_id = msg_ref["id"]
            if msg_id in self._processed_ids:
                continue
            try:
                raw = service.users().messages().get(userId="me", id=msg_id, format="full").execute()
                item = self._parse_message(raw)
                # Mark as read
                service.users().messages().modify(
                    userId="me",
                    id=msg_id,
                    body={"removeLabelIds": ["UNREAD"]},
                ).execute()
                items.append(item)
            except Exception:
                pass  # skip individual message errors

        return items

    def _load_credentials(self):
        """Load credentials via gmail_auth module."""
        try:
            from src.watchers.gmail_auth import get_credentials
            return get_credentials(self.vault_root)
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Internal: message parsing
    # ------------------------------------------------------------------

    def _parse_message(self, raw: dict[str, Any]) -> dict[str, Any]:
        """Normalize raw message to InboxItem dict.

        Handles two formats:
        - Flat mock: dict with top-level 'source', 'subject', 'body', etc.
        - Real API: dict with 'payload.headers' + 'payload.parts'
        """
        # Flat mock schema — no 'payload' key
        if "payload" not in raw:
            return self._parse_flat(raw)

        return self._parse_api(raw)

    def _parse_flat(self, raw: dict[str, Any]) -> dict[str, Any]:
        """Return flat mock dict as-is (already normalized)."""
        item = dict(raw)
        item.setdefault("source", "gmail")
        item.setdefault("type", "email")
        item.setdefault("priority", "MEDIUM")
        item.setdefault("tags", [])
        return item

    def _parse_api(self, raw: dict[str, Any]) -> dict[str, Any]:
        """Parse nested Gmail REST API payload into normalized InboxItem."""
        payload = raw.get("payload", {})
        headers = {h["name"]: h["value"] for h in payload.get("headers", [])}

        subject = headers.get("Subject", "(no subject)")
        from_addr = headers.get("From", "")
        to_addr = headers.get("To", "")
        message_id = headers.get("Message-ID", "")
        date_str = headers.get("Date", "")

        body = self._extract_body(payload)
        priority = self._infer_priority(subject, body)
        tags = self._infer_tags(subject, body)

        return {
            "id": raw["id"],
            "source": "gmail",
            "subject": subject,
            "from_address": from_addr,
            "to_address": to_addr,
            "message_id": message_id,
            "received_at": date_str,
            "thread_id": raw.get("threadId", ""),
            "body": body,
            "type": "email",
            "priority": priority,
            "filename": f"{raw['id']}.md",
            "tags": tags,
        }

    def _extract_body(self, payload: dict[str, Any]) -> str:
        """Extract plain text body from payload, decoding base64."""
        # Single-part message
        body_data = payload.get("body", {}).get("data", "")
        if body_data:
            return self._decode_b64(body_data)

        # Multi-part: find text/plain part
        for part in payload.get("parts", []):
            if part.get("mimeType") == "text/plain":
                data = part.get("body", {}).get("data", "")
                if data:
                    return self._decode_b64(data)
            # Nested parts
            nested = part.get("parts", [])
            for sub in nested:
                if sub.get("mimeType") == "text/plain":
                    data = sub.get("body", {}).get("data", "")
                    if data:
                        return self._decode_b64(data)

        return ""

    @staticmethod
    def _decode_b64(data: str) -> str:
        """Decode URL-safe base64 Gmail body data."""
        try:
            padded = data + "=" * (4 - len(data) % 4)
            return base64.urlsafe_b64decode(padded).decode("utf-8", errors="replace")
        except Exception:
            return ""

    @staticmethod
    def _infer_priority(subject: str, body: str) -> str:
        text = (subject + " " + body).lower()
        if any(k in text for k in ("lead", "buy", "purchase", "contract")):
            return "CRITICAL"
        if any(k in text for k in ("urgent", "asap", "inquiry", "interested")):
            return "HIGH"
        return "MEDIUM"

    @staticmethod
    def _infer_tags(subject: str, body: str) -> list[str]:
        text = (subject + " " + body).lower()
        tags: list[str] = []
        if any(k in text for k in ("lead", "buy", "purchase")):
            tags.append("lead")
        if any(k in text for k in ("inquiry", "interested", "question")):
            tags.append("inquiry")
        return tags
