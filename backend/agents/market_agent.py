"""Market agent - price / SMA / trend / momentum via the Market MCP."""

from __future__ import annotations

from typing import Any, Dict

import market_engine as me
from backend.agents.base_agent import AgentContext, BaseAgent
from backend.orchestrator.data_layer import MarketDataNotFound


class MarketAgent(BaseAgent):
    name = "market_agent"

    async def handle(self, ctx: AgentContext) -> Dict[str, Any]:
        symbol = ctx.entities.get("symbol") or ctx.session.last_market_symbol
        if not symbol:
            return self.result({"available": True, "needs_symbol": True})
        try:
            price = await self.services.get_price(symbol)
            bars = await self.services.get_ohlc(symbol, 60)
            trend = me.detect_trend_vs_sma(bars, sma_days=20)
            momentum = me.compute_momentum(bars, lookback_days=10)
            return self.result({
                "symbol": symbol,
                "price": price,
                "sma": trend.get("sma"),
                "trend": trend.get("trend"),
                "pct_diff": trend.get("pct_diff"),
                "momentum_pct": momentum.get("momentum_pct"),
                "ohlc_count": len(bars),
            })
        except MarketDataNotFound as exc:
            return self.result({}, status="failed",
                               error=f"Market data not found: {exc.args[0] if exc.args else symbol}")
        except Exception as exc:  # noqa: BLE001
            return self.result({}, status="failed", error=f"Market data unavailable: {exc}")
