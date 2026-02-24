# Silver Tier Watcher Interface Contracts

**Feature**: 002-silver-tier
**Date**: 2026-02-20

---

## BaseWatcher Extensions (Silver)

`src/watchers/base_watcher.py` is extended with two shared methods. All watchers inherit
these — no per-watcher duplication.

```python
class BaseWatcher:
    # Existing Bronze interface (unchanged)
    def check_for_updates(self) -> list[dict]: ...
    def _make_item_id(self, *args) -> str: ...

    # NEW: Silver additions
    @property
    def dry_run(self) -> bool:
        """
        True if DRY_RUN env var is "true" (case-insensitive) or constructor flag set.
        Default: False.
        """

    def _load_mock_items(self, mock_folder: str) -> list[dict]:
        """
        Load all *.json files from mock_folder as item dicts.
        Skips malformed files (logs warning, continues).
        Returns empty list if folder does not exist.
        """
```

---

## GmailWatcher

**File**: `src/watchers/gmail_watcher.py`
**Auth**: `vault/.gmail_token.json` (written by `gmail_auth.py`); auto-refresh via google-auth
**Dry-run**: Reads `vault/Watch/gmail_mock/*.json` when `GMAIL_CLIENT_ID` absent or `DRY_RUN=true`

```python
class GmailWatcher(BaseWatcher):
    def check_for_updates(self) -> list[dict]:
        """
        Poll Gmail inbox. Return normalized item dicts.

        Dry-run path: self._load_mock_items(gmail_mock_dir)
        Live path:
          1. Load credentials from vault/.gmail_token.json
          2. Refresh token if expired
          3. Call messages.list(userId="me", q=query, maxResults=max_results)
          4. For each message: call messages.get(), run _parse_message()
          5. Mark message as read (messages.modify, remove UNREAD label)
          6. Skip already-processed IDs (from state file)
          7. Write normalized items to vault/Inbox/
        Returns: list of normalized item dicts (empty if nothing new)

        On OAuth failure: log MEDIUM audit entry, return [] (no crash)
        """

    def _parse_message(self, raw: dict) -> dict:
        """
        Normalize Gmail API response OR flat mock to standard item dict.

        Detection: presence of "payload" key → real API response
                   absence of "payload" → flat mock schema

        Real API path: extract headers (Subject, From, To, Date) from payload.headers[];
                       extract plain text body from payload.parts[].body.data (base64)
        Mock path: direct field mapping from flat schema

        Returns standard item dict (see data-model.md InboxItem definition).
        """

    def setup_session(self):
        """
        Not applicable for Gmail (no browser session; OAuth2 uses token file).
        gmail_auth.py handles one-time credential setup.
        """
```

**State file**: `vault/state/gmail_watcher_state.json`
**Rate limit**: Max 100 Gmail API calls per hour (enforced internally)

---

## WhatsAppWatcher

**File**: `src/watchers/whatsapp_watcher.py` (DONE ✓ — 31 tests, 416 total passing)
**Auth**: Playwright persistent context at `vault/state/whatsapp_session/`
**Dry-run**: Reads `vault/Watch/whatsapp_mock/*.json` when session absent or `DRY_RUN=true`

```python
class WhatsAppWatcher(BaseWatcher):
    def check_for_updates(self) -> list[dict]:
        """
        Poll WhatsApp Web via Playwright. Return normalized item dicts.

        Dry-run: session absent or DRY_RUN=true → _load_mock_items(whatsapp_mock_dir)
        Live:
          1. launch_persistent_context(vault/state/whatsapp_session/, headless=True)
          2. Navigate to https://web.whatsapp.com
          3. Wait for [data-testid="chat-list"]
          4. If QR code detected: log warning, return [] (session expired)
          5. Query [data-testid="icon-unread-count"] to find unread chats
          6. Parse sender (line 0) + body preview (line 1) via inner_text()
          7. Filter by configured keywords; dedup by content-hash ID
        """

    def setup_session(self):
        """
        Open headful browser for QR code scan. Run once to establish session.
        """
```

**State file**: `vault/state/whatsapp_watcher_state.json`
**ToS note**: WhatsApp ToS prohibits automated use — personal productivity only

---

## LinkedInWatcher

**File**: `src/watchers/linkedin_watcher.py`
**Auth**: Playwright persistent context at `vault/state/linkedin_session/`
**Dry-run**: Reads `vault/Watch/linkedin_mock/*.json` when session absent or `DRY_RUN=true`

```python
class LinkedInWatcher(BaseWatcher):
    def check_for_updates(self) -> list[dict]:
        """
        Read LinkedIn engagement data via Playwright. Return engagement item dicts.

        Dry-run: session absent or DRY_RUN=true → _load_mock_items(linkedin_mock_dir)
        Live:
          1. launch_persistent_context(vault/state/linkedin_session/, headless=True)
          2. Navigate to https://www.linkedin.com/in/{username}/detail/recent-activity/
          3. If URL contains /login: log LOW audit entry with re-login instructions, return []
          4. Extract 5 most recent posts:
             - reactions: int from aria-label on reaction button
             - comments: int from comment count element
             - post_preview: first 200 chars of post text
             - post_url: canonical URL
             - id: SHA256 of post_url[:12]
          5. Return items with type:social_media_engagement, source:linkedin
        On Playwright exception: log LOW audit, return [] (no crash)

        username: read from settings.yaml watchers.linkedin.username
        """

    def setup_session(self):
        """
        Open headful browser for manual LinkedIn login. Run once to establish session.
        Session persisted to vault/state/linkedin_session/ (gitignored).
        """
```

**State file**: None (LinkedIn items use SHA256 of post_url for dedup; no persistent ID list)
**Poll interval**: 3600s (1 hour) — engagement data changes slowly

---

## FilesystemWatcher

**File**: `src/watchers/filesystem_watcher.py` (Bronze — unchanged)
**Poll interval**: 5s
**Dry-run**: Not applicable (reads local filesystem; always works without credentials)

---

## gmail_auth.py

**File**: `src/watchers/gmail_auth.py`
**Purpose**: One-time OAuth2 setup. Run manually: `python src/watchers/gmail_auth.py`

```python
def main():
    """
    Launch OAuth2 InstalledAppFlow. Writes vault/.gmail_token.json on success.

    Uses GMAIL_CLIENT_ID and GMAIL_CLIENT_SECRET from .env.
    Opens browser for consent screen (or prints auth URL for headless).
    Scopes: ["https://www.googleapis.com/auth/gmail.modify"]
    """
```

---

## Orchestrator Watcher Registration Contract

`src/orchestrator.py` `_init_watchers()` must:

```python
def _init_watchers(self):
    watchers = [
        (GmailWatcher(self.settings, self.vault_root), "gmail_watcher"),
        (WhatsAppWatcher(self.settings, self.vault_root), "whatsapp_watcher"),
        (LinkedInWatcher(self.settings, self.vault_root), "linkedin_watcher"),
        (FilesystemWatcher(self.settings, self.vault_root), "filesystem_watcher"),
    ]
    for watcher, name in watchers:
        t = threading.Thread(
            target=self._watcher_loop,
            args=(watcher, name),
            daemon=True,
            name=f"watcher-{name}"
        )
        t.start()
```

Each watcher thread writes to `self._watcher_health` dict (protected by `threading.Lock`):

```python
self._watcher_health[name] = {
    "last_poll": datetime.utcnow().isoformat(),
    "items_this_cycle": len(items),
    "status": "OK",  # or "ERROR"
}
```

`update_dashboard.py` reads `orchestrator._watcher_health` (passed as parameter or singleton).
