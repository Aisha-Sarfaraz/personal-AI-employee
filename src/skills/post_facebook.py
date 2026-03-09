"""post_facebook skill — draft Facebook + Instagram cross-post, HITL gate, publish on approval."""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any

import yaml

try:
    import requests as _requests
except ImportError:  # pragma: no cover
    _requests = None  # type: ignore[assignment]

from src.core.audit_logger import log
from src.core.retry_handler import ErrorCategory, with_retry
from src.core.vault import write_frontmatter_file

_DEFAULT_TEMPLATE = (
    "Excited to share some insights about running a modern AI-powered business. "
    "Stay tuned for more updates on productivity, automation, and growth strategies. "
    "#AIAssisted #BusinessAutomation"
)


# ---------------------------------------------------------------------------
# Settings helpers
# ---------------------------------------------------------------------------


def _load_settings() -> dict[str, Any]:
    """Load settings.yaml from config/ directory."""
    candidates = [
        os.path.join(os.path.dirname(__file__), "..", "..", "config", "settings.yaml"),
        "config/settings.yaml",
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                with open(path, encoding="utf-8") as f:
                    return yaml.safe_load(f) or {}
            except Exception:
                pass
    return {}


def _posted_within_days(vault_root: str, action_type: str, frequency_days: int) -> bool:
    """Return True if a post with given action_type was made within frequency_days."""
    logs_dir = os.path.join(vault_root, "Logs")
    if not os.path.isdir(logs_dir):
        return False

    cutoff = datetime.now(timezone.utc) - timedelta(days=frequency_days)

    for fname in os.listdir(logs_dir):
        if not fname.endswith(".json"):
            continue
        fpath = os.path.join(logs_dir, fname)
        try:
            with open(fpath, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                        if entry.get("action_type") == action_type:
                            ts_str = entry.get("timestamp", "")
                            if ts_str:
                                ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                                if ts >= cutoff:
                                    return True
                    except Exception:
                        continue
        except Exception:
            continue

    return False


# ---------------------------------------------------------------------------
# Draft helpers
# ---------------------------------------------------------------------------


def _draft_post(vault_root: str) -> str:
    """Draft post text using Claude API or template fallback."""
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return _DEFAULT_TEMPLATE

    try:
        import anthropic  # type: ignore[import]
        client = anthropic.Anthropic(api_key=api_key)
        model = os.environ.get("ANTHROPIC_PLAN_MODEL", "claude-haiku-4-5-20251001")
        msg = client.messages.create(
            model=model,
            max_tokens=512,
            messages=[
                {
                    "role": "user",
                    "content": (
                        "Write a professional Facebook + Instagram post (max 1000 chars) "
                        "showcasing AI-powered business insights. Include #AIAssisted hashtag."
                    ),
                }
            ],
        )
        return msg.content[0].text
    except Exception:
        return _DEFAULT_TEMPLATE


# ---------------------------------------------------------------------------
# Error helpers
# ---------------------------------------------------------------------------


def _handle_auth_error(vault_root: str, error_detail: str) -> None:
    """Create META_AUTH_ALERT in vault/Inbox/."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    filename = f"META_AUTH_ALERT_{ts}.md"
    metadata = {
        "type": "auth_alert",
        "source": "meta_api",
        "error": error_detail,
        "risk_level": "CRITICAL",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    body = f"# Meta API Authentication Error\n\n{error_detail}\n\nFacebook/Instagram watcher has been paused."
    write_frontmatter_file(vault_root, f"Inbox/{filename}", metadata, body)


# ---------------------------------------------------------------------------
# Live publishing (called on approval)
# ---------------------------------------------------------------------------


@with_retry(max_attempts=3, base_delay=1.0, max_delay=60.0)
def _publish_facebook(text: str, page_id: str, token: str) -> dict[str, Any]:
    """POST to Facebook Page feed."""
    resp = _requests.post(
        f"https://graph.facebook.com/v20.0/{page_id}/feed",
        json={"message": text, "access_token": token},
        timeout=15,
    )
    if resp.status_code in (401, 403):
        err = PermissionError(f"Meta auth error {resp.status_code}")
        err.error_category = ErrorCategory.AUTH  # type: ignore[attr-defined]
        raise err
    resp.raise_for_status()
    return resp.json()


@with_retry(max_attempts=3, base_delay=1.0, max_delay=60.0)
def _publish_instagram(text: str, ig_user_id: str, token: str) -> dict[str, Any]:
    """Two-step Instagram publish: create media container, then publish."""
    # Step 1: create container
    resp1 = _requests.post(
        f"https://graph.facebook.com/v20.0/{ig_user_id}/media",
        json={"caption": text, "access_token": token},
        timeout=15,
    )
    if resp1.status_code in (401, 403):
        err = PermissionError(f"Meta auth error {resp1.status_code}")
        err.error_category = ErrorCategory.AUTH  # type: ignore[attr-defined]
        raise err
    resp1.raise_for_status()
    creation_id = resp1.json().get("id")

    # Step 2: publish
    resp2 = _requests.post(
        f"https://graph.facebook.com/v20.0/{ig_user_id}/media_publish",
        json={"creation_id": creation_id, "access_token": token},
        timeout=15,
    )
    resp2.raise_for_status()
    return resp2.json()


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def run(vault_root: str, dev_mode: bool = True) -> dict[str, Any]:
    """Draft a Facebook + Instagram cross-post, gate on HITL, publish on approval.

    Returns:
        {"created": 1, "approval_file": "<path>"}   — approval file written
        {"skipped": 1, "reason": "too_soon"}          — posted within frequency_days
        {"skipped": 1, "reason": "disabled"}          — facebook.enabled = false
    """
    settings = _load_settings()
    fb_settings = settings.get("facebook", {})

    # Guard 1: enabled check
    if not fb_settings.get("enabled", False):
        return {"skipped": 1, "reason": "disabled"}

    # Guard 2: frequency check
    frequency_days = fb_settings.get("frequency_days", 3)
    if _posted_within_days(vault_root, "post_facebook", frequency_days):
        return {"skipped": 1, "reason": "too_soon"}

    # Draft post
    draft_text = _draft_post(vault_root)

    # Write approval file
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"FB_POST_{ts}.md"
    approval_path = os.path.join(vault_root, "Pending_Approval", filename)

    metadata: dict[str, Any] = {
        "type": "social_post_approval",
        "platforms": ["facebook", "instagram"],
        "draft_text": draft_text,
        "character_count": len(draft_text),
        "risk_level": "HIGH",
        "requires_approval": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    body = (
        f"# Facebook + Instagram Post Approval\n\n"
        f"{draft_text}\n\n"
        f"Move this file to vault/Approved/ to publish.\n"
    )

    os.makedirs(os.path.dirname(approval_path), exist_ok=True)
    write_frontmatter_file(vault_root, f"Pending_Approval/{filename}", metadata, body)

    # Audit log
    try:
        log(
            vault_root=vault_root,
            action_type="post_facebook",
            actor="post_facebook",
            target="facebook",
            parameters={"character_count": len(draft_text), "dev_mode": dev_mode},
            approval_status="pending",
            approved_by=None,
            result="success",
        )
    except Exception:
        pass

    return {"created": 1, "approval_file": approval_path}
