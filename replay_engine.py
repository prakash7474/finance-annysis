"""replay_engine.py - Accelerated market replay feed (paper/simulated).

Replays a deterministic, hand-crafted OHLC series (with an obvious trend change
and a scripted price jump) at accelerated speed so the demo shows visible
movement without real market hours.  All maths (SMA, realised volatility, trend,
spike detection) are deterministic Python - never the LLM.
"""

from __future__ import annotations

import math
import random
import statistics
from typing import Any, Dict, List, Optional

SYMBOLS = ["RELIANCE", "TCS", "INFY", "HDFCBANK", "SBIN"]
_BASE_PRICES = {"RELIANCE": 2450.0, "TCS": 3680.0, "INFY": 1520.0,
                "HDFCBANK": 1620.0, "SBIN": 780.0}
_BARS = 140
_JUMP_IDX = 90  # scripted price jump -> volatility spike zone


def _generate_series() -> Dict[str, List[float]]:
    """Deterministic close series per symbol with a baked-in jump + vol spike."""
    rng = random.Random(42)  # fixed seed -> identical every run
    series: Dict[str, List[float]] = {}
    for sym in SYMBOLS:
        price = _BASE_PRICES[sym]
        closes: List[float] = [price]
        for i in range(_BARS):
            # Low volatility before the jump zone, elevated through it.
            if _JUMP_IDX - 3 <= i < _JUMP_IDX + 8:
                vol = 0.025
            else:
                vol = 0.006
            ret = 0.0012 + rng.gauss(0, vol)
            if i == _JUMP_IDX:
                ret += 0.16  # the scripted price jump
            elif i in (_JUMP_IDX + 2, _JUMP_IDX + 4):
                ret += 0.03  # choppy re-entry, keeps volatility high
            price = price * (1 + ret)
            closes.append(price)
        series[sym] = closes
    return series


class MarketReplayFeed:
    """Steps through the deterministic series and derives market facts."""

    def __init__(self, start_cursor: int = 60):
        self.symbols = SYMBOLS
        self._start_cursor = start_cursor
        self._series = _generate_series()
        self.cursor = min(start_cursor, _BARS)
        self._announced: Dict[str, bool] = {s: False for s in SYMBOLS}

    # ── advance / replay ─────────────────────────────────────────────────────
    def advance(self, symbols: Optional[List[str]] = None) -> Dict[str, float]:
        """Advance the replay by one bar (loops back to keep the demo live)."""
        self.cursor += 1
        if self.cursor >= _BARS:
            # Wrap around so the demo keeps ticking; re-arm spike announcements.
            self.cursor = self._start_cursor
            self._announced = {s: False for s in self.symbols}
        return {s: self.latest_price(s) for s in (symbols or self.symbols)}

    def step(self, symbol: str) -> float:
        """Advance only feed for one symbol (used for deterministic tests)."""
        return self.latest_price(symbol)

    # ── OHLC accessors (slice to cursor) ─────────────────────────────────────
    def series(self, symbol: str) -> List[float]:
        return self._series[symbol][: self.cursor]

    def ohlc(self, symbol: str, n: int = 30) -> List[Dict[str, Any]]:
        closes = self.series(symbol)[-n:]
        if not closes:
            return []
        out = []
        for i, close in enumerate(closes):
            prev = closes[i - 1] if i else close
            open_ = prev * (1 + (0.0005 if i % 2 else -0.0005))
            out.append({"date": f"2026-08-{i + 1:02d}", "open": round(open_, 2),
                        "high": round(max(open_, close) * 1.005, 2),
                        "low": round(min(open_, close) * 0.995, 2), "close": round(close, 2)})
        return out

    def latest_price(self, symbol: str) -> float:
        closes = self._series[symbol][: self.cursor]
        return round(closes[-1], 2) if closes else _BASE_PRICES[symbol]

    def ohlc_open(self, symbol: str) -> float:
        closes = self._series[symbol][: self.cursor]
        return round(closes[-1] * 0.998, 2) if closes else _BASE_PRICES[symbol]

    # ── deterministic maths ──────────────────────────────────────────────────
    def compute_sma(self, symbol: str, window: int = 20) -> Optional[float]:
        closes = self._series[symbol][: self.cursor]
        if len(closes) < window:
            return None
        return round(statistics.fmean(closes[-window:]), 2)

    def compute_realized_volatility(self, symbol: str, lookback: int = 5,
                                    annualize: bool = True) -> Optional[float]:
        closes = self._series[symbol][: self.cursor]
        if len(closes) < lookback + 1:
            return None
        returns = [(closes[i] - closes[i - 1]) / closes[i - 1] for i in range(len(closes) - lookback, len(closes))]
        vol = statistics.pstdev(returns)
        return round(vol * (math.sqrt(252) if annualize else 1.0), 4)

    def classify_trend(self, symbol: str, sma_window: int = 20) -> str:
        sma = self.compute_sma(symbol, sma_window)
        price = self.latest_price(symbol) if len(self.series(symbol)) > sma_window and sma else 0.0
        if sma is None:
            return "NOT_ENOUGH_DATA"
        pct = (price - sma) / sma
        if pct > 0.02:
            return "UPTREND"
        if pct < -0.02:
            return "DOWNTREND"
        return "NEUTRAL"

    def detect_volatility_spike(self, symbol: str, lookback: int = 5,
                                threshold: float = 2.2) -> bool:
        closes = self._series[symbol][: self.cursor]
        if len(closes) < max(lookback * 3, 20):
            return False
        recent = [(closes[i] - closes[i - 1]) / closes[i - 1] for i in range(len(closes) - lookback, len(closes))]
        baseline_window = max(10, len(closes) - lookback * 4)
        baseline = [(closes[i] - closes[i - 1]) / closes[i - 1] for i in range(len(closes) - baseline_window, len(closes) - lookback)]
        recent_vol = statistics.pstdev(recent)
        base_vol = statistics.pstdev(baseline) if len(baseline) > 1 else 0.0
        if base_vol <= 0:
            return len(recent) and recent_vol > 0
        return recent_vol > threshold * base_vol

    def maybe_spike(self, symbol: str, **kw) -> bool:
        """Return True once per symbol when a volatility spike occurs."""
        if self.detect_volatility_spike(symbol, **kw):
            if not self._announced[symbol]:
                self._announced[symbol] = True
                return True
        return False

    def reset_announced(self) -> None:
        self._announced = {s: False for s in self.symbols}

    def market_facts(self, symbol: str) -> Dict[str, Any]:
        return {
            "symbol": symbol,
            "price": self.latest_price(symbol),
            "sma": self.compute_sma(symbol),
            "realized_volatility": self.compute_realized_volatility(symbol),
            "trend": self.classify_trend(symbol),
        }


# Module-level singleton feed (shared by the backend, MCP servers and demo).
feed = MarketReplayFeed()
