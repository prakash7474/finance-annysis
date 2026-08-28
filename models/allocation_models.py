"""Allocation / trading models for the AI Trading Allocation add-on (paper only)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class Holding(BaseModel):
    symbol: str
    quantity: float
    avg_price: float
    current_price: float
    market_value: float


class AccountSnapshot(BaseModel):
    account_id: str
    account_name: str
    risk_profile: str  # conservative | moderate | aggressive
    currency: str = "INR"
    cash_balance: float
    margin_available: float
    portfolio_value: float
    holdings: List[Holding] = Field(default_factory=list)
    daily_pnl_pct: float = Field(default=0.0)  # used by the circuit breaker


class TradeProposal(BaseModel):
    symbol: str
    side: str  # BUY | SELL
    proposed_quantity: float
    rationale: str
    confidence: str = "MEDIUM"  # LOW | MEDIUM | HIGH
    proposer: str = "ai"


class RuleResult(BaseModel):
    rule: str
    passed: bool
    original_value: Optional[float] = None
    capped_value: Optional[float] = None
    message: str


class FinalAllocationDecision(BaseModel):
    trace_id: str
    account_id: str
    account_name: str
    risk_profile: str
    proposal: TradeProposal
    rules: List[RuleResult] = Field(default_factory=list)
    final_quantity: float
    final_value: float
    status: str  # EXECUTE | RESIZED | REJECTED
    reason: str


class OrderRequest(BaseModel):
    account_id: str
    symbol: str
    side: str
    quantity: float


class PaperOrder(BaseModel):
    order_id: str
    account_id: str
    symbol: str
    side: str
    quantity: float
    requested_price: float
    fill_price: float
    slippage_pct: float
    fill_value: float
    status: str  # FILLED | REJECTED
    fill_time: str
    reason: str = ""


class MarketQuote(BaseModel):
    symbol: str
    price: float
    sma: Optional[float] = None
    realized_volatility: Optional[float] = None
    trend: Optional[str] = None
