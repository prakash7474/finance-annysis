"""Market-domain Pydantic schemas."""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class MarketQuote(BaseModel):
    symbol: str
    price: float


class OHLCRow(BaseModel):
    date: str
    open: float
    high: float
    low: float
    close: float


class OHLCResult(BaseModel):
    symbol: str
    bars: List[OHLCRow]
    count: int


class TrendResult(BaseModel):
    symbol: Optional[str] = None
    latest_close: Optional[float] = None
    sma: Optional[float] = None
    trend: str
    pct_diff: Optional[float] = None
    sma_days: Optional[int] = None


class MomentumResult(BaseModel):
    symbol: Optional[str] = None
    momentum_pct: float
    lookback_days: int
    older_close: float
    latest_close: float


class HighLowRange(BaseModel):
    high: float
    low: float
    range_pct: float
    days: int


class MarketQuery(BaseModel):
    symbol: str = Field(min_length=1, max_length=20)
    days: Optional[int] = Field(default=None, ge=1, le=500)
    sma_days: Optional[int] = Field(default=20, ge=2, le=250)
    lookback_days: Optional[int] = Field(default=10, ge=1, le=250)
