"""Handbook Compliance Checker skill — validates actions against business rules."""

import os
import re
from dataclasses import dataclass
from typing import Any

from src.core.vault import read_file


@dataclass
class ValidationResult:
    """Result of validating an action against handbook rules."""
    allowed: bool
    risk_level: str
    requires_approval: bool
    reason: str


# Default financial thresholds (used if handbook parsing fails)
DEFAULT_FINANCIAL_THRESHOLDS: list[tuple[float, float, str]] = [
    (0, 100, "MEDIUM"),
    (100, 1000, "HIGH"),
    (1000, 10000, "CRITICAL"),
]
DEFAULT_DENIED_THRESHOLD: float = 10000


def classify_financial_risk(amount: float) -> str:
    """Classify financial risk based on amount.

    Args:
        amount: Dollar amount of the financial action.

    Returns:
        Risk level: MEDIUM, HIGH, CRITICAL, or DENIED.
    """
    if amount > DEFAULT_DENIED_THRESHOLD:
        return "DENIED"
    for low, high, risk in DEFAULT_FINANCIAL_THRESHOLDS:
        if low <= amount < high:
            return risk
    if amount >= 1000:
        return "CRITICAL"
    return "MEDIUM"


def classify_action_risk(action_type: str, details: dict[str, Any] | None = None) -> str:
    """Classify risk level for an action type.

    Args:
        action_type: Type of action (send_email, create_invoice, etc.).
        details: Action-specific details.

    Returns:
        Risk level: LOW, MEDIUM, HIGH, or CRITICAL.
    """
    details = details or {}

    # Financial actions use amount-based classification
    if action_type in ("create_invoice", "record_expense", "process_payment"):
        amount = details.get("amount", 0)
        try:
            amount = float(amount)
        except (ValueError, TypeError):
            amount = 0
        return classify_financial_risk(amount)

    # Communication actions
    if action_type in ("send_email", "post_social"):
        return "HIGH"

    # File operations
    if action_type == "file_operation":
        return "LOW"

    # Calendar updates
    if action_type == "update_calendar":
        return "MEDIUM"

    return "MEDIUM"


def validate_action(
    vault_root: str,
    action_type: str,
    details: dict[str, Any] | None = None,
) -> ValidationResult:
    """Validate an action against Company_Handbook.md rules.

    Args:
        vault_root: Path to vault root.
        action_type: Type of action.
        details: Action-specific details.

    Returns:
        ValidationResult with allowed, risk_level, requires_approval, reason.
    """
    details = details or {}
    risk_level = classify_action_risk(action_type, details)

    if risk_level == "DENIED":
        amount = details.get("amount", "unknown")
        return ValidationResult(
            allowed=False,
            risk_level="DENIED",
            requires_approval=False,
            reason=f"Financial amount ${amount} exceeds maximum threshold ($10,000). Action denied.",
        )

    requires_approval = risk_level in ("HIGH", "CRITICAL")

    if risk_level == "LOW":
        reason = "Low-risk action. Auto-approved per handbook rules."
    elif risk_level == "MEDIUM":
        reason = "Medium-risk action. Proceeds with notification logged."
    elif risk_level == "HIGH":
        reason = "High-risk action. Requires explicit human approval."
    else:
        reason = "Critical-risk action. Requires explicit human approval with confirmation."

    return ValidationResult(
        allowed=True,
        risk_level=risk_level,
        requires_approval=requires_approval,
        reason=reason,
    )


def parse_handbook(vault_root: str) -> dict[str, Any]:
    """Parse Company_Handbook.md for dynamic rule extraction.

    Args:
        vault_root: Path to vault root.

    Returns:
        Dict with parsed rules. Falls back to defaults if parsing fails.
    """
    rules: dict[str, Any] = {
        "financial_thresholds": DEFAULT_FINANCIAL_THRESHOLDS,
        "denied_threshold": DEFAULT_DENIED_THRESHOLD,
    }

    try:
        content = read_file(vault_root, "Company_Handbook.md")
        # Extract financial thresholds from handbook
        thresholds = _extract_financial_thresholds(content)
        if thresholds:
            rules["financial_thresholds"] = thresholds["ranges"]
            rules["denied_threshold"] = thresholds["denied_above"]
    except FileNotFoundError:
        pass  # Use defaults

    return rules


def _extract_financial_thresholds(content: str) -> dict[str, Any] | None:
    """Extract financial thresholds from handbook markdown content."""
    # Look for patterns like "$0-100 MEDIUM", "$100-1K HIGH", etc.
    patterns = [
        (r'\$0[- ]+\$?100.*?MEDIUM', 0, 100, "MEDIUM"),
        (r'\$100[- ]+\$?1[,.]?000.*?HIGH', 100, 1000, "HIGH"),
        (r'\$1[,.]?000[- ]+\$?10[,.]?000.*?CRITICAL', 1000, 10000, "CRITICAL"),
    ]

    found_ranges: list[tuple[float, float, str]] = []
    for pattern, low, high, risk in patterns:
        if re.search(pattern, content, re.IGNORECASE):
            found_ranges.append((low, high, risk))

    denied_match = re.search(r'>\s*\$?10[,.]?000.*?DENIED', content, re.IGNORECASE)
    denied_above = 10000 if denied_match else DEFAULT_DENIED_THRESHOLD

    if found_ranges:
        return {"ranges": found_ranges, "denied_above": denied_above}
    return None


def run(vault_root: str) -> dict[str, Any]:
    """Skill entry point — parse handbook and return rules.

    Args:
        vault_root: Absolute path to the vault directory.

    Returns:
        Dict with processed count, errors list, and skipped count.
    """
    try:
        rules = parse_handbook(vault_root)
        return {"processed": 1, "errors": [], "skipped": 0}
    except Exception as e:
        return {"processed": 0, "errors": [str(e)], "skipped": 0}
