"""DEV_MODE action executor — simulates external actions."""

from typing import Any


def _send_email(details: dict[str, Any], dev_mode: bool) -> dict[str, Any]:
    """Simulate sending an email."""
    to = details.get("to", "unknown")
    subject = details.get("subject", "No subject")
    return {
        "success": True,
        "action_type": "send_email",
        "details": f"{'[SIMULATED] ' if dev_mode else ''}Sent email to {to}: {subject}",
        "simulated": dev_mode,
    }


def _create_invoice(details: dict[str, Any], dev_mode: bool) -> dict[str, Any]:
    """Simulate creating an invoice."""
    amount = details.get("amount", 0)
    vendor = details.get("vendor", "unknown")
    return {
        "success": True,
        "action_type": "create_invoice",
        "details": f"{'[SIMULATED] ' if dev_mode else ''}Created invoice for ${amount} from {vendor}",
        "simulated": dev_mode,
    }


def _post_social(details: dict[str, Any], dev_mode: bool) -> dict[str, Any]:
    """Simulate posting to social media."""
    platform = details.get("platform", "unknown")
    return {
        "success": True,
        "action_type": "post_social",
        "details": f"{'[SIMULATED] ' if dev_mode else ''}Posted to {platform}",
        "simulated": dev_mode,
    }


def _update_calendar(details: dict[str, Any], dev_mode: bool) -> dict[str, Any]:
    """Simulate updating calendar."""
    event = details.get("event", "unknown")
    return {
        "success": True,
        "action_type": "update_calendar",
        "details": f"{'[SIMULATED] ' if dev_mode else ''}Updated calendar: {event}",
        "simulated": dev_mode,
    }


def _file_operation(details: dict[str, Any], dev_mode: bool) -> dict[str, Any]:
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
) -> dict[str, Any]:
    """Execute or simulate an external action.

    Args:
        action_type: One of the registered action types.
        details: Action-specific parameters.
        dev_mode: If True, simulate only.

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

    return handler(details, dev_mode)
