---
name: generate-invoice
description: Create customer or vendor invoices in Odoo with correct chart of accounts mapping. Use when the Finance Agent needs to create a new invoice or bill.
version: 1.0.0
agent: finance-agent
type: action
inputs:
  - invoice_type: customer_invoice or vendor_bill
  - partner: Customer or vendor name/ID
  - line_items: List of items with description, quantity, unit_price, account
  - due_date: Payment due date
  - currency: Currency code (default from Odoo settings)
outputs:
  - invoice_id: Odoo invoice ID (account.move)
  - invoice_number: Human-readable invoice number
  - total_amount: Calculated total including tax
  - status: draft (always created as draft, requires approval to post)
reusability: extremely-high
framework_agnostic: false
requires_mcp: odoo-mcp
---

# Skill: generate-invoice

## 1. Purpose

Create properly structured invoices in Odoo with correct chart of accounts mapping, tax calculations, and partner association. Invoices are always created as drafts — posting requires HITL approval.

## 2. When to Use This Skill

**Mandatory invocation:**
- User requests invoice creation
- Finance Agent processes a billing request
- Communication Agent routes an invoice-related email

## 3. Workflow

1. **Validate**: Verify all required fields (partner, line items, amounts)
2. **Lookup**: Check partner exists in Odoo; if not, flag for creation
3. **Map**: Map line items to correct chart of accounts
4. **Calculate**: Verify tax calculations
5. **Create**: Create draft invoice via Odoo JSON-RPC (`account.move.create`)
6. **Verify**: Read back created invoice to confirm accuracy
7. **Present**: Show invoice summary to human for posting approval

## 4. Odoo JSON-RPC Operations

```python
# Create invoice
invoice_data = {
    "move_type": "out_invoice",  # or "in_invoice" for vendor bills
    "partner_id": partner_id,
    "invoice_date": date,
    "invoice_date_due": due_date,
    "invoice_line_ids": [(0, 0, {
        "name": description,
        "quantity": qty,
        "price_unit": unit_price,
        "account_id": account_id,
    })]
}
```

## 5. Idempotency

Before creating, check for duplicate invoices:
- Same partner + same total + same date = potential duplicate
- If duplicate detected, present both to human and ask to confirm

## 6. HITL Gate

**Risk Level**: HIGH (financial transaction)
**Approval Required**: YES — always
- Draft creation: notify human
- Posting (confirming) invoice: explicit approval required

## 7. Constraints

- Always create as DRAFT — never post without approval
- Verify chart of accounts mapping before creation
- Log every invoice creation in audit trail
- Include tax calculations in presentation to human
