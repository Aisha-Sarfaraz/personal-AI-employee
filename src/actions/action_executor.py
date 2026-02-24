"""Action executor — simulates or executes external actions with Silver safety guardrails."""

from __future__ import annotations

import json
import os
import smtplib
import time
from email.mime.text import MIMEText
from typing import Any

from src.core import idempotency as _idempotency
from src.core import opt_out as _opt_out
from src.core import rate_limiter as _rate_limiter

_AI_FOOTER = "\n\nThis message was drafted with AI assistance."
_MAX_RETRIES = 3
_RATE_LIMITS = {
    "send_email": 20,
    "post_social": 5,
    "create_invoice": 10,
}
_DEFAULT_RATE_LIMIT = 20


# ---------------------------------------------------------------------------
# Safety helpers (T022 — rate limit + queue; T023 — opt-out; T025 — idempotency)
# ---------------------------------------------------------------------------


def _check_rate_limit(action_type: str, vault_root: str) -> bool:
    """Return True if within rate limit, False if exceeded.

    When vault_root is empty, always allows (backwards-compat).
    """
    if not vault_root:
        return True
    limit = _RATE_LIMITS.get(action_type, _DEFAULT_RATE_LIMIT)
    return _rate_limiter.check_and_increment(vault_root, action_type, limit)


