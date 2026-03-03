"""Tests for Odoo MCP server -- async handler tests (no subprocess)."""
import json
import pytest

pytest_plugins = ["pytest_asyncio"]


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.asyncio
async def test_list_tools_returns_six_tools(monkeypatch, tmp_path):
    monkeypatch.setenv("DEV_MODE", "true")
    monkeypatch.setenv("VAULT_ROOT", str(tmp_path))
    from src.mcp_servers.odoo_mcp import server as srv
    tools = await srv._list_tools_handler()
    assert len(tools) == 6
    names = {t.name for t in tools}
    expected = {"create_invoice", "list_invoices", "record_expense",
                "get_account_balance", "post_invoice", "list_transactions"}
    assert names == expected


@pytest.mark.asyncio
async def test_call_tool_create_invoice(monkeypatch, tmp_path):
    monkeypatch.setenv("DEV_MODE", "true")
    monkeypatch.setenv("VAULT_ROOT", str(tmp_path))
    from src.mcp_servers.odoo_mcp import server as srv
    result = await srv._call_tool_handler("create_invoice", {
        "partner": "ACME", "amount": 100.0, "description": "Test"
    })
    assert result
    data = json.loads(result[0].text)
    assert data["status"] == "pending_approval"


@pytest.mark.asyncio
async def test_call_tool_list_transactions(monkeypatch, tmp_path):
    monkeypatch.setenv("DEV_MODE", "true")
    monkeypatch.setenv("VAULT_ROOT", str(tmp_path))
    from src.mcp_servers.odoo_mcp import server as srv
    result = await srv._call_tool_handler("list_transactions", {})
    assert result
    data = json.loads(result[0].text)
    assert "transactions" in data


@pytest.mark.asyncio
async def test_call_tool_list_invoices(monkeypatch, tmp_path):
    monkeypatch.setenv("DEV_MODE", "true")
    monkeypatch.setenv("VAULT_ROOT", str(tmp_path))
    from src.mcp_servers.odoo_mcp import server as srv
    result = await srv._call_tool_handler("list_invoices", {})
    assert result
    data = json.loads(result[0].text)
    assert "invoices" in data


@pytest.mark.asyncio
async def test_call_tool_unknown_raises(monkeypatch, tmp_path):
    monkeypatch.setenv("DEV_MODE", "true")
    monkeypatch.setenv("VAULT_ROOT", str(tmp_path))
    from src.mcp_servers.odoo_mcp import server as srv
    with pytest.raises(ValueError, match="Unknown tool"):
        await srv._call_tool_handler("unknown_tool", {})


@pytest.mark.asyncio
async def test_all_tool_schemas_are_dicts(monkeypatch, tmp_path):
    monkeypatch.setenv("DEV_MODE", "true")
    monkeypatch.setenv("VAULT_ROOT", str(tmp_path))
    from src.mcp_servers.odoo_mcp import server as srv
    tools = await srv._list_tools_handler()
    for tool in tools:
        assert isinstance(tool.inputSchema, dict)
