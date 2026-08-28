"""Tests for the MCP client manager (tool discovery + registry)."""

from backend.orchestrator.mcp_client_manager import MCPClientManager


def test_discover_tools_categories():
    d = MCPClientManager.discover_tools()
    assert {"bank", "loan", "market", "intelligence"} <= set(d.keys())
    assert any(t["name"] == "get_cash_position" for t in d["bank"])
    assert any(t["name"] == "calculate_loan" for t in d["loan"])
    assert any(t["name"] == "get_quote" for t in d["market"])


def test_discover_servers():
    servers = MCPClientManager.discover_servers()
    assert "bank_mcp" in servers and "loan_mcp" in servers and "market_mcp" in servers
    bank_tools = [t["name"] for t in servers["bank_mcp"]["tools"]]
    assert "get_cash_position" in bank_tools


def test_registry_tools():
    tools = MCPClientManager.registry_tools()
    assert len(tools) >= 15
    assert all({"name", "domain", "server", "description"} <= set(t) for t in tools)


def test_invoke_unconnected_raises():
    import pytest

    manager = MCPClientManager()
    with pytest.raises(RuntimeError):
        asyncio_run_invoke(manager, "bank", "get_accounts", {})


def asyncio_run_invoke(manager, server, tool, args):
    import asyncio

    return asyncio.run(manager.invoke(server, tool, args))
