---
name: reconcile-transactions
description: Match and reconcile bank transactions with journal entries in Odoo. Use when bank statements need matching with existing invoices and bills.
version: 1.0.0
agent: finance-agent
type: action
inputs:
  - bank_statement: Bank statement data (transactions list)
  - date_range: Period to reconcile
  - auto_match_threshold: Confidence threshold for auto-matching (default 0.95)
outputs:
  - matched: List of matched transaction pairs
  - unmatched: List of transactions that couldn't be matched
  - suggestions: Suggested matches with confidence scores
  - reconciliation_report: Summary of reconciliation results
reusability: extremely-high
requires_mcp: odoo-mcp
---

# Skill: reconcile-transactions

## 1. Purpose

Match bank statement transactions with corresponding journal entries in Odoo. Automatically match high-confidence pairs and present uncertain matches for human review.

## 2. When to Use This Skill

**Mandatory invocation:**
- Periodic reconciliation (weekly/monthly)
- New bank statement imported
- Finance Agent detects unreconciled transactions

## 3. Workflow

1. **Fetch**: Get unreconciled journal entries from Odoo
2. **Parse**: Process bank statement transactions
3. **Match**: For each bank transaction, find matching journal entries by:
   - Exact amount match
   - Date proximity (within 3 business days)
   - Partner/reference matching
4. **Score**: Assign confidence score to each match
5. **Auto-match**: Match pairs with confidence > threshold
6. **Present**: Show uncertain matches to human for approval
7. **Reconcile**: Execute reconciliation via Odoo JSON-RPC
8. **Report**: Generate reconciliation summary

## 4. HITL Gate

**Risk Level**: HIGH (financial reconciliation)
**Approval Required**: YES — explicit approval for all reconciliation actions

## 5. Constraints

- Never auto-reconcile without human review in Phase 1
- Log every reconciliation action with before/after states
- Flag unmatched transactions prominently
- Idempotent — re-running produces same results
