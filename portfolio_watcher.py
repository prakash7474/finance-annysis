"""
portfolio_watcher.py - Deterministic market watch & alert system.

Watchers analyse configured symbols (price, SMA, trend, momentum) and emit
alerts on trend/momentum flips, large moves and SMA crossovers.  It is purely an
analysis system: it NEVER executes trades.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import market_engine as me
from models.alert_models import MarketAlert

DEFAULT_SYMBOLS = ["RELIANCE", "TCS", "INFY"]


def _adapter():
    from mock_market_adapter import MockMarketAdapter

    return MockMarketAdapter(seed=42)


def compute_state(symbol: str, adapter=None) -> Dict[str, Any]:
    """Compute current market state for a symbol."""
    adapter = adapter or _adapter()
    price = adapter.get_latest_price(symbol)
    bars = adapter.get_ohlc_history(symbol, 60)
    trend = me.detect_trend_vs_sma(bars, sma_days=20)
    momentum = me.compute_momentum(bars, lookback_days=10)
    sma = trend.get("sma")
    above_sma = (trend.get("pct_diff") is not None and trend["pct_diff"] > 0)
    return {
        "symbol": symbol.upper(),
        "price": price,
        "trend": trend.get("trend") or "NEUTRAL",
        "momentum_pct": momentum.get("momentum_pct", 0.0),
        "sma": sma,
        "pct_diff": trend.get("pct_diff"),
        "above_sma": above_sma,
    }


def build_snapshot(symbols: List[str], adapter=None) -> Dict[str, Dict[str, Any]]:
    return {s.upper(): compute_state(s, adapter) for s in symbols}


def detect_alerts(previous: Dict[str, Any], current: Dict[str, Any]) -> List[MarketAlert]:
    alerts: List[MarketAlert] = []
    if not previous:
        return alerts
    p, c = previous, current

    # Trend flip
    if p.get("trend") in ("UPTREND", "DOWNTREND") and c.get("trend") in ("UPTREND", "DOWNTREND") and p["trend"] != c["trend"]:
        alerts.append(MarketAlert(
            symbol=c["symbol"], alert_type="TREND_FLIP", previous_state=p["trend"],
            current_state=c["trend"], severity="MEDIUM",
            message=f"{c['symbol']} trend flipped from {p['trend']} to {c['trend']}.",
        ))

    # Momentum sign flip
    prev_mom = p.get("momentum_pct", 0.0)
    cur_mom = c.get("momentum_pct", 0.0)
    if prev_mom != 0 and cur_mom != 0 and (prev_mom > 0) != (cur_mom > 0):
        alerts.append(MarketAlert(
            symbol=c["symbol"], alert_type="MOMENTUM_FLIP", previous_state=f"{prev_mom:+.2f}%",
            current_state=f"{cur_mom:+.2f}%", severity="MEDIUM",
            message=f"{c['symbol']} momentum flipped sign ({prev_mom:+.2f}% -> {cur_mom:+.2f}%).",
        ))

    # Large price movement
    p_price = p.get("price")
    c_price = c.get("price")
    if p_price and c_price:
        move_pct = (c_price - p_price) / p_price * 100.0
        if abs(move_pct) >= 5.0:
            alerts.append(MarketAlert(
                symbol=c["symbol"], alert_type="LARGE_MOVE", previous_state=f"{p_price:,.2f}",
                current_state=f"{c_price:,.2f}", severity="HIGH" if abs(move_pct) >= 10 else "LOW",
                message=f"{c['symbol']} moved {move_pct:+.2f}% to {c_price:,.2f}.",
            ))

    # SMA crossover
    if p.get("above_sma") is not None and c.get("above_sma") is not None and p["above_sma"] != c["above_sma"]:
        alerts.append(MarketAlert(
            symbol=c["symbol"], alert_type="SMA_CROSSOVER", previous_state="above SMA" if p["above_sma"] else "below SMA",
            current_state="above SMA" if c["above_sma"] else "below SMA", severity="LOW",
            message=f"{c['symbol']} crossed the 20-day SMA.",
        ))

    return alerts


def watch_portfolio(symbols: Optional[List[str]] = None, previous: Optional[Dict[str, Dict[str, Any]]] = None,
                    adapter=None) -> Dict[str, Any]:
    """Watch a set of symbols; return current snapshot + alerts vs ``previous``."""
    symbols = [s.upper() for s in (symbols or DEFAULT_SYMBOLS)]
    current = build_snapshot(symbols, adapter)
    alerts: List[MarketAlert] = []
    if previous:
        for sym, state in current.items():
            if sym in previous:
                alerts.extend(detect_alerts(previous[sym], state))
    return {"snapshot": current, "alerts": alerts}
