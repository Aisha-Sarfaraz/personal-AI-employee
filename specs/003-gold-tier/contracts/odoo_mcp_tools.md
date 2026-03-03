# Odoo MCP Tools — API Contract

**Feature**: 003-gold-tier
**Module**: `src/mcp_servers/odoo_mcp/`
**Transport**: stdio (MCP Python SDK v1.x)
**Date**: 2026-02-25

---

## Overview

The Odoo MCP server exposes six tools over stdio MCP protocol. All tools are also exposed as
plain Python functions in `src/mcp_servers/odoo_mcp/client.py` for direct import by
`finance_watcher.py` and `generate_invoice.py`.

- **Read tools** (auto-approved, direct Odoo call): `list_invoices`, `get_account_balance`, `list_transactions`
- **Write tools** (HITL gate required): `create_invoice`, `record_expense`, `post_invoice`

In `dev_mode: true`, all tools return mocked responses and log `simulated: true`.

---

## Tool 1 — `create_invoice`

**Type**: Write (HITL required)

### Input Schema

```json
{
  "partner": "string (required) — customer/vendor name",
  "amount": "number (required) — positive decimal",
  "description": "string (required) — line item description",
  "move_type": "string (optional, default: out_invoice) — out_invoice | in_invoice",
  "currency": "string (optional, default: USD)"
}
```

### Behaviour

1. Validates all required fields present.
2. Creates `vault/Pending_Approval/INVOICE_<timestamp>.md` with YAML frontmatter.
3. Returns `{status: "pending_approval", approval_file: "<path>"}`.
4. **Does NOT call Odoo** until the approval file moves to `vault/Approved/`.
5. In `dev_mode: true`: returns `{status: "pending_approval", approval_file: "<path>", simulated: true}`.

### Success Response

```json
{
  "status": "pending_approval",
  "approval_file": "vault/Pending_Approval/INVOICE_20260225_100000.md"
}
```

### Error Responses

| Condition | Response |
|-----------|----------|
| Missing required field | `{"status": "error", "error": "Missing required field: <name>"}` |
| Odoo unreachable (after approval) | `{"status": "failure", "error": "Odoo connection refused"}` |

---

## Tool 2 — `list_invoices`

**Type**: Read (auto-approved)

### Input Schema

```json
{
  "limit": "integer (optional, default: 20) — max invoices to return",
  "state": "string (optional) — draft | posted | cancelled | all (default: all)"
}
```

### Behaviour

1. Calls Odoo JSON-RPC `execute_kw("account.move", "search_read", ...)`.
2. Returns list of invoice summaries.
3. In `dev_mode: true`: returns fixtures from `vault/Watch/finance_mock/`.

### Success Response

```json
{
  "invoices": [
    {
      "id": 42,
      "name": "INV/2026/00001",
      "partner_name": "ACME Corp",
      "amount_total": 1250.00,
      "state": "posted",
      "invoice_date": "2026-02-20"
    }
  ],
  "count": 1
}
```

---

## Tool 3 — `record_expense`

**Type**: Write (HITL required)

### Input Schema

```json
{
  "description": "string (required)",
  "amount": "number (required) — positive decimal (stored as negative in Odoo)",
  "account": "string (required) — account name or code",
  "date": "string (optional, default: today) — YYYY-MM-DD"
}
```

### Behaviour

Same HITL gate pattern as `create_invoice`. Creates `vault/Pending_Approval/EXPENSE_<ts>.md`.

### Success Response

```json
{
  "status": "pending_approval",
  "approval_file": "vault/Pending_Approval/EXPENSE_20260225_100000.md"
}
```

---

## Tool 4 — `get_account_balance`

**Type**: Read (auto-approved)

### Input Schema

```json
{
  "account": "string (optional) — account name or code; omit for overall balance"
}
```

### Success Response

```json
{
  "account": "Bank",
  "balance": 15420.50,
  "currency": "USD",
  "as_of": "2026-02-25"
}
```

---

## Tool 5 — `post_invoice`

**Type**: Write (HITL required)

### Input Schema

```json
{
  "invoice_id": "integer (required) — Odoo account.move ID to post (confirm)"
}
```

### Behaviour

Creates approval file. On approval, calls `account.move.action_post()` in Odoo.
Posts the invoice from `draft` to `posted` state.

### Success Response (after approval + Odoo call)

```json
{
  "status": "success",
  "invoice_id": 42,
  "state": "posted"
}
```

---

## Tool 6 — `list_transactions`

**Type**: Read (auto-approved)

### Input Schema

```json
{
  "limit": "integer (optional, default: 50)",
  "date_from": "string (optional) — YYYY-MM-DD",
  "date_to": "string (optional) — YYYY-MM-DD"
}
```

### Behaviour

1. Calls Odoo `account.move.line` search_read for journal items.
2. Returns list of transactions used by `FinanceWatcher.check_for_updates()`.
3. In `dev_mode: true`: reads `vault/Watch/finance_mock/*.json`.

### Success Response

```json
{
  "transactions": [
    {
      "move_line_id": 101,
      "date": "2026-02-24",
      "description": "Client payment — ACME",
      "amount": 1250.00,
      "account": "Bank"
    }
  ],
  "count": 1
}
```

---

## Client Module Contract (`src/mcp_servers/odoo_mcp/client.py`)

The client module exposes the same six operations as synchronous Python functions
for direct import (no MCP protocol overhead for in-process calls).

```python
class OdooMCPClient:
    def __init__(self, url: str, db: str, uid: int, password: str, dev_mode: bool = False): ...

    def create_invoice(self, partner: str, amount: float, description: str,
                       move_type: str = "out_invoice") -> dict: ...

    def list_invoices(self, limit: int = 20, state: str = "all") -> dict: ...

    def record_expense(self, description: str, amount: float, account: str,
                       date: str | None = None) -> dict: ...

    def get_account_balance(self, account: str | None = None) -> dict: ...

    def post_invoice(self, invoice_id: int) -> dict: ...

    def list_transactions(self, limit: int = 50, date_from: str | None = None,
                          date_to: str | None = None) -> dict: ...
```

All methods raise `ConnectionError` on Odoo unreachable (caller catches and falls back).
All methods respect `dev_mode` and return mocked responses without HTTP calls when True.

---

## Odoo JSON-RPC Call Pattern

```python
# Per-call auth — used in all OdooMCPClient methods
def _execute_kw(self, model, method, args, kwargs=None):
    payload = {
        "jsonrpc": "2.0", "method": "call", "id": 1,
        "params": {
            "service": "object",
            "method": "execute_kw",
            "args": [self.db, self.uid, self.password, model, method, args, kwargs or {}],
        }
    }
    resp = requests.post(f"{self.url}/web/dataset/call_kw", json=payload, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    if "error" in data:
        raise RuntimeError(data["error"]["data"].get("message", "Odoo error"))
    return data["result"]
```
