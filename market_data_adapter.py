"""
market_data_adapter.py - Base class for market data adapters.

Implementations:
  - MockMarketAdapter: deterministic synthetic data (default)
  - RealYahooAdapter: real data via yfinance (optional)
"""

from abc import ABC, abstractmethod
from typing import Any


class MarketDataAdapter(ABC):
    @abstractmethod
    def get_latest_price(self, symbol: str) -> float:
        """Return latest price for a symbol."""
        pass

    @abstractmethod
    def get_ohlc_history(self, symbol: str, days: int) -> list[dict[str, Any]]:
        """
        Return list of daily bars sorted by date ascending:
        [{"date": "2026-08-27", "open": 123.4, "high": 126.7, "low": 122.1, "close": 125.3}, ...]
        """
        pass
