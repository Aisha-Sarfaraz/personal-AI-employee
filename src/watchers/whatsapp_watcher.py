"""WhatsApp Watcher — Playwright-based WhatsApp Web automation.

NOTE: This uses WhatsApp Web browser automation. WhatsApp's Terms of Service
prohibit automated/non-human use. Use only for personal productivity with
your own account and at your own discretion.

Authentication: persistent browser session stored in vault/state/whatsapp_session/.
First run opens a browser window for QR code scan; subsequent runs are headless.
"""

import hashlib
import os
import re
import time
from typing import Any

from src.watchers.base_watcher import BaseWatcher

_WHATSAPP_URL = "https://web.whatsapp.com"
_CHAT_LIST_SELECTOR = '[data-testid="chat-list"]'
_UNREAD_SELECTOR = '[data-testid="icon-unread-count"]'
_QR_SELECTOR = '[data-testid="qrcode"]'
_CHAT_CELL_SELECTOR = '[data-testid="cell-frame-container"]'

_DEFAULT_KEYWORDS = [
    "urgent", "asap", "invoice", "payment", "help",
    "quote", "price", "pricing", "interested", "contract",
]

_PRIORITY_KEYWORDS = {"urgent", "asap", "emergency", "critical"}


class WhatsAppWatcher(BaseWatcher):
    """WhatsApp Web watcher using Playwright persistent browser session.

    Reads unread messages matching configured keywords and converts them
    to vault Inbox items. Deduplicates via sender+content hash so the
    same message is never ingested twice.

    Dry-run mode (DRY_RUN=true or session absent): reads from
    vault/Watch/whatsapp_mock/*.json without touching WhatsApp Web.
    """

    def __init__(
        self,
        vault_root: str,
        poll_interval: int = 120,
        session_path: str | None = None,
        keywords: list[str] | None = None,
        dry_run: bool = False,
    ) -> None:
        super().__init__("whatsapp_watcher", vault_root, poll_interval)
        self._session_path = session_path or os.path.join(
            vault_root, "state", "whatsapp_session"
        )
        # Use `is not None` so callers can pass `[]` to allow all messages.
        self.keywords: list[str] = keywords if keywords is not None else list(_DEFAULT_KEYWORDS)
        self._dry_run_flag = dry_run

    # ------------------------------------------------------------------ #
    # Public interface                                                      #
    # ------------------------------------------------------------------ #

    @property
    def dry_run(self) -> bool:
        return self._dry_run_flag or os.environ.get("DRY_RUN", "false").lower() == "true"

    def check_for_updates(self) -> list[dict[str, Any]]:
        """Return new unread WhatsApp items matching keywords.

        Falls back to mock mode when:
        - DRY_RUN=true environment variable is set, OR
        - dry_run=True constructor argument, OR
        - session directory does not exist (first-time setup not completed).
        """
        if self.dry_run or not os.path.exists(self._session_path):
            mock_dir = os.path.join(self.vault_root, "Watch", "whatsapp_mock")
            raw_items = self._load_mock_items(mock_dir)
            return self._process_raw_items(raw_items)

        try:
            return self._scrape_whatsapp_web()
        except Exception as exc:
            # Degrade gracefully — never crash the orchestrator
            self._log_warning(f"WhatsApp Web scrape failed: {exc}")
            return []

    # ------------------------------------------------------------------ #
    # First-run setup                                                       #
    # ------------------------------------------------------------------ #

    def setup_session(self) -> None:
        """Open a visible browser for the user to scan the QR code.

        Call this once before using the watcher in headless mode.
        Blocks until WhatsApp Web is fully loaded (QR scanned).
        """
        try:
            from playwright.sync_api import sync_playwright  # type: ignore[import]
        except ImportError:
            raise ImportError(
                "playwright is not installed. Run: pip install playwright && "
                "playwright install chromium"
            )

        os.makedirs(self._session_path, exist_ok=True)
        print(
            "\n[whatsapp_watcher] Opening browser for WhatsApp QR code scan...\n"
            "Scan the QR code on your phone to link this device.\n"
            "The browser will stay open until you are logged in.\n"
        )
        with sync_playwright() as p:
            ctx = p.chromium.launch_persistent_context(
                self._session_path,
                headless=False,
                viewport={"width": 1280, "height": 900},
            )
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            page.goto(_WHATSAPP_URL, wait_until="networkidle", timeout=60_000)
            # Wait for QR to disappear (= logged in)
            page.wait_for_selector(
                f":not({_QR_SELECTOR})",
                timeout=120_000,
            )
            # Wait for chat list to confirm login
            page.wait_for_selector(_CHAT_LIST_SELECTOR, timeout=30_000)
            print("[whatsapp_watcher] Session saved. You can now run in headless mode.")
            ctx.close()

    # ------------------------------------------------------------------ #
    # WhatsApp Web scraping                                                 #
    # ------------------------------------------------------------------ #

    def _scrape_whatsapp_web(self) -> list[dict[str, Any]]:
        try:
            from playwright.sync_api import sync_playwright  # type: ignore[import]
        except ImportError:
            raise ImportError(
                "playwright is not installed. Run: pip install playwright && "
                "playwright install chromium"
            )

        items: list[dict[str, Any]] = []

        with sync_playwright() as p:
            ctx = p.chromium.launch_persistent_context(
                self._session_path,
                headless=True,
                viewport={"width": 1280, "height": 900},
            )
            try:
                page = ctx.pages[0] if ctx.pages else ctx.new_page()
                page.goto(_WHATSAPP_URL, wait_until="networkidle", timeout=30_000)

                # Session expired → QR code visible
                if page.query_selector(_QR_SELECTOR):
                    self._log_warning(
                        "WhatsApp session expired. Re-run setup_session() to scan QR code."
                    )
                    return []

                # Wait for chat list
                try:
                    page.wait_for_selector(_CHAT_LIST_SELECTOR, timeout=15_000)
                except Exception:
                    self._log_warning("Chat list not found — WhatsApp Web may not be loaded.")
                    return []

                # Find all chat cells that contain an unread badge
                chat_cells = page.query_selector_all(_CHAT_CELL_SELECTOR)
                for cell in chat_cells:
                    try:
                        if not cell.query_selector(_UNREAD_SELECTOR):
                            continue
                        item = self._extract_item_from_cell(cell)
                        if item:
                            items.append(item)
                    except Exception:
                        continue  # skip malformed cells

            finally:
                ctx.close()

        return items

    def _extract_item_from_cell(self, cell: Any) -> dict[str, Any] | None:
        """Parse a WhatsApp Web chat cell into a vault item dict."""
        raw_text = (cell.inner_text() or "").strip()
        lines = [ln.strip() for ln in raw_text.splitlines() if ln.strip()]

        if len(lines) < 2:
            return None

        sender = lines[0]
        # Message preview is typically lines[1]; lines[-1] may be time or unread count
        body = lines[1] if len(lines) > 1 else ""

        # Apply keyword filter
        text_lower = f"{sender} {body}".lower()
        if self.keywords and not any(kw.lower() in text_lower for kw in self.keywords):
            return None

        msg_id = self._make_message_id(sender, body)
        if self.is_processed(msg_id):
            return None

        priority = (
            "HIGH"
            if any(kw in text_lower for kw in _PRIORITY_KEYWORDS)
            else "MEDIUM"
        )

        return {
            "id": msg_id,
            "source": "whatsapp",
            "from_number": sender,
            "to_number": "self",
            "body": f"**From:** {sender}\n\n{body}",
            "type": "general",
            "priority": priority,
            "filename": f"{msg_id}.md",
            "tags": [],
        }

    # ------------------------------------------------------------------ #
    # Dry-run / mock mode                                                   #
    # ------------------------------------------------------------------ #

    def _process_raw_items(self, raw_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Normalize raw JSON dicts into WhatsApp vault items, applying keyword filter and dedup.

        Expected raw schema (subset of Twilio-compatible or custom):
        {
            "MessageSid": "SM...",   // or omit for auto-ID
            "From": "+1234567890",
            "Body": "message text"
        }
        """
        items: list[dict[str, Any]] = []
        for data in raw_items:
            sender = data.get("From", data.get("from_number", "mock_sender"))
            body = data.get("Body", data.get("body", ""))
            sid = data.get("MessageSid", data.get("message_sid", ""))
            msg_id = f"WA_{sid}" if sid else self._make_message_id(sender, body)

            if self.is_processed(msg_id):
                continue

            text_lower = f"{sender} {body}".lower()
            if self.keywords and not any(kw.lower() in text_lower for kw in self.keywords):
                continue

            priority = (
                "HIGH"
                if any(kw in text_lower for kw in _PRIORITY_KEYWORDS)
                else "MEDIUM"
            )

            self._processed_ids.add(msg_id)  # mark before return so next scan skips
            items.append({
                "id": msg_id,
                "source": "whatsapp",
                "from_number": sender,
                "to_number": data.get("To", data.get("to_number", "self")),
                "body": f"**From:** {sender}\n\n{body}",
                "type": "general",
                "priority": priority,
                "filename": f"{msg_id}.md",
                "tags": [],
            })

        return items

    # ------------------------------------------------------------------ #
    # Helpers                                                               #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _make_message_id(sender: str, body: str) -> str:
        """Stable ID from sender + body content (ignores time).

        Two messages with identical sender+body = same ID = deduplicated.
        Different body from same sender = different ID = new item.
        """
        sender_norm = re.sub(r"\W+", "_", sender.lower())[:20].strip("_")
        body_hash = hashlib.sha256(body.encode("utf-8")).hexdigest()[:10]
        return f"WA_{sender_norm}_{body_hash}"

    def _log_warning(self, msg: str) -> None:
        """Print a timestamped warning (no hard dependency on audit_logger)."""
        ts = time.strftime("%Y-%m-%dT%H:%M:%S")
        print(f"[{ts}] [whatsapp_watcher] WARNING: {msg}")
