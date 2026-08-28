"""
governance_mcp_server.py - Phase 2 Governance MCP (mocked accounts).

Exposes read-only account snapshots (paper) and the risk-profile the Rules Engine
uses.  Unknown accounts return a structured ACCOUNT_NOT_LINKED error.
"""

import json

from mcp.server.mcpserver import MCPServer

from _common import run_server
from accounts_provider import AccountNotLinked, provider

mcp = MCPServer("governance-accounts", instructions="Mocked account snapshots (paper)")


@mcp.resource("governance://accounts/{account_id}/snapshot")
def resource_snapshot(account_id: str) -> str:
    try:
        snapshot = provider.get_snapshot(account_id)
        return json.dumps(snapshot.model_dump())
    except AccountNotLinked as exc:
        return json.dumps({"error": exc.error_code, "message": exc.message})


@mcp.tool()
def get_account_snapshot(account_id: str) -> str:
    """Fetch a mocked account snapshot by id."""
    return resource_snapshot(account_id)


@mcp.tool()
def list_accounts() -> str:
    """List available mocked accounts."""
    return json.dumps({"accounts": [s.model_dump() for s in provider.list_snapshots()]})


if __name__ == "__main__":
    run_server(mcp, default_port=9006)
