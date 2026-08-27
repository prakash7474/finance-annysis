"""
mock_market_adapter.py - Deterministic mock market data for hackathon demo.

Generates realistic-looking OHLC data seeded by symbol name.
"""

import random
from datetime import datetime, timedelta

from market_data_adapter import MarketDataAdapter


# Well-known NSE symbols with approximate base prices
SYMBOL_BASE_PRICES = {
    "RELIANCE": 2450.0,
    "INFY": 1480.0,
    "TCS": 3650.0,
    "HDFCBANK": 1620.0,
    "ICICIBANK": 1250.0,
    "SBIN": 780.0,
    "WIPRO": 460.0,
    "ITC": 475.0,
    "BHARTIARTL": 1550.0,
    "KOTAKBANK": 1780.0,
    "LT": 3400.0,
    "AXISBANK": 1120.0,
    "BAJFINANCE": 6800.0,
    "MARUTI": 12500.0,
    "SUNPHARMA": 1680.0,
    "ADANIENT": 2900.0,
    "TATAMOTORS": 680.0,
    "NIFTY50": 24500.0,
    "SENSEX": 80500.0,
}


class MockMarketAdapter(MarketDataAdapter):
    def __init__(self, seed: int = 42):
        self.seed = seed

    def _rng(self, symbol: str) -> random.Random:
        """Create a deterministic RNG seeded by symbol + base seed."""
        return random.Random(f"{symbol}:{self.seed}")

    def get_latest_price(self, symbol: str) -> float:
        rng = self._rng(symbol)
        base = SYMBOL_BASE_PRICES.get(symbol.upper(), 100 + (abs(hash(symbol)) % 2000))
        noise = rng.uniform(-base * 0.02, base * 0.02)
        return round(base + noise, 2)

    def get_ohlc_history(self, symbol: str, days: int) -> list[dict]:
        rng = self._rng(symbol)
        base = SYMBOL_BASE_PRICES.get(symbol.upper(), 100 + (abs(hash(symbol)) % 2000))

        bars = []
        price = base
        today = datetime.now()

        for i in range(days):
            date = today - timedelta(days=days - i - 1)

            # Skip weekends
            if date.weekday() >= 5:
                continue

            drift = rng.uniform(-base * 0.015, base * 0.015)
            price = max(base * 0.3, price + drift)

            open_ = round(price + rng.uniform(-base * 0.005, base * 0.005), 2)
            intra_high = round(rng.uniform(0, base * 0.01), 2)
            intra_low = round(rng.uniform(0, base * 0.01), 2)
            high_ = round(max(open_, price) + intra_high, 2)
            low_ = round(min(open_, price) - intra_low, 2)
            close_ = round(price, 2)

            bars.append({
                "date": date.strftime("%Y-%m-%d"),
                "open": open_,
                "high": high_,
                "low": low_,
                "close": close_,
            })

        return bars


# Optional: Real adapter using yfinance
class RealYahooAdapter(MarketDataAdapter):
    """Real market data from Yahoo Finance. Requires: pip install yfinance"""

    def get_latest_price(self, symbol: str) -> float:
        try:
            import yfinance as yf
        except ImportError:
            raise ImportError("yfinance not installed. Run: pip install yfinance")

        ticker = yf.Ticker(f"{symbol}.NS")
        hist = ticker.history(period="1d")
        if hist.empty:
            raise ValueError(f"No data for {symbol}")
        return float(hist["Close"].iloc[-1])

    def get_ohlc_history(self, symbol: str, days: int) -> list[dict]:
        try:
            import yfinance as yf
        except ImportError:
            raise ImportError("yfinance not installed. Run: pip install yfinance")

        ticker = yf.Ticker(f"{symbol}.NS")
        hist = ticker.history(period=f"{days}d")
        bars = []
        for ts, row in hist.iterrows():
            bars.append({
                "date": ts.strftime("%Y-%m-%d"),
                "open": round(float(row["Open"]), 2),
                "high": round(float(row["High"]), 2),
                "low": round(float(row["Low"]), 2),
                "close": round(float(row["Close"]), 2),
            })
        return bars
