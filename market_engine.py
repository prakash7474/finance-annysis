"""
market_engine.py - Pure Python market analysis functions.

Computes SMA, trend detection, and momentum from OHLC data.
No MCP or I/O logic.
"""

from typing import Any


def compute_sma(closes: list[float], window: int) -> list[float | None]:
    """
    Compute Simple Moving Average for a series of closing prices.

    Returns a list of same length; first (window-1) entries are None.
    """
    sma: list[float | None] = []
    for i in range(len(closes)):
        if i < window - 1:
            sma.append(None)
        else:
            window_slice = closes[i - window + 1 : i + 1]
            sma.append(round(sum(window_slice) / window, 2))
    return sma


def detect_trend_vs_sma(
    ohlc: list[dict],
    sma_days: int = 20,
) -> dict[str, Any]:
    """
    Determine trend by comparing latest close to its SMA.

    Returns:
        {
            "latest_close": float,
            "sma": float | None,
            "trend": "UPTREND" | "DOWNTREND" | "NEUTRAL",
            "pct_diff": float | None,
        }
    """
    if not ohlc:
        return {
            "latest_close": None,
            "sma": None,
            "trend": "NEUTRAL",
            "pct_diff": None,
        }

    closes = [bar["close"] for bar in ohlc]
    sma_values = compute_sma(closes, sma_days)
    latest_close = closes[-1]
    latest_sma = sma_values[-1]

    if latest_sma is None:
        return {
            "latest_close": latest_close,
            "sma": None,
            "trend": "NEUTRAL",
            "pct_diff": None,
        }

    pct_diff = (latest_close - latest_sma) / latest_sma * 100

    if pct_diff > 2:
        trend = "UPTREND"
    elif pct_diff < -2:
        trend = "DOWNTREND"
    else:
        trend = "NEUTRAL"

    return {
        "latest_close": round(latest_close, 2),
        "sma": round(latest_sma, 2),
        "trend": trend,
        "pct_diff": round(pct_diff, 2),
    }


def compute_momentum(ohlc: list[dict], lookback_days: int = 10) -> dict[str, Any]:
    """
    Compute simple momentum: % change over last N days.

    Returns:
        {"momentum_pct": float, "lookback_days": int, "older_close": float, "latest_close": float}
    """
    if len(ohlc) < 2:
        return {
            "momentum_pct": 0.0,
            "lookback_days": lookback_days,
            "older_close": ohlc[-1]["close"] if ohlc else 0,
            "latest_close": ohlc[-1]["close"] if ohlc else 0,
        }

    if len(ohlc) < lookback_days + 1:
        lookback_days = len(ohlc) - 1

    older_close = ohlc[-(lookback_days + 1)]["close"]
    latest_close = ohlc[-1]["close"]

    momentum_pct = (latest_close - older_close) / older_close * 100 if older_close != 0 else 0.0

    return {
        "momentum_pct": round(momentum_pct, 2),
        "lookback_days": lookback_days,
        "older_close": round(older_close, 2),
        "latest_close": round(latest_close, 2),
    }


def compute_high_low_range(ohlc: list[dict], days: int | None = None) -> dict[str, Any]:
    """
    Compute high/low range for the last N days (or all data).
    """
    if not ohlc:
        return {"high": 0, "low": 0, "range_pct": 0, "days": 0}

    data = ohlc[-days:] if days else ohlc
    highs = [bar["high"] for bar in data]
    lows = [bar["low"] for bar in data]

    period_high = max(highs)
    period_low = min(lows)
    range_pct = ((period_high - period_low) / period_low * 100) if period_low > 0 else 0

    return {
        "high": round(period_high, 2),
        "low": round(period_low, 2),
        "range_pct": round(range_pct, 2),
        "days": len(data),
    }


# ──────────────────────────────────────────────────────────────────────────────
# Formatting helpers
# ──────────────────────────────────────────────────────────────────────────────

def format_price(symbol: str, price: float) -> str:
    return f"{symbol}: Rs.{price:,.2f}"


def format_ohlc_table(ohlc: list[dict], symbol: str, last_n: int = 10) -> str:
    """Pretty-print OHLC as a table (show last N rows)."""
    data = ohlc[-last_n:] if len(ohlc) > last_n else ohlc
    lines = [
        f"OHLC for {symbol} (last {len(data)} of {len(ohlc)} days):",
        "-" * 60,
        f"{'Date':<12} {'Open':>10} {'High':>10} {'Low':>10} {'Close':>10}",
        "-" * 60,
    ]
    for bar in data:
        lines.append(
            f"{bar['date']:<12} {bar['open']:>10.2f} {bar['high']:>10.2f} "
            f"{bar['low']:>10.2f} {bar['close']:>10.2f}"
        )
    lines.append("-" * 60)
    return "\n".join(lines)


def format_trend(symbol: str, result: dict) -> str:
    """Pretty-print trend analysis."""
    trend_emoji = {"UPTREND": "^", "DOWNTREND": "v", "NEUTRAL": "~"}
    emoji = trend_emoji.get(result["trend"], "?")

    lines = [
        f"Trend Analysis for {symbol}:",
        "-" * 40,
        f"  Latest close:  Rs.{result['latest_close']:,.2f}" if result["latest_close"] else "  Latest close: N/A",
    ]

    if result["sma"] is not None:
        lines.append(f"  {20}-day SMA:    Rs.{result['sma']:,.2f}")
        lines.append(f"  Difference:   {result['pct_diff']:+.2f}%")
        lines.append(f"  Trend:        {emoji} {result['trend']}")
    else:
        lines.append("  SMA:          Insufficient data")

    return "\n".join(lines)


def format_momentum(symbol: str, result: dict) -> str:
    """Pretty-print momentum analysis."""
    arrow = "+" if result["momentum_pct"] >= 0 else ""

    lines = [
        f"Momentum for {symbol}:",
        "-" * 40,
        f"  Lookback:     {result['lookback_days']} days",
        f"  Older close:  Rs.{result['older_close']:,.2f}",
        f"  Latest close: Rs.{result['latest_close']:,.2f}",
        f"  Momentum:     {arrow}{result['momentum_pct']:.2f}%",
    ]

    if result["momentum_pct"] > 5:
        lines.append("  Signal:       Strong positive momentum")
    elif result["momentum_pct"] > 0:
        lines.append("  Signal:       Mild positive momentum")
    elif result["momentum_pct"] > -5:
        lines.append("  Signal:       Mild negative momentum")
    else:
        lines.append("  Signal:       Strong negative momentum")

    return "\n".join(lines)
