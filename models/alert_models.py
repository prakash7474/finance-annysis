"""Alert / market-watch Pydantic models for FinPilot Phase 5."""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class MarketAlert(BaseModel):
    symbol: str
    alert_type: str  # TREND_FLIP | MOMENTUM_FLIP | LARGE_MOVE | SMA_CROSSOVER
    previous_state: str
    current_state: str
    severity: str
    message: str


class FinancialAlert(BaseModel):
    alert_id: str
    trace_id: Optional[str] = None
    timestamp: str
    category: str  # TRANSACTION_ANOMALY | LOW_LIQUIDITY | HIGH_DTI | SPENDING_SPIKE
    #                | GOAL_SHORTFALL | MARKET_CHANGE | DEBT_RISK | FORECAST_RISK
    severity: str  # CRITICAL | HIGH | MEDIUM | LOW | INFO
    title: str
    description: str
    source: str
    recommended_action: Optional[str] = None
