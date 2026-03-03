"""post_twitter skill — draft tweet, HITL gate, publish on approval via OAuth 1.0a."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

import yaml

try:
    import tweepy  # type: ignore[import]
except ImportError:  # pragma: no cover
    tweepy = None  # type: ignore[assignment]

from src.core import rate_limiter
from src.core.audit_logger import log
from src.core.retry_handler import ErrorCategory
from src.core.vault import write_frontmatter_file

_MAX_TWEET_CHARS = 280
_DEFAULT_TEMPLATE = (
    "Excited to share insights on AI-powered business automation. "
    "Stay tuned for more updates! #AIAssisted #BusinessGrowth"
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


# ---------------------------------------------------------------------------
# Tweet helpers
# ---------------------------------------------------------------------------


def _enforce_tweet_limit(text: str) -> str:
    """Enforce 280-character limit; truncate at 277 + '...' if over."""
    if len(text) <= _MAX_TWEET_CHARS:
        return text
    return text[:277] + "..."


def _draft_tweet(vault_root: str) -> str:
    """Draft tweet text using Claude API or template fallback."""
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return _enforce_tweet_limit(_DEFAULT_TEMPLATE)

    try:
        import anthropic  # type: ignore[import]
        client = anthropic.Anthropic(api_key=api_key)
        model = os.environ.get("ANTHROPIC_PLAN_MODEL", "claude-haiku-4-5-20251001")
        msg = client.messages.create(
            model=model,
            max_tokens=128,
            messages=[
                {
                    "role": "user",
                    "content": (
                        "Write a tweet (max 260 chars) showcasing AI-powered business insights. "
                        "Include #AIAssisted. Be concise and engaging."
                    ),
                }
            ],
        )
        text = msg.content[0].text
        return _enforce_tweet_limit(text)
    except Exception:
        return _enforce_tweet_limit(_DEFAULT_TEMPLATE)


# ---------------------------------------------------------------------------
# Error helpers
# ---------------------------------------------------------------------------


def _handle_auth_error(vault_root: str, error_detail: str) -> None:
    """Create TWITTER_AUTH_ALERT in vault/Inbox/."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    filename = f"TWITTER_AUTH_ALERT_{ts}.md"
    metadata = {
        "type": "auth_alert",
        "source": "twitter_api",
        "error": error_detail,
        "risk_level": "CRITICAL",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    body = f"# Twitter API Authentication Error\n\n{error_detail}\n\nTwitter watcher has been paused."
    write_frontmatter_file(vault_root, f"Inbox/{filename}", metadata, body)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def run(vault_root: str, dev_mode: bool = True) -> dict[str, Any]:
    """Draft a tweet, gate on HITL, publish on approval.

    Returns:
        {"created": 1, "approval_file": "<path>"}   — approval file written
        {"skipped": 1, "reason": "rate_limit"}        — rate limit exceeded
        {"skipped": 1, "reason": "disabled"}          — twitter.enabled = false
    """
    settings = _load_settings()
    tw_settings = settings.get("twitter", {})

    # Guard 1: enabled check
    if not tw_settings.get("enabled", False):
        return {"skipped": 1, "reason": "disabled"}

    # Guard 2: rate limit check (1 tweet per hour window)
    if not rate_limiter.check_and_increment(vault_root, "post_tweet", limit_per_hour=1):
        return {"skipped": 1, "reason": "rate_limit"}

    # Draft tweet
    draft_text = _draft_tweet(vault_root)
    draft_text = _enforce_tweet_limit(draft_text)

    # Write approval file
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"TWEET_{ts}.md"
    approval_path = os.path.join(vault_root, "Pending_Approval", filename)

    metadata: dict[str, Any] = {
        "type": "social_post_approval",
        "platforms": ["twitter"],
        "draft_text": draft_text,
        "character_count": len(draft_text),
        "risk_level": "HIGH",
        "requires_approval": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    body = (
        f"# Tweet Approval\n\n"
        f"{draft_text}\n\n"
        f"Character count: {len(draft_text)}/280\n\n"
        f"Move this file to vault/Approved/ to publish.\n"
    )

    os.makedirs(os.path.dirname(approval_path), exist_ok=True)
    write_frontmatter_file(vault_root, f"Pending_Approval/{filename}", metadata, body)

    # Audit log
    try:
        log(
            vault_root=vault_root,
            action_type="post_tweet",
            actor="post_twitter",
            target="twitter",
            parameters={"character_count": len(draft_text), "dev_mode": dev_mode},
            approval_status="pending",
            approved_by=None,
            result="success",
        )
    except Exception:
        pass

    return {"created": 1, "approval_file": approval_path}