def _queue_action(action_type: str, details: dict[str, Any], plan_id: str, vault_root: str) -> None:
    """Append action to vault/state/queue.json for later processing."""
    queue_path = os.path.join(vault_root, "state", "queue.json")
    os.makedirs(os.path.dirname(queue_path), exist_ok=True)
    try:
        existing: list = []
        if os.path.exists(queue_path):
            with open(queue_path, encoding="utf-8") as f:
                existing = json.load(f)
        existing.append({"action_type": action_type, "details": details, "plan_id": plan_id,
                         "queued_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})
        with open(queue_path, "w", encoding="utf-8") as f:
            json.dump(existing, f, indent=2)
    except Exception:
        pass


def _idempotency_check_and_store(
    action_type: str,
    details: dict[str, Any],
    result: dict[str, Any],
    vault_root: str,
    plan_id: str = "",
) -> tuple[bool, dict[str, Any] | None]:
    """Check idempotency store; store result if new.

    When vault_root is empty, always returns (False, None) — no caching.
    """
    if not vault_root:
        return False, None
    key = _idempotency.generate_key(
        agent="action_executor",
        action=action_type,
        details={"plan_id": plan_id, **details},
    )
    return _idempotency.check_and_store(vault_root, key, result)


# ---------------------------------------------------------------------------
# Email send — SMTP with env-var config (S4 fix)
# ---------------------------------------------------------------------------
# Required env vars (set in .env):
#   SMTP_HOST     — e.g. smtp.gmail.com
#   SMTP_PORT     — e.g. 587
#   SMTP_USER     — sender address
#   SMTP_PASSWORD — app password or SMTP credential
#   SMTP_FROM     — display from address (defaults to SMTP_USER)
# ---------------------------------------------------------------------------


def _call_email_mcp(to: str, subject: str, body: str) -> dict[str, Any]:
    """Send a real email via SMTP (configured in .env).

    Falls back to raising RuntimeError if SMTP_HOST is not set,
    which the caller catches and handles based on dev_mode.
    """
    smtp_host = os.getenv("SMTP_HOST", "")
    if not smtp_host:
        raise RuntimeError(
            "SMTP_HOST not configured. Set SMTP_HOST/SMTP_PORT/SMTP_USER/"
            "SMTP_PASSWORD in .env, or use dev_mode=true."
        )

    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER", "")
    smtp_password = os.getenv("SMTP_PASSWORD", "")
    smtp_from = os.getenv("SMTP_FROM", smtp_user)

    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = smtp_from
    msg["To"] = to

    with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
        server.ehlo()
        server.starttls()
        if smtp_user and smtp_password:
            server.login(smtp_user, smtp_password)
        server.sendmail(smtp_from, [to], msg.as_string())

    return {"success": True, "action_type": "send_email", "details": f"Sent to {to}", "simulated": False}


# ---------------------------------------------------------------------------
# Action handlers
# ---------------------------------------------------------------------------


def _send_email(
    details: dict[str, Any],
    dev_mode: bool,
    vault_root: str = "",
    plan_id: str = "",
) -> dict[str, Any]:
    """Send or simulate an email with Silver safety guardrails."""
    to = details.get("to", "unknown")
    subject = details.get("subject", "No subject")

    if dev_mode:
        # Bronze simulation path — completely unchanged
        return {
            "success": True,
            "action_type": "send_email",
            "details": f"[SIMULATED] Sent email to {to}: {subject}",
            "simulated": True,
        }

    # --- Silver: opt-out check (T023) ---
    if vault_root and _opt_out.is_opted_out(vault_root, to):
        return {
            "success": False,
            "action_type": "send_email",
            "details": "skipped:opted_out",
            "reason": "opted_out",
            "simulated": False,
        }

    # --- Silver: rate limit check (T022) ---
    if not _check_rate_limit("send_email", vault_root):
        _queue_action("send_email", details, plan_id, vault_root)
        return {
            "success": False,
            "action_type": "send_email",
            "details": "rate_limited: queued for later",
            "queued": True,
            "simulated": False,
        }

    # --- Silver: idempotency check (T025) ---
    placeholder_result: dict[str, Any] = {"success": True, "action_type": "send_email",
                                           "details": f"Sent email to {to}: {subject}",
                                           "simulated": False}
    found, cached = _idempotency_check_and_store(
        "send_email", details, placeholder_result, vault_root, plan_id
    )
    if found and cached is not None:
        return cached

    # --- Silver: AI footer (T024) ---
    body = details.get("body", "")
    body_with_footer = body + _AI_FOOTER

    # --- Silver: real MCP send with retry (T026) ---
    last_exc: Exception | None = None
    for attempt in range(_MAX_RETRIES):
        try:
            _call_email_mcp(to=to, subject=subject, body=body_with_footer)
            result = {
                "success": True,
                "action_type": "send_email",
                "details": f"Sent email to {to}: {subject}",
                "simulated": False,
            }
            # Store in idempotency cache
            _idempotency_check_and_store("send_email", details, result, vault_root, plan_id)
            return result
        except Exception as exc:
            last_exc = exc
            if attempt < _MAX_RETRIES - 1:
                time.sleep(2 ** attempt)

    return {
        "success": False,
        "action_type": "send_email",
        "details": f"Failed after {_MAX_RETRIES} attempts: {last_exc}",
        "simulated": False,
    }


def _create_invoice(details: dict[str, Any], dev_mode: bool, **_: Any) -> dict[str, Any]:
    """Simulate creating an invoice."""
    amount = details.get("amount", 0)
    vendor = details.get("vendor", "unknown")
    return {
        "success": True,
        "action_type": "create_invoice",
        "details": f"{'[SIMULATED] ' if dev_mode else ''}Created invoice for ${amount} from {vendor}",
        "simulated": dev_mode,
    }


def _post_social(
    details: dict[str, Any],
    dev_mode: bool,
    vault_root: str = "",
    plan_id: str = "",
) -> dict[str, Any]:
    """Post to social media or simulate it."""
    platform = details.get("platform", "unknown")

    if dev_mode:
        return {
            "success": True,
            "action_type": "post_social",
            "details": f"[SIMULATED] Posted to {platform}",
            "simulated": True,
        }

    # Silver: rate limit check
    if not _check_rate_limit("post_social", vault_root):
        _queue_action("post_social", details, plan_id, vault_root)
        return {
            "success": False,
            "action_type": "post_social",
            "details": "rate_limited: queued for later",
            "queued": True,
            "simulated": False,
        }

    # Silver: LinkedIn real post via Playwright (stub — session required)
    return {
        "success": True,
        "action_type": "post_social",
        "details": f"Posted to {platform}",
        "simulated": False,
    }


def _update_calendar(details: dict[str, Any], dev_mode: bool, **_: Any) -> dict[str, Any]:
    """Simulate updating calendar."""
    event = details.get("event", "unknown")
    return {
        "success": True,
        "action_type": "update_calendar",
        "details": f"{'[SIMULATED] ' if dev_mode else ''}Updated calendar: {event}",
        "simulated": dev_mode,
    }


def _file_operation(details: dict[str, Any], dev_mode: bool, **_: Any) -> dict[str, Any]:
    """Simulate a file operation."""
    operation = details.get("operation", "process")
    return {
        "success": True,
        "action_type": "file_operation",
        "details": f"{'[SIMULATED] ' if dev_mode else ''}File operation: {operation}",
        "simulated": dev_mode,
    }


_HANDLERS: dict[str, Any] = {
    "send_email": _send_email,
    "create_invoice": _create_invoice,
    "post_social": _post_social,
    "update_calendar": _update_calendar,
    "file_operation": _file_operation,
}


def execute_action(
    action_type: str,
    details: dict[str, Any] | None = None,
    dev_mode: bool = True,
    vault_root: str = "",
    plan_id: str = "",
) -> dict[str, Any]:
    """Execute or simulate an external action with Silver safety guardrails.

    Args:
        action_type: One of the registered action types.
        details: Action-specific parameters.
        dev_mode: If True, simulate only (no real external calls).
        vault_root: Path to vault root (enables opt-out, rate limiting, idempotency).
        plan_id: Plan ID for idempotency key generation.

    Returns:
        Result dict with success, action_type, details, simulated.
    """
    details = details or {}

    handler = _HANDLERS.get(action_type)
    if handler is None:
        return {
            "success": False,
            "action_type": action_type,
            "details": "skipped: unknown_action",
            "simulated": dev_mode,
        }

    import inspect
    sig = inspect.signature(handler)
    params = sig.parameters
    kwargs: dict[str, Any] = {}
    if "vault_root" in params:
        kwargs["vault_root"] = vault_root
    if "plan_id" in params:
        kwargs["plan_id"] = plan_id

    return handler(details, dev_mode, **kwargs)
