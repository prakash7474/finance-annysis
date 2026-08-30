"""
demat_mcp_server.py - Phase 4 Demat MCP (PAPER MODE ONLY).

No live-mode code path exists.  Orders fill against the current replay tick with
a fixed slippage and update the mocked snapshot.  Defence-in-depth: orders that
exceed available cash are rejected at this layer too.

Hardened: input validation, structured error responses, health check,
and idempotency guard (same order_id not double-filled).
"""

import json
import time

from mcp.server.mcpserver import MCPServer

try:
    from _common import run_server
except ImportError:
    from mcp_servers._common import run_server
from accounts_provider import AccountNotLinked, provider
from demat_engine import InsufficientCash, OrderNotFound, demat_engine
from replay_engine import MarketReplayFeed, SYMBOLS
from models.allocation_models import OrderRequest
from structured_logger import get_logger, metrics

log = get_logger("demat_mcp")

mcp = MCPServer("demat-paper", instructions="Paper-mode demat execution (NO live trades)")
_feed = MarketReplayFeed(start_cursor=60)
_start_time = time.time()

VALID_SIDES = {"BUY", "SELL"}


import math


def _validate_order_inputs(account_id: str, symbol: str, side: str, quantity: float) -> str | None:
    """Validate all inputs before doing any work. Returns error JSON or None."""
    if not account_id or not isinstance(account_id, str):
        return json.dumps({"error": "VALIDATION_ERROR", "message": "account_id is required"})
    if not symbol or not isinstance(symbol, str):
        return json.dumps({"error": "VALIDATION_ERROR", "message": "symbol is required"})
    sym = symbol.upper().strip()
    if sym not in SYMBOLS:
        return json.dumps({"error": "INVALID_SYMBOL",
                           "message": f"Symbol '{sym}' not in supported list: {SYMBOLS}"})
    if not side or side.upper().strip() not in VALID_SIDES:
        return json.dumps({"error": "VALIDATION_ERROR",
                           "message": f"side must be BUY or SELL, got '{side}'"})
    if not isinstance(quantity, (int, float)) or math.isnan(quantity) or math.isinf(quantity) or quantity <= 0:
        return json.dumps({"error": "VALIDATION_ERROR",
                           "message": f"quantity must be > 0 and finite, got {quantity}"})
    return None


@mcp.tool()
def place_paper_order(account_id: str, symbol: str, side: str, quantity: float) -> str:
    """Place a PAPER order (simulated fill at current tick + 0.1% slippage)."""
    # Validate inputs before doing any work
    err = _validate_order_inputs(account_id, symbol, side, quantity)
    if err:
        metrics.increment("demat_validation_error")
        return err

    try:
        market_price = _feed.latest_price(symbol.upper())
        order = demat_engine.place_paper_order(account_id, symbol.upper(), side, quantity, market_price)
        metrics.increment("demat_orders_filled")
        log.info("paper_order_filled", account_id=account_id, symbol=symbol.upper(),
                 side=side, quantity=quantity, fill_price=order.fill_price)
        return json.dumps(order.model_dump())
    except AccountNotLinked as exc:
        metrics.increment("demat_account_not_linked")
        return json.dumps({"error": exc.error_code, "message": exc.message})
    except InsufficientCash as exc:
        metrics.increment("demat_insufficient_cash")
        log.warning("insufficient_cash", account_id=account_id, symbol=symbol.upper())
        return json.dumps({"error": "INSUFFICIENT_CASH", "message": exc.message,
                           "status": "REJECTED"})
    except ValueError as exc:
        metrics.increment("demat_validation_error")
        return json.dumps({"error": "VALIDATION_ERROR", "message": str(exc)})
    except Exception as exc:
        metrics.increment("demat_internal_error")
        log.exception("place_order_error", account_id=account_id, symbol=symbol.upper())
        return json.dumps({"error": "INTERNAL_ERROR", "message": "Failed to place order."})


@mcp.tool()
def get_order_status(order_id: str) -> str:
    """Fetch a paper order's status."""
    if not order_id or not isinstance(order_id, str):
        metrics.increment("demat_validation_error")
        return json.dumps({"error": "VALIDATION_ERROR", "message": "order_id is required"})
    try:
        order = demat_engine.get_order_status(order_id)
        return json.dumps(order.model_dump())
    except OrderNotFound as exc:
        return json.dumps({"error": exc.error_code, "message": exc.message})
    except Exception as exc:
        log.exception("get_order_error", order_id=order_id)
        return json.dumps({"error": "INTERNAL_ERROR", "message": "Failed to fetch order status."})


@mcp.tool()
def health_check() -> str:
    """Health check: returns server uptime and status."""
    return json.dumps({
        "status": "healthy",
        "server": "demat-paper",
        "uptime_seconds": round(time.time() - _start_time, 1),
        "total_orders": len(demat_engine.list_orders()),
        "metrics": metrics.snapshot(),
    })


@mcp.resource("demat://orders/{order_id}")
def resource_order(order_id: str) -> str:
    return get_order_status(order_id)


if __name__ == "__main__":
    run_server(mcp, default_port=9007)
