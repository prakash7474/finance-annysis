"""
market_realtime_mcp_server.py - Phase 1 Market Realtime MCP (paper/simulated).

Replays a deterministic OHLC series at accelerated speed.  Exposes resources
(market://quotes/{symbol}/latest|ohlc) and deterministic tools
(compute_sma, compute_realized_volatility, classify_trend, advance_replay).
The backend runs the live accelerated feed and emits ``volatility_spike`` over
SSE; this server exposes the same deterministic maths over MCP.
"""

import json

from mcp.server.mcpserver import MCPServer

from _common import run_server
from replay_engine import MarketReplayFeed, SYMBOLS

mcp = MCPServer("market-realtime", instructions="Accelerated market replay feed (simulated)")
feed = MarketReplayFeed(start_cursor=60)


def _s(symbol: str) -> str:
    return symbol.upper() if symbol.upper() in SYMBOLS else "RELIANCE"


@mcp.tool()
def compute_sma(symbol: str, window: int = 20) -> str:
    """20-day (default) simple moving average for a symbol. Structured error if not enough data."""
    sym = _s(symbol)
    sma = feed.compute_sma(sym, window)
    if sma is None:
        return json.dumps({"error": "NOT_ENOUGH_DATA", "message": f"Need {window} bars for {sym}."})
    return json.dumps({"symbol": sym, "sma": sma, "window": window})


@mcp.tool()
def compute_realized_volatility(symbol: str, lookback: int = 5) -> str:
    """Annualised realised volatility over a lookback window."""
    sym = _s(symbol)
    vol = feed.compute_realized_volatility(sym, lookback)
    if vol is None:
        return json.dumps({"error": "NOT_ENOUGH_DATA", "message": f"Need {lookback + 1} bars for {sym}."})
    return json.dumps({"symbol": sym, "realized_volatility": vol, "lookback": lookback})


@mcp.tool()
def classify_trend(symbol: str) -> str:
    """Classify trend: UPTREND / DOWNTREND / NEUTRAL / NOT_ENOUGH_DATA."""
    sym = _s(symbol)
    return json.dumps({"symbol": sym, "trend": feed.classify_trend(sym)})


@mcp.tool()
def advance_replay(symbol: str = "RELIANCE", steps: int = 1) -> str:
    """Advance the replay feed (accelerated time). Returns the latest price."""
    sym = _s(symbol)
    for _ in range(max(1, min(steps, 20))):
        feed.advance()
    return json.dumps({"symbol": sym, "cursor": feed.cursor, "price": feed.latest_price(sym)})


@mcp.resource("market://quotes/{symbol}/latest")
def resource_latest(symbol: str) -> str:
    sym = _s(symbol)
    return json.dumps({"symbol": sym, "price": feed.latest_price(sym),
                       "sma": feed.compute_sma(sym),
                       "realized_volatility": feed.compute_realized_volatility(sym),
                       "trend": feed.classify_trend(sym)})


@mcp.resource("market://quotes/{symbol}/ohlc")
def resource_ohlc(symbol: str) -> str:
    sym = _s(symbol)
    return json.dumps({"symbol": sym, "bars": feed.ohlc(sym, 30), "count": 30})


if __name__ == "__main__":
    run_server(mcp, default_port=9005)
