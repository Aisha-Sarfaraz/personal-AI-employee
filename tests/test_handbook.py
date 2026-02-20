"""Tests for src.skills.check_handbook."""

import pytest
from pathlib import Path

from src.core.vault import write_file
from src.skills.check_handbook import (
    classify_financial_risk,
    classify_action_risk,
    validate_action,
    parse_handbook,
    ValidationResult,
)


VAULT_DIRS = ("Inbox", "Needs_Action", "Plans", "Done", "Logs",
              "Pending_Approval", "Approved", "Rejected")


def make_vault(tmp_path: Path) -> str:
    vault_root = tmp_path / "vault"
    for folder in VAULT_DIRS:
        (vault_root / folder).mkdir(parents=True, exist_ok=True)
    return str(vault_root)


class TestFinancialRisk:
    def test_50_is_medium(self):
        assert classify_financial_risk(50) == "MEDIUM"

    def test_99_is_medium(self):
        assert classify_financial_risk(99) == "MEDIUM"

    def test_100_is_high(self):
        assert classify_financial_risk(100) == "HIGH"

    def test_500_is_high(self):
        assert classify_financial_risk(500) == "HIGH"

    def test_999_is_high(self):
        assert classify_financial_risk(999) == "HIGH"

    def test_1000_is_critical(self):
        assert classify_financial_risk(1000) == "CRITICAL"

    def test_5000_is_critical(self):
        assert classify_financial_risk(5000) == "CRITICAL"

    def test_9999_is_critical(self):
        assert classify_financial_risk(9999) == "CRITICAL"

    def test_10001_is_denied(self):
        assert classify_financial_risk(10001) == "DENIED"

    def test_15000_is_denied(self):
        assert classify_financial_risk(15000) == "DENIED"

    def test_0_is_medium(self):
        assert classify_financial_risk(0) == "MEDIUM"


class TestActionRisk:
    def test_create_invoice_with_amount_uses_financial_risk(self):
        risk = classify_action_risk("create_invoice", {"amount": 500})
        assert risk == "HIGH"

    def test_send_email_is_high(self):
        assert classify_action_risk("send_email") == "HIGH"

    def test_file_operation_is_low(self):
        assert classify_action_risk("file_operation") == "LOW"

    def test_update_calendar_is_medium(self):
        assert classify_action_risk("update_calendar") == "MEDIUM"

    def test_unknown_action_defaults_medium(self):
        assert classify_action_risk("unknown_action") == "MEDIUM"


class TestValidateAction:
    def test_low_risk_auto_approved(self, tmp_path):
        vault_root = make_vault(tmp_path)
        result = validate_action(vault_root, "file_operation")
        assert result.allowed is True
        assert result.risk_level == "LOW"
        assert result.requires_approval is False

    def test_high_risk_requires_approval(self, tmp_path):
        vault_root = make_vault(tmp_path)
        result = validate_action(vault_root, "send_email")
        assert result.allowed is True
        assert result.risk_level == "HIGH"
        assert result.requires_approval is True

    def test_denied_not_allowed(self, tmp_path):
        vault_root = make_vault(tmp_path)
        result = validate_action(vault_root, "create_invoice", {"amount": 15000})
        assert result.allowed is False
        assert result.risk_level == "DENIED"

    def test_returns_validation_result(self, tmp_path):
        vault_root = make_vault(tmp_path)
        result = validate_action(vault_root, "file_operation")
        assert isinstance(result, ValidationResult)


class TestParseHandbook:
    def test_returns_defaults_when_no_handbook(self, tmp_path):
        vault_root = make_vault(tmp_path)
        rules = parse_handbook(vault_root)
        assert "financial_thresholds" in rules
        assert "denied_threshold" in rules

    def test_parses_handbook_thresholds(self, tmp_path):
        vault_root = make_vault(tmp_path)
        handbook_content = """# Company Handbook

## Financial Thresholds

| Amount Range | Risk Level |
|-------------|------------|
| $0-100 | MEDIUM |
| $100-1,000 | HIGH |
| $1,000-10,000 | CRITICAL |
| >$10,000 | DENIED |
"""
        write_file(vault_root, "Company_Handbook.md", handbook_content)
        rules = parse_handbook(vault_root)
        assert len(rules["financial_thresholds"]) >= 3
