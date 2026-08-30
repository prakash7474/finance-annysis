"""
market_mcp_server.py - Standalone MCP server for market data (Phase 4).

Exposes tools:
  - get_price : latest price for a symbol
  - get_ohlc  : OHLC history
  - get_news  : mock headlines

Runs over stdio by default, or SSE with:  python mcp_servers/market_mcp_server.py --sse --port 9002
"""

import json

from mcp.server.mcpserver import MCPServer

try:
    from _common import run_server
except ImportError:
    from mcp_servers._common import run_server

from mock_market_adapter import MockMarketAdapter

mcp = MCPServer("market-data", instructions="Market data server for Indian stocks")
adapter = MockMarketAdapter(seed=42)


@mcp.tool()
def get_price(symbol: str) -> str:
    """Return latest price for a given symbol (e.g., 'RELIANCE', 'INFY', 'TCS')."""
    price = adapter.get_latest_price(symbol)
    return json.dumps({"symbol": symbol.upper(), "price": price})


@mcp.tool()
def get_ohlc(symbol: str, days: int = 30) -> str:
    """Return daily OHLC history for a symbol for the last N days."""
    bars = adapter.get_ohlc_history(symbol, days)
    return json.dumps({"symbol": symbol.upper(), "bars": bars, "count": len(bars)})


@mcp.tool()
def get_news(symbol: str) -> str:
    """Return recent news headlines for a symbol (mock data for demo)."""
    news = [
        {"date": "2026-08-27", "headline": f"{symbol.upper()} reports strong Q2 earnings, beats estimates", "source": "Economic Times"},
        {"date": "2026-08-26", "headline": f"Analysts upgrade {symbol.upper()} on improved margins", "source": "Moneycontrol"},
        {"date": "2026-08-25", "headline": f"{symbol.upper()} announces dividend of Rs.15 per share", "source": "LiveMint"},
    ]
    return json.dumps({"symbol": symbol.upper(), "news": news, "count": len(news)})


if __name__ == "__main__":
    run_server(mcp, default_port=9002)
