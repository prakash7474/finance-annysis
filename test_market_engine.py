"""
test_market_engine.py - Unit tests for market_engine.py

Run with: python -m pytest test_market_engine.py -v
"""

from market_engine import (
    compute_sma,
    detect_trend_vs_sma,
    compute_momentum,
    compute_high_low_range,
)
from mock_market_adapter import MockMarketAdapter


# ──────────────────────────────────────────────────────────────────────────────
# SMA Tests
# ──────────────────────────────────────────────────────────────────────────────

def test_sma_basic():
    """SMA window-3 on [10,12,14,16,18] should give [None, None, 12, 14, 16]."""
    closes = [10.0, 12.0, 14.0, 16.0, 18.0]
    sma = compute_sma(closes, 3)
    assert sma[0] is None
    assert sma[1] is None
    assert abs(sma[2] - 12.0) < 1e-6
    assert abs(sma[3] - 14.0) < 1e-6
    assert abs(sma[4] - 16.0) < 1e-6


def test_sma_window_equals_length():
    """SMA window == data length gives one value at the end."""
    closes = [10.0, 20.0, 30.0]
    sma = compute_sma(closes, 3)
    assert sma[0] is None
    assert sma[1] is None
    assert abs(sma[2] - 20.0) < 1e-6


def test_sma_window_1():
    """SMA window-1 should return the values themselves."""
    closes = [10.0, 20.0, 30.0]
    sma = compute_sma(closes, 1)
    assert sma == [10.0, 20.0, 30.0]


def test_sma_empty():
    """Empty input returns empty list."""
    assert compute_sma([], 5) == []


# ──────────────────────────────────────────────────────────────────────────────
# Trend Detection Tests
# ──────────────────────────────────────────────────────────────────────────────

def _make_ohlc(prices: list[float]) -> list[dict]:
    """Helper: create OHLC bars from a list of close prices."""
    return [
        {
            "date": f"2026-08-{i+1:02d}",
            "open": p - 1,
            "high": p + 2,
            "low": p - 2,
            "close": p,
        }
        for i, p in enumerate(prices)
    ]


def test_uptrend_vs_sma():
    """Clearly rising prices should be UPTREND."""
    prices = list(range(1, 31))  # 1..30
    ohlc = _make_ohlc(prices)
    result = detect_trend_vs_sma(ohlc, sma_days=20)
    assert result["trend"] == "UPTREND"
    assert result["pct_diff"] > 2


def test_downtrend_vs_sma():
    """Clearly falling prices should be DOWNTREND."""
    prices = list(range(30, 0, -1))  # 30..1
    ohlc = _make_ohlc(prices)
    result = detect_trend_vs_sma(ohlc, sma_days=20)
    assert result["trend"] == "DOWNTREND"
    assert result["pct_diff"] < -2


def test_neutral_trend():
    """Flat prices should be NEUTRAL."""
    prices = [100.0] * 30
    ohlc = _make_ohlc(prices)
    result = detect_trend_vs_sma(ohlc, sma_days=20)
    assert result["trend"] == "NEUTRAL"
    assert abs(result["pct_diff"]) < 0.01


def test_insufficient_data():
    """Fewer bars than SMA window returns NEUTRAL with None sma."""
    ohlc = _make_ohlc([10.0, 20.0])
    result = detect_trend_vs_sma(ohlc, sma_days=20)
    assert result["trend"] == "NEUTRAL"
    assert result["sma"] is None


def test_empty_ohlc():
    """Empty OHLC returns safe defaults."""
    result = detect_trend_vs_sma([], sma_days=20)
    assert result["latest_close"] is None
    assert result["sma"] is None


# ──────────────────────────────────────────────────────────────────────────────
# Momentum Tests
# ──────────────────────────────────────────────────────────────────────────────

def test_momentum_positive():
    """Rising prices should give positive momentum."""
    prices = list(range(1, 21))  # 1..20
    ohlc = _make_ohlc(prices)
    result = compute_momentum(ohlc, lookback_days=10)
    # older close = 10, latest = 20 => 100%
    assert abs(result["momentum_pct"] - 100.0) < 1e-6


def test_momentum_negative():
    """Falling prices should give negative momentum."""
    prices = list(range(20, 0, -1))  # 20..1
    ohlc = _make_ohlc(prices)
    result = compute_momentum(ohlc, lookback_days=10)
    # older close = prices[-11] = 11, latest = 1 => (1-11)/11*100 = -90.91%
    assert result["momentum_pct"] < -80


def test_momentum_short_data():
    """When data < lookback+1, adjusts lookback."""
    ohlc = _make_ohlc([100.0, 110.0, 105.0])
    result = compute_momentum(ohlc, lookback_days=10)
    assert result["lookback_days"] == 2
    assert abs(result["momentum_pct"] - ((105 - 100) / 100 * 100)) < 1e-6


def test_momentum_empty():
    """Empty OHLC returns 0 momentum."""
    result = compute_momentum([], lookback_days=10)
    assert result["momentum_pct"] == 0.0


# ──────────────────────────────────────────────────────────────────────────────
# High/Low Range Tests
# ──────────────────────────────────────────────────────────────────────────────

def test_high_low_range():
    ohlc = _make_ohlc([100.0, 110.0, 95.0, 105.0])
    result = compute_high_low_range(ohlc)
    assert result["high"] == 112.0  # max(high) = 110+2
    assert result["low"] == 93.0    # min(low) = 95-2
    assert result["days"] == 4


def test_high_low_range_subset():
    ohlc = _make_ohlc([100.0, 110.0, 95.0, 105.0, 120.0])
    result = compute_high_low_range(ohlc, days=3)
    assert result["days"] == 3


# ──────────────────────────────────────────────────────────────────────────────
# Integration Tests with MockAdapter
# ──────────────────────────────────────────────────────────────────────────────

def test_mock_adapter_ohlc_length():
    adapter = MockMarketAdapter(seed=42)
    ohlc = adapter.get_ohlc_history("INFY", days=60)
    # Should have ~42 bars (60 days minus weekends)
    assert len(ohlc) > 30
    assert len(ohlc) <= 60


def test_mock_adapter_price():
    adapter = MockMarketAdapter(seed=42)
    price = adapter.get_latest_price("RELIANCE")
    assert price > 2000  # RELIANCE base is ~2450


def test_mock_adapter_deterministic():
    """Same seed should give same results."""
    a1 = MockMarketAdapter(seed=99)
    a2 = MockMarketAdapter(seed=99)
    assert a1.get_latest_price("INFY") == a2.get_latest_price("INFY")
    assert a1.get_ohlc_history("INFY", 10) == a2.get_ohlc_history("INFY", 10)


def test_mock_adapter_with_engine():
    """Full integration: adapter -> engine."""
    adapter = MockMarketAdapter(seed=123)
    ohlc = adapter.get_ohlc_history("TCS", days=60)
    assert len(ohlc) >= 30

    trend = detect_trend_vs_sma(ohlc, sma_days=20)
    assert "trend" in trend
    assert "latest_close" in trend

    momentum = compute_momentum(ohlc, lookback_days=10)
    assert "momentum_pct" in momentum
