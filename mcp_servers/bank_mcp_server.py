"""
bank_mcp_server.py - Standalone MCP server for mock bank data (Phase 4).

Exposes tools:
  - get_accounts      : list all accounts
  - get_transactions  : list / filter transactions
  - get_loan_offers   : list available loan products

Runs over stdio by default, or SSE with:  python mcp_servers/bank_mcp_server.py --sse --port 9001
"""

import json

from mcp.server.mcpserver import MCPServer

from _common import run_server  # inserts project root on sys.path
from backend._boot import MOCK_DATA_FILE

mcp = MCPServer("mock-bank", instructions="Mock bank data server for finance analysis")


def _load_data() -> dict:
    with open(MOCK_DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


@mcp.tool()
def get_accounts() -> str:
    """List all bank accounts with their current balances."""
    return json.dumps(_load_data()["accounts"])


@mcp.tool()
def get_transactions(account_id: str | None = None, start_date: str | None = None,
                     end_date: str | None = None) -> str:
    """List transactions, optionally filtered by account and date range."""
    txns = _load_data()["transactions"]
    if account_id:
        txns = [t for t in txns if t["account_id"] == account_id]
    if start_date:
        txns = [t for t in txns if t["date"] >= start_date]
    if end_date:
        txns = [t for t in txns if t["date"] <= end_date]
    return json.dumps(txns)


@mcp.tool()
def get_loan_offers() -> str:
    """List available loan products and their details."""
    return json.dumps(_load_data()["loan_offers"])


if __name__ == "__main__":
    run_server(mcp, default_port=9001)
