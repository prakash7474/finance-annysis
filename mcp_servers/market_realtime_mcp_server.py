"""
market_realtime_mcp_server.py - Phase 1 Market Realtime MCP (paper/simulated).

Replays a deterministic OHLC series at accelerated speed.  Exposes resources
(market://quotes/{symbol}/latest|ohlc) and deterministic tools
(compute_sma, compute_realized_volatility, classify_trend, advance_replay).
The backend runs the live accelerated feed and emits ``volatility_spike`` over
SSE; this server exposes the same deterministic maths over MCP.

Hardened: input validation, structured error responses, health check,
and metrics counters.
"""

import json
import time

from mcp.server.mcpserver import MCPServer

try:
    from _common import run_server
except ImportError:
    from mcp_servers._common import run_server
from replay_engine import MarketReplayFeed, SYMBOLS
from structured_logger import get_logger, metrics

log = get_logger("market_realtime_mcp")

mcp = MCPServer("market-realtime", instructions="Accelerated market replay feed (simulated)")
feed = MarketReplayFeed(start_cursor=60)
_start_time = time.time()


def _s(symbol: str) -> str:
    """Validate and normalise a symbol. Falls back to RELIANCE."""
    sym = symbol.upper().strip() if symbol else "RELIANCE"
    return sym if sym in SYMBOLS else "RELIANCE"


def _validate_symbol(symbol: str) -> tuple[str, str | None]:
    """Return (normalised_symbol, error_json_or_None)."""
    if not symbol or not isinstance(symbol, str):
        return "RELIANCE", None
    sym = symbol.upper().strip()
    if sym not in SYMBOLS:
        return sym, json.dumps({"error": "INVALID_SYMBOL",
                                "message": f"Symbol '{sym}' not in supported list: {SYMBOLS}"})
    return sym, None


def _validate_positive_int(value: int, name: str, lo: int = 1, hi: int = 200) -> tuple[int, str | None]:
    if not isinstance(value, (int, float)) or value < lo:
        return lo, json.dumps({"error": "VALIDATION_ERROR",
                               "message": f"{name} must be >= {lo}, got {value}"})
    return min(int(value), hi), None


@mcp.tool()
def compute_sma(symbol: str, window: int = 20) -> str:
    """20-day (default) simple moving average for a symbol. Structured error if not enough data."""
    sym, err = _validate_symbol(symbol)
    if err:
        metrics.increment("market_tool_validation_error")
        return err
    window, err2 = _validate_positive_int(window, "window")
    if err2:
        metrics.increment("market_tool_validation_error")
        return err2
    sma = feed.compute_sma(sym, window)
    if sma is None:
        return json.dumps({"error": "NOT_ENOUGH_DATA", "message": f"Need {window} bars for {sym}."})
    metrics.increment("market_sma_calls")
    return json.dumps({"symbol": sym, "sma": sma, "window": window})


@mcp.tool()
def compute_realized_volatility(symbol: str, lookback: int = 5) -> str:
    """Annualised realised volatility over a lookback window."""
    sym, err = _validate_symbol(symbol)
    if err:
        metrics.increment("market_tool_validation_error")
        return err
    lookback, err2 = _validate_positive_int(lookback, "lookback")
    if err2:
        metrics.increment("market_tool_validation_error")
        return err2
    vol = feed.compute_realized_volatility(sym, lookback)
    if vol is None:
        return json.dumps({"error": "NOT_ENOUGH_DATA", "message": f"Need {lookback + 1} bars for {sym}."})
    metrics.increment("market_vol_calls")
    return json.dumps({"symbol": sym, "realized_volatility": vol, "lookback": lookback})


@mcp.tool()
def classify_trend(symbol: str) -> str:
    """Classify trend: UPTREND / DOWNTREND / NEUTRAL / NOT_ENOUGH_DATA."""
    sym, err = _validate_symbol(symbol)
    if err:
        metrics.increment("market_tool_validation_error")
        return err
    metrics.increment("market_trend_calls")
    return json.dumps({"symbol": sym, "trend": feed.classify_trend(sym)})


@mcp.tool()
def advance_replay(symbol: str = "RELIANCE", steps: int = 1) -> str:
    """Advance the replay feed (accelerated time). Returns the latest price."""
    sym, err = _validate_symbol(symbol)
    if err:
        metrics.increment("market_tool_validation_error")
        return err
    steps, err2 = _validate_positive_int(steps, "steps", lo=1, hi=20)
    if err2:
        metrics.increment("market_tool_validation_error")
        return err2
    for _ in range(steps):
        feed.advance()
    metrics.increment("market_advance_calls")
    log.info("advance_replay", symbol=sym, steps=steps, cursor=feed.cursor,
             price=feed.latest_price(sym))
    return json.dumps({"symbol": sym, "cursor": feed.cursor, "price": feed.latest_price(sym)})


@mcp.tool()
def health_check() -> str:
    """Health check: returns server uptime and status."""
    return json.dumps({
        "status": "healthy",
        "server": "market-realtime",
        "uptime_seconds": round(time.time() - _start_time, 1),
        "cursor": feed.cursor,
        "symbols": SYMBOLS,
        "metrics": metrics.snapshot(),
    })


@mcp.resource("market://quotes/{symbol}/latest")
def resource_latest(symbol: str) -> str:
    sym, err = _validate_symbol(symbol)
    if err:
        return err
    return json.dumps({"symbol": sym, "price": feed.latest_price(sym),
                       "sma": feed.compute_sma(sym),
                       "realized_volatility": feed.compute_realized_volatility(sym),
                       "trend": feed.classify_trend(sym)})


@mcp.resource("market://quotes/{symbol}/ohlc")
def resource_ohlc(symbol: str) -> str:
    sym, err = _validate_symbol(symbol)
    if err:
        return err
    return json.dumps({"symbol": sym, "bars": feed.ohlc(sym, 30), "count": 30})


if __name__ == "__main__":
    run_server(mcp, default_port=9005)
