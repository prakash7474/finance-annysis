"""Tests for the market replay engine (Phase 1)."""

from replay_engine import MarketReplayFeed, SYMBOLS


def _feed_at(cursor):
    f = MarketReplayFeed(start_cursor=60)
    while f.cursor < cursor:
        f.advance()
    return f


def test_symbols_present():
    assert "RELIANCE" in SYMBOLS and "TCS" in SYMBOLS and "INFY" in SYMBOLS


def test_advance_moves_price():
    f = MarketReplayFeed(start_cursor=60)
    before = f.latest_price("RELIANCE")
    f.advance()
    after = f.latest_price("RELIANCE")
    assert before != after


def test_sma_before_enough_data_returns_none():
    f = MarketReplayFeed(start_cursor=5)
    assert f.compute_sma("RELIANCE", 20) is None


def test_sma_with_enough_data():
    f = _feed_at(80)
    assert f.compute_sma("RELIANCE", 20) is not None


def test_realized_volatility_missing_data():
    f = MarketReplayFeed(start_cursor=3)
    assert f.compute_realized_volatility("RELIANCE", 5) is None


def test_trend_classification():
    f = _feed_at(80)
    assert f.classify_trend("RELIANCE") in ("UPTREND", "DOWNTREND", "NEUTRAL")


def test_volatility_spike_fires_at_scripted_jump():
    f = MarketReplayFeed(start_cursor=60)
    # Before the jump -> no spike.
    while f.cursor < 80:
        f.advance()
    assert f.detect_volatility_spike("RELIANCE") is False
    # Past the jump -> spike.
    while f.cursor < 94:
        f.advance()
    assert f.detect_volatility_spike("RELIANCE") is True


def test_maybe_spike_once_per_symbol():
    f = MarketReplayFeed(start_cursor=60)
    while f.cursor < 94:
        f.advance()
    assert f.maybe_spike("RELIANCE") is True
    assert f.maybe_spike("RELIANCE") is False  # only announced once


def test_market_facts_shape():
    f = _feed_at(80)
    facts = f.market_facts("RELIANCE")
    for key in ("symbol", "price", "sma", "realized_volatility", "trend"):
        assert key in facts


def test_ohlc_bars():
    f = _feed_at(90)
    bars = f.ohlc("INFY", 10)
    assert len(bars) == 10
    assert {"open", "high", "low", "close"} <= set(bars[0].keys())
