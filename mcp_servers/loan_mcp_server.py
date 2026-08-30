"""
loan_mcp_server.py - Standalone MCP server exposing the deterministic loan engine.

The loan engine is pure Python (no external call); exposing it over MCP lets the
orchestrator invoke loan math through the same "server" abstraction as bank and
market data.  Runs over stdio by default, or SSE with:  python mcp_servers/loan_mcp_server.py --sse --port 9003
"""

import json

from mcp.server.mcpserver import MCPServer

try:
    from _common import run_server
except ImportError:
    from mcp_servers._common import run_server

import loan_engine as le

mcp = MCPServer("loan-engine", instructions="Deterministic loan calculation server")


@mcp.tool()
def calculate_emi(principal: float, annual_rate_pct: float, tenure_months: int) -> str:
    """Compute the monthly EMI for a principal, annual rate (%) and tenure (months)."""
    return json.dumps({"emi": le.calculate_emi(principal, annual_rate_pct, tenure_months)})


@mcp.tool()
def analyze_loan(amount: float, rate: float, tenure_months: int, monthly_income: float,
                 existing_emi: float = 0.0) -> str:
    """Analyze a loan: EMI, total cost and risk assessment."""
    return json.dumps(le.assess_loan_risk(amount, rate, tenure_months, monthly_income, existing_emi))


@mcp.tool()
def compare_loan_offers(amount: float, offers: str | list, monthly_income: float, existing_emi: float = 0.0) -> str:
    """Compare loan offers (offers is a JSON array or string) ranked by total cost."""
    if isinstance(offers, list):
        offer_list = offers
    else:
        try:
            offer_list = json.loads(offers)
        except Exception as exc:
            return json.dumps({"error": "INVALID_OFFERS_JSON", "message": str(exc), "offers": []})
    return json.dumps(le.compare_loan_offers(amount, offer_list, monthly_income, existing_emi))


if __name__ == "__main__":
    run_server(mcp, default_port=9003)
