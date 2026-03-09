"""Accounting Audit skill — Gold Tier T028.

Reads Odoo financial data and produces a structured summary for CEO Briefing.
"""

from __future__ import annotations

import logging
import os
from datetime import date, datetime, timedelta, timezone
from typing import Any

import yaml

from src.mcp_servers.odoo_mcp.client import OdooMCPClient

logger = logging.getLogger(__name__)

_AUDIT_LOGIC_PATH = "config/audit_logic.yaml"


def _load_audit_logic() -> dict[str, Any]:
    """Load audit logic config from config/audit_logic.yaml."""
    try:
        with open(_AUDIT_LOGIC_PATH, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except (OSError, yaml.YAMLError):
        return {
            "SUBSCRIPTION_PATTERNS": [
                "subscription", "monthly fee", "monthly plan", "saas",
                "recurring", "annual fee", "license fee", "software license",
                "hosting fee", "maintenance fee", "retainer", "membership",
            ],
            "COST_SPIKE_THRESHOLD": 1.20,
            "INACTIVITY_DAYS": 30,
        }


def _is_this_week(date_str: str) -> bool:
    """Check if a date string falls within the last 7 days."""
    try:
        d = datetime.strptime(date_str, "%Y-%m-%d").date()
        today = date.today()
        week_ago = today - timedelta(days=7)
        return week_ago <= d <= today
    except (ValueError, TypeError):
        return False


def _is_this_month(date_str: str) -> bool:
    """Check if a date string falls within the current month."""
    try:
        d = datetime.strptime(date_str, "%Y-%m-%d").date()
        today = date.today()
        return d.year == today.year and d.month == today.month
    except (ValueError, TypeError):
        return False


def _calculate_revenue(invoices: list[dict[str, Any]]) -> dict[str, Any]:
    """Calculate revenue metrics from posted invoices."""
    weekly_paid = 0.0
    mtd_total = 0.0

    for inv in invoices:
        if inv.get("state") != "posted":
            continue
        amount = float(inv.get("amount_total", 0.0))
        invoice_date = inv.get("invoice_date", "")

        if _is_this_week(invoice_date):
            weekly_paid += amount
        if _is_this_month(invoice_date):
            mtd_total += amount

    return {
        "weekly_paid": weekly_paid,
        "mtd_total": mtd_total,
    }


def _calculate_expenses(transactions: list[dict[str, Any]]) -> dict[str, Any]:
    """Calculate expense metrics from transactions."""
    # Group expenses (negative amounts) by account
    category_totals: dict[str, float] = {}

    for txn in transactions:
        amount = float(txn.get("amount", 0.0))
        if amount < 0:  # expense
            account = txn.get("account", "Unknown")
            # Normalize account name to category
            category = account.split(":")[0] if ":" in account else account
            category_totals[category] = category_totals.get(category, 0.0) + abs(amount)

    # Sort by total and take top 5
    top_categories = sorted(
        [{"category": cat, "total": total} for cat, total in category_totals.items()],
        key=lambda x: x["total"],
        reverse=True,
    )[:5]

    return {
        "top_categories": top_categories,
    }


def _check_subscriptions(
    transactions: list[dict[str, Any]],
    patterns: list[str],
) -> list[str]:
    """Check for subscription-like expenses and return suggestions."""
    suggestions = []
    flagged = set()

    for txn in transactions:
        desc = txn.get("description", "").lower()
        amount = float(txn.get("amount", 0.0))
        if amount >= 0:  # only check expenses (negative amounts)
            continue
        for pattern in patterns:
            if pattern.lower() in desc and desc not in flagged:
                flagged.add(desc)
                suggestions.append(
                    f"Subscription detected: '{txn['description']}' "
                    f"({abs(amount):.2f}) — consider reviewing"
                )
                break

    return suggestions


def run(vault_root: str) -> dict[str, Any]:
    """Run accounting audit and return financial summary.

    Args:
        vault_root: Path to vault root directory.

    Returns:
        Dict with keys: revenue, expenses, suggestions.
        On Odoo error: {revenue: None, expenses: None, error: "...", degraded: True}
    """
    dev_mode = os.environ.get("DEV_MODE", "").lower() in ("true", "1", "yes")

    try:
        client = OdooMCPClient.from_env(vault_root=vault_root, dev_mode=dev_mode)

        # Fetch data from Odoo
        invoices_result = client.list_invoices(state="posted")
        invoices = invoices_result.get("invoices", [])

        transactions_result = client.list_transactions()
        transactions = transactions_result.get("transactions", [])

    except ConnectionError as exc:
        logger.warning("Odoo offline during accounting audit: %s", exc)
        return {
            "revenue": None,
            "expenses": None,
            "suggestions": [],
            "error": "Odoo offline",
            "degraded": True,
        }
    except Exception as exc:
        logger.error("Accounting audit failed: %s", exc)
        return {
            "revenue": None,
            "expenses": None,
            "suggestions": [],
            "error": str(exc),
            "degraded": True,
        }

    # Load audit logic for subscription patterns
    audit_logic = _load_audit_logic()
    subscription_patterns = audit_logic.get("SUBSCRIPTION_PATTERNS", [])

    # Calculate metrics
    revenue = _calculate_revenue(invoices)
    expenses = _calculate_expenses(transactions)
    suggestions = _check_subscriptions(transactions, subscription_patterns)

    return {
        "revenue": revenue,
        "expenses": expenses,
        "suggestions": suggestions,
    }
