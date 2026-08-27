"""
bank_mcp_server.py - MCP server for mock bank data.

Exposes tools:
  - get_accounts: List all accounts
  - get_transactions: List transactions with optional date/account filters
  - get_loan_offers: List available loan products
"""

import json
from pathlib import Path
from mcp.server.mcpserver import MCPServer
from mcp.types import TextContent

# Create MCP server
mcp = MCPServer("mock-bank", instructions="Mock bank data server for finance analysis")

# Load mock data
DATA_FILE = Path(__file__).parent / "mock_data.json"


def _load_data() -> dict:
    with open(DATA_FILE, "r") as f:
        return json.load(f)


@mcp.tool()
def get_accounts() -> str:
    """List all bank accounts with their current balances."""
    data = _load_data()
    return json.dumps(data["accounts"])


@mcp.tool()
def get_transactions(
    account_id: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> str:
    """
    List transactions, optionally filtered by account and date range.
    
    Args:
        account_id: Filter by account ID (e.g., "ACC001")
        start_date: Filter transactions on or after this date (YYYY-MM-DD)
        end_date: Filter transactions on or before this date (YYYY-MM-DD)
    """
    data = _load_data()
    txns = data["transactions"]

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
    data = _load_data()
    return json.dumps(data["loan_offers"])


if __name__ == "__main__":
    mcp.run()
