"""generate_linkedin_post skill — drafts LinkedIn posts via Claude with frequency guard."""

from __future__ import annotations

import glob
import os
from datetime import datetime, timedelta, timezone
from typing import Any

import yaml

from src.core.vault import write_frontmatter_file

_AI_HASHTAG = "#AIAssisted"
_DEFAULT_TEMPLATE = (
    "Excited to share some insights about running a modern AI-powered business. "
    "Stay tuned for more updates on productivity, automation, and growth strategies. "
    f"\n\n{_AI_HASHTAG}"
)


def _is_enabled(vault_root: str = "") -> bool:
    """Check settings.yaml to see if the skill is enabled."""
    try:
        import yaml as _yaml
        settings_path = os.path.join(os.path.dirname(vault_root) if vault_root else ".", "config", "settings.yaml")
        if not os.path.exists(settings_path):
            settings_path = "config/settings.yaml"
        with open(settings_path, encoding="utf-8") as f:
            cfg = _yaml.safe_load(f)
        return bool(cfg.get("skills", {}).get("generate_linkedin_post", {}).get("enabled", True))
    except Exception:
        return True  # default enabled when config unavailable


def _has_recent_post(vault_root: str, frequency_days: int) -> bool:
    """Return True if a linkedin_post audit entry exists within frequency_days."""
    logs_dir = os.path.join(vault_root, "Logs")
    if not os.path.isdir(logs_dir):
        return False

    cutoff = datetime.now(timezone.utc) - timedelta(days=frequency_days)
    for log_file in glob.glob(os.path.join(logs_dir, "*.md")):
        try:
            with open(log_file, encoding="utf-8") as f:
                content = f.read()
            # Quick check before full parse
            if "linkedin_post" not in content:
                continue
            parts = content.split("---")
            if len(parts) < 3:
                continue
            meta = yaml.safe_load(parts[1])
            if str(meta.get("action", "")) == "linkedin_post":
                ts_str = str(meta.get("timestamp", ""))
                if ts_str:
                    ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                    if ts >= cutoff:
                        return True
        except Exception:
            continue
    return False


def _load_prompt_template(vault_root: str) -> str:
    """Load prompt from vault/Templates/linkedin_post_prompt.md or return default."""
    prompt_path = os.path.join(vault_root, "Templates", "linkedin_post_prompt.md")
    if os.path.exists(prompt_path):
        try:
            with open(prompt_path, encoding="utf-8") as f:
                return f.read()
        except Exception:
            pass
    return (
        "Write a professional LinkedIn post (max 3000 chars) that showcases expertise "
        "in AI-powered business automation. Include practical insights, be authentic, "
        f"and end with {_AI_HASHTAG}. Make it engaging and value-driven."
    )


def _call_claude(prompt: str) -> str:
    """Call Claude API for LinkedIn post draft.

    Raises:
        Exception: If API call fails or anthropic package unavailable.
    """
    try:
        import anthropic  # type: ignore[import]
    except ImportError as exc:
        raise ImportError("anthropic package not installed") from exc

    model = os.environ.get("ANTHROPIC_PLAN_MODEL", "claude-haiku-4-5-20251001")
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    message = client.messages.create(
        model=model,
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text


def run(
    vault_root: str,
    frequency_days: int = 3,
    dev_mode: bool = True,
) -> dict[str, Any]:
    """Draft a LinkedIn post for human review and approval.

    Args:
        vault_root: Path to vault root directory.
        frequency_days: Minimum days between posts (cadence guard).
        dev_mode: If True, use template instead of Claude API.

    Returns:
        Dict with keys: processed, post_files_created, skipped_rate_limit, errors, skipped.
    """
    # Guard 1: enabled check
    if not _is_enabled(vault_root):
        return {"processed": 0, "post_files_created": 0, "skipped_rate_limit": 0, "errors": 0, "skipped": 1}

    # Guard 2: cadence check
    if _has_recent_post(vault_root, frequency_days):
        return {"processed": 0, "post_files_created": 0, "skipped_rate_limit": 1, "errors": 0, "skipped": 1}

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    use_claude = bool(api_key) and not dev_mode

    # Generate post content
    post_content = ""
    if use_claude:
        try:
            prompt = _load_prompt_template(vault_root)
            post_content = _call_claude(prompt)
        except Exception:
            post_content = ""

    # Ensure #AIAssisted is included
    if not post_content or _AI_HASHTAG not in post_content:
        post_content = (post_content or _DEFAULT_TEMPLATE)
        if _AI_HASHTAG not in post_content:
            post_content = post_content.rstrip() + f"\n\n{_AI_HASHTAG}"

    # Write plan file
    now = datetime.now(timezone.utc)
    timestamp = now.strftime("%Y%m%d_%H%M%S")
    plan_id = f"LINKEDIN_POST_{timestamp}"

    metadata: dict[str, Any] = {
        "id": plan_id,
        "type": "linkedin_post",
        "risk_level": "HIGH",
        "requires_approval": True,
        "status": "pending",
        "created": now.strftime("%Y-%m-%dT%H:%M:%S"),
        "platform": "linkedin",
        "ai_generated": use_claude,
    }

    body = f"## LinkedIn Post Draft\n\n{post_content}\n"

    try:
        write_frontmatter_file(vault_root, f"Plans/{plan_id}.md", metadata, body)
        post_files_created = 1
    except Exception:
        return {"processed": 1, "post_files_created": 0, "skipped_rate_limit": 0, "errors": 1, "skipped": 0}

    return {
        "processed": 1,
        "post_files_created": post_files_created,
        "skipped_rate_limit": 0,
        "errors": 0,
        "skipped": 0,
    }
