"""
demat_mcp_server.py - Phase 4 Demat MCP (PAPER MODE ONLY).

No live-mode code path exists.  Orders fill against the current replay tick with
a fixed slippage and update the mocked snapshot.  Defence-in-depth: orders that
exceed available cash are rejected at this layer too.
"""

import json

from mcp.server.mcpserver import MCPServer

from _common import run_server
from accounts_provider import AccountNotLinked, provider
from demat_engine import InsufficientCash, OrderNotFound, demat_engine
from replay_engine import MarketReplayFeed
from models.allocation_models import OrderRequest

mcp = MCPServer("demat-paper", instructions="Paper-mode demat execution (NO live trades)")
_feed = MarketReplayFeed(start_cursor=60)


@mcp.tool()
def place_paper_order(account_id: str, symbol: str, side: str, quantity: float) -> str:
    """Place a PAPER order (simulated fill at current tick + 0.1% slippage)."""
    try:
        market_price = _feed.latest_price(symbol.upper())
        order = demat_engine.place_paper_order(account_id, symbol.upper(), side, quantity, market_price)
        return json.dumps(order.model_dump())
    except AccountNotLinked as exc:
        return json.dumps({"error": exc.error_code, "message": exc.message})
    except InsufficientCash as exc:
        return json.dumps({"error": "INSUFFICIENT_CASH", "message": exc.message,
                           "status": "REJECTED"})
    except ValueError as exc:
        return json.dumps({"error": "VALIDATION_ERROR", "message": str(exc)})


@mcp.tool()
def get_order_status(order_id: str) -> str:
    """Fetch a paper order's status."""
    try:
        order = demat_engine.get_order_status(order_id)
        return json.dumps(order.model_dump())
    except OrderNotFound as exc:
        return json.dumps({"error": exc.error_code, "message": exc.message})


@mcp.resource("demat://orders/{order_id}")
def resource_order(order_id: str) -> str:
    return get_order_status(order_id)


if __name__ == "__main__":
    run_server(mcp, default_port=9007)
