"""Odoo Community MCP server -- stdio transport.

Exposes 6 tools via MCP protocol for use by Claude Code and other MCP clients.
For in-process use, import OdooMCPClient directly from client.py.

Usage (stdio):
    python -m src.mcp_servers.odoo_mcp.server

Test (direct handler call, no subprocess):
    tools = await _list_tools_handler()
    result = await _call_tool_handler("list_transactions", {})
"""
from __future__ import annotations

import json
import os
from typing import Any

try:
    import anyio
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import TextContent, Tool
    _MCP_AVAILABLE = True
except ImportError:
    _MCP_AVAILABLE = False

    class TextContent:  # type: ignore[no-redef]
        def __init__(self, type: str, text: str):
            self.type = type
            self.text = text

    class Tool:  # type: ignore[no-redef]
        def __init__(self, name: str, description: str, inputSchema: dict):
            self.name = name
            self.description = description
            self.inputSchema = inputSchema

from src.mcp_servers.odoo_mcp.client import OdooMCPClient

_TOOLS = [
    Tool(
        name="create_invoice",
        description="Create a customer or vendor invoice in Odoo. Requires HITL approval.",
        inputSchema={
            "type": "object",
            "properties": {
                "partner": {"type": "string", "description": "Customer/vendor name"},
                "amount": {"type": "number", "description": "Invoice total (positive)"},
                "description": {"type": "string", "description": "Line item description"},
                "move_type": {"type": "string", "enum": ["out_invoice", "in_invoice"],
                              "default": "out_invoice"},
            },
            "required": ["partner", "amount", "description"],
        },
    ),
    Tool(
        name="list_invoices",
        description="List invoices from Odoo. Auto-approved read operation.",
        inputSchema={
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "default": 20},
                "state": {"type": "string", "enum": ["draft", "posted", "cancelled", "all"],
                          "default": "all"},
            },
        },
    ),
    Tool(
        name="record_expense",
        description="Record an expense in Odoo. Requires HITL approval.",
        inputSchema={
            "type": "object",
            "properties": {
                "description": {"type": "string"},
                "amount": {"type": "number", "description": "Positive decimal"},
                "account": {"type": "string", "description": "Account name or code"},
                "date": {"type": "string", "description": "YYYY-MM-DD (optional)"},
            },
            "required": ["description", "amount", "account"],
        },
    ),
    Tool(
        name="get_account_balance",
        description="Get account balance from Odoo. Auto-approved read operation.",
        inputSchema={
            "type": "object",
            "properties": {
                "account": {"type": "string", "description": "Account name (optional)"},
            },
        },
    ),
    Tool(
        name="post_invoice",
        description="Post (confirm) a draft invoice in Odoo. Requires HITL approval.",
        inputSchema={
            "type": "object",
            "properties": {
                "invoice_id": {"type": "integer", "description": "Odoo account.move ID"},
            },
            "required": ["invoice_id"],
        },
    ),
    Tool(
        name="list_transactions",
        description="List journal line transactions from Odoo. Auto-approved read operation.",
        inputSchema={
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "default": 50},
                "date_from": {"type": "string", "description": "YYYY-MM-DD"},
                "date_to": {"type": "string", "description": "YYYY-MM-DD"},
            },
        },
    ),
]


def _get_client(vault_root: str | None = None) -> OdooMCPClient:
    dev_mode = os.environ.get("DEV_MODE", "").lower() in ("true", "1", "yes")
    root = vault_root or os.environ.get("VAULT_ROOT", "vault")
    return OdooMCPClient.from_env(vault_root=root, dev_mode=dev_mode)


async def _list_tools_handler() -> list[Tool]:
    return _TOOLS


async def _call_tool_handler(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    client = _get_client()

    dispatch: dict[str, Any] = {
        "create_invoice": lambda a: client.create_invoice(
            partner=a["partner"], amount=a["amount"], description=a["description"],
            move_type=a.get("move_type", "out_invoice"),
        ),
        "list_invoices": lambda a: client.list_invoices(
            limit=a.get("limit", 20), state=a.get("state", "all"),
        ),
        "record_expense": lambda a: client.record_expense(
            description=a["description"], amount=a["amount"], account=a["account"],
            date=a.get("date"),
        ),
        "get_account_balance": lambda a: client.get_account_balance(
            account=a.get("account"),
        ),
        "post_invoice": lambda a: client.post_invoice(invoice_id=a["invoice_id"]),
        "list_transactions": lambda a: client.list_transactions(
            limit=a.get("limit", 50),
            date_from=a.get("date_from"),
            date_to=a.get("date_to"),
        ),
    }

    if name not in dispatch:
        raise ValueError(f"Unknown tool: {name}")

    result = dispatch[name](arguments)
    return [TextContent(type="text", text=json.dumps(result))]


if _MCP_AVAILABLE:
    server = Server("odoo-mcp")

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return await _list_tools_handler()

    @server.call_tool()
    async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
        return await _call_tool_handler(name, arguments)

    async def main() -> None:
        async with stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                server.create_initialization_options(),
            )

    if __name__ == "__main__":
        anyio.run(main)
