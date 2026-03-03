from __future__ import annotations
import json
import os
from datetime import datetime, timezone
from typing import Any
import requests
from src.core.retry_handler import ErrorCategory, with_retry

_APPROVAL_TEMPLATE = """---
type: {approval_type}
partner: {partner}
amount: {amount}
description: {description}
move_type: {move_type}
risk_level: HIGH
requires_approval: true
simulated: {simulated}
created_at: {created_at}
---

# {title}

Please review and approve this action.

| Field | Value |
|-------|-------|
| Partner | {partner} |
| Amount | {amount} |
| Description | {description} |
"""


class OdooMCPClient:
    """Python client for Odoo 19+ External JSON-RPC API.

    In dev_mode=True, all methods return mocked responses without HTTP calls.
    """

    def __init__(
        self,
        url: str,
        db: str,
        uid: int,
        password: str,
        vault_root: str = "",
        dev_mode: bool = False,
    ) -> None:
        self.url = url.rstrip("/")
        self.db = db
        self.uid = uid
        self.password = password
        self.vault_root = vault_root
        self.dev_mode = dev_mode

    @classmethod
    def from_env(cls, vault_root: str = "", dev_mode: bool | None = None) -> "OdooMCPClient":
        """Create client from environment variables."""
        if dev_mode is None:
            dev_mode = os.environ.get("DEV_MODE", "").lower() in ("true", "1", "yes")
        return cls(
            url=os.environ.get("ODOO_URL", "http://localhost:8069"),
            db=os.environ.get("ODOO_DB", "fte_db"),
            uid=int(os.environ.get("ODOO_UID", "1")),
            password=os.environ.get("ODOO_PASSWORD", ""),
            vault_root=vault_root,
            dev_mode=dev_mode,
        )

    @with_retry(max_attempts=3, base_delay=1.0, max_delay=60.0)
    def _execute_kw(
        self,
        model: str,
        method: str,
        args: list[Any],
        kwargs: dict[str, Any] | None = None,
    ) -> Any:
        """Perform a JSON-RPC call to Odoo with per-call auth."""
        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "id": 1,
            "params": {
                "service": "object",
                "method": "execute_kw",
                "args": [self.db, self.uid, self.password, model, method, args, kwargs or {}],
            },
        }
        try:
            resp = requests.post(
                f"{self.url}/web/dataset/call_kw",
                json=payload,
                timeout=10,
            )
            resp.raise_for_status()
        except requests.exceptions.ConnectionError as e:
            raise ConnectionError(f"Odoo unreachable at {self.url}: {e}") from e
        except requests.exceptions.HTTPError as e:
            from src.core.retry_handler import categorise_http_error
            status = e.response.status_code if e.response else 500
            cat = categorise_http_error(status)
            new_exc = RuntimeError(f"Odoo HTTP {status}: {e}")
            new_exc.error_category = cat  # type: ignore[attr-defined]
            raise new_exc from e
        data = resp.json()
        if "error" in data:
            raise RuntimeError(data["error"].get("data", {}).get("message", "Odoo error"))
        return data["result"]

    def _write_approval_file(
        self,
        approval_type: str,
        title: str,
        partner: str,
        amount: float,
        description: str,
        move_type: str = "out_invoice",
    ) -> str:
        """Write a HITL approval file to vault/Pending_Approval/."""
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        filename = f"INVOICE_{ts}.md" if "invoice" in approval_type else f"EXPENSE_{ts}.md"
        if "post_invoice" in approval_type:
            filename = f"POST_INVOICE_{ts}.md"
        pending_dir = os.path.join(self.vault_root, "Pending_Approval")
        os.makedirs(pending_dir, exist_ok=True)
        approval_path = os.path.join(pending_dir, filename)
        content = _APPROVAL_TEMPLATE.format(
            approval_type=approval_type,
            partner=partner,
            amount=amount,
            description=description,
            move_type=move_type,
            simulated=str(self.dev_mode).lower(),
            created_at=datetime.now(timezone.utc).isoformat(),
            title=title,
        )
        with open(approval_path, "w", encoding="utf-8") as f:
            f.write(content)
        return approval_path

    def create_invoice(
        self,
        partner: str,
        amount: float,
        description: str,
        move_type: str = "out_invoice",
        currency: str = "USD",
    ) -> dict[str, Any]:
        """Create a customer/vendor invoice -- writes HITL approval file."""
        if not partner or not description or amount <= 0:
            raise ValueError("partner, description are required and amount must be > 0")
        approval_file = self._write_approval_file(
            approval_type="invoice_approval",
            title=f"Invoice -- {partner}",
            partner=partner,
            amount=amount,
            description=description,
            move_type=move_type,
        )
        return {"status": "pending_approval", "approval_file": approval_file, "simulated": self.dev_mode}

    def record_expense(
        self,
        description: str,
        amount: float,
        account: str,
        date: str | None = None,
    ) -> dict[str, Any]:
        """Record an expense -- writes HITL approval file."""
        approval_file = self._write_approval_file(
            approval_type="expense_approval",
            title=f"Expense -- {description}",
            partner=account,
            amount=amount,
            description=description,
        )
        return {"status": "pending_approval", "approval_file": approval_file, "simulated": self.dev_mode}

    def post_invoice(self, invoice_id: int) -> dict[str, Any]:
        """Post (confirm) a draft invoice -- writes HITL approval file."""
        approval_file = self._write_approval_file(
            approval_type="post_invoice_approval",
            title=f"Post Invoice #{invoice_id}",
            partner=f"Invoice #{invoice_id}",
            amount=0.0,
            description=f"Confirm and post Odoo invoice ID {invoice_id}",
        )
        return {"status": "pending_approval", "approval_file": approval_file, "simulated": self.dev_mode}

    def list_invoices(self, limit: int = 20, state: str = "all") -> dict[str, Any]:
        """List invoices from Odoo or return mock data in dev_mode."""
        if self.dev_mode:
            mock = [{"id": 1, "name": "INV/2026/00001", "partner_name": "ACME Corp",
                     "amount_total": 1250.00, "state": "posted", "invoice_date": "2026-02-20"}]
            return {"invoices": mock, "count": len(mock)}
        domain = [] if state == "all" else [["state", "=", state]]
        results = self._execute_kw("account.move", "search_read", [domain],
            {"fields": ["name", "partner_id", "amount_total", "state", "invoice_date"], "limit": limit})
        invoices = [{"id": r["id"], "name": r["name"],
                     "partner_name": r["partner_id"][1] if r.get("partner_id") else "",
                     "amount_total": r["amount_total"], "state": r["state"],
                     "invoice_date": r.get("invoice_date", "")} for r in (results or [])]
        return {"invoices": invoices, "count": len(invoices)}

    def get_account_balance(self, account: str | None = None) -> dict[str, Any]:
        """Get account balance from Odoo or return mock in dev_mode."""
        if self.dev_mode:
            return {"account": account or "Bank", "balance": 15420.50,
                    "currency": "USD", "as_of": datetime.now(timezone.utc).strftime("%Y-%m-%d")}
        domain = [["account_id.name", "=", account]] if account else []
        results = self._execute_kw("account.move.line", "read_group",
            [domain, ["balance"], ["account_id"]], {})
        balance = sum(r.get("balance", 0) for r in (results or []))
        return {"account": account or "All", "balance": float(balance),
                "currency": "USD", "as_of": datetime.now(timezone.utc).strftime("%Y-%m-%d")}

    def list_transactions(self, limit: int = 50, date_from: str | None = None,
                          date_to: str | None = None) -> dict[str, Any]:
        """List journal line transactions from Odoo or mock in dev_mode."""
        if self.dev_mode:
            mock = [
                {"move_line_id": 101, "date": "2026-02-24",
                 "description": "Client payment -- ACME", "amount": 1250.00, "account": "Bank"},
                {"move_line_id": 102, "date": "2026-02-24",
                 "description": "Office supplies", "amount": -45.00, "account": "Expenses:Office"},
            ]
            return {"transactions": mock, "count": len(mock)}
        domain: list[Any] = [["move_id.state", "=", "posted"]]
        if date_from:
            domain.append(["date", ">=", date_from])
        if date_to:
            domain.append(["date", "<=", date_to])
        results = self._execute_kw("account.move.line", "search_read", [domain],
            {"fields": ["id", "date", "name", "balance", "account_id"], "limit": limit})
        transactions = [
            {"move_line_id": r["id"], "date": r.get("date", ""),
             "description": r.get("name", ""),
             "amount": float(r.get("balance", 0)),
             "account": r["account_id"][1] if r.get("account_id") else ""}
            for r in (results or [])
        ]
        return {"transactions": transactions, "count": len(transactions)}
