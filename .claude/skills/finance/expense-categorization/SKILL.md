---
name: expense-categorization
description: Classify and record expenses by category using Odoo chart of accounts. Use when expenses need recording or categorization.
version: 1.0.0
agent: finance-agent
type: action
inputs:
  - expense_description: What the expense is for
  - amount: Expense amount
  - vendor: Vendor or payee name
  - date: Transaction date
  - receipt: Receipt data (optional)
outputs:
  - category: Mapped chart of accounts category
  - expense_entry_id: Odoo journal entry ID
  - confidence: Categorization confidence
reusability: extremely-high
requires_mcp: odoo-mcp
---

# Skill: expense-categorization

## 1. Purpose

Classify expenses into the correct chart of accounts category and record them in Odoo. Flags uncertain categorizations for human review.

## 2. When to Use This Skill

**Mandatory invocation:**
- User submits an expense for recording
- Communication Agent routes an expense-related email
- Finance watcher detects a new transaction

## 3. Categorization Rules

| Keyword Pattern | Account Category | Odoo Account |
|----------------|-----------------|--------------|
| Office supplies, stationery | Office Expenses | 6200 |
| Software, SaaS, subscription | Software & IT | 6300 |
| Travel, flight, hotel | Travel Expenses | 6400 |
| Meals, food, restaurant | Meals & Entertainment | 6500 |
| Marketing, ads, promotion | Marketing | 6600 |
| Professional services, consulting | Professional Fees | 6700 |
| Unknown | FLAG FOR REVIEW | — |

## 4. Workflow

1. **Parse**: Extract expense details (amount, vendor, description)
2. **Categorize**: Match to chart of accounts using rules and patterns
3. **Validate**: Check for duplicates (same vendor + amount + date)
4. **Record**: Create journal entry in Odoo (as draft)
5. **Flag**: If categorization confidence < 0.7, ask human to confirm
6. **Approve**: Route through HITL gate for approval

## 5. HITL Gate

**Risk Level**: MEDIUM (< $100) or HIGH (>= $100)
**Approval Required**: Notify for MEDIUM, explicit approval for HIGH

## 6. Constraints

- Always flag first-time vendors for human review
- Never categorize uncertain expenses without human input
- Log categorization decisions for audit trail
- Idempotent — duplicate detection before recording
