"""Gmail OAuth2 authentication helper."""

from __future__ import annotations

import json
import os

SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]


def get_credentials(vault_root: str):
    """Return valid Gmail OAuth2 credentials, refreshing or re-authorizing as needed.

    Args:
        vault_root: Path to vault root directory.

    Returns:
        google.oauth2.credentials.Credentials, or None on failure.
    """
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError:
        return None

    token_path = os.path.join(vault_root, ".gmail_token.json")
    creds = None

    if os.path.exists(token_path):
        try:
            creds = Credentials.from_authorized_user_file(token_path, SCOPES)
        except Exception:
            creds = None

    if creds and creds.valid:
        return creds

    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            _save_token(token_path, creds)
            return creds
        except Exception:
            return None

    # First-time flow — requires interactive console or client secrets file
    client_id = os.environ.get("GMAIL_CLIENT_ID", "")
    client_secret = os.environ.get("GMAIL_CLIENT_SECRET", "")
    if not client_id or not client_secret:
        return None

    client_config = {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob", "http://localhost"],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }

    try:
        flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
        creds = flow.run_local_server(port=0)
        _save_token(token_path, creds)
        return creds
    except Exception:
        return None


def _save_token(token_path: str, creds) -> None:
    """Persist credentials to disk."""
    try:
        os.makedirs(os.path.dirname(token_path), exist_ok=True)
        with open(token_path, "w", encoding="utf-8") as f:
            f.write(creds.to_json())
    except Exception:
        pass
