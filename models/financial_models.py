"""Shared Pydantic models for FinPilot Phase 5 (financial intelligence)."""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class FinancialHealthScore(BaseModel):
    """Deterministic financial health score (Gemini never computes this)."""

    score: float
    status: str  # EXCELLENT | HEALTHY | MODERATE | AT_RISK | CRITICAL
    liquidity_score: float
    debt_score: float
    expense_score: float
    savings_score: float
    reasons: List[str] = Field(default_factory=list)


class CashFlowForecast(BaseModel):
    forecast_date: str
    projected_balance: float
    projected_income: float
    projected_expenses: float
    projected_emi: float
    confidence: float
    risk_level: str
    days: int


class SpendingForecast(BaseModel):
    category: str
    historical_average: float
    projected_amount: float
    change_percentage: float
    risk_level: str


class TransactionAnomaly(BaseModel):
    transaction_id: str
    amount: float
    category: str
    expected_amount: float
    deviation_percentage: float
    severity: str  # NORMAL | LOW | MEDIUM | HIGH | CRITICAL
    reason: str


class FinancialGoal(BaseModel):
    goal_id: str
    name: str
    target_amount: float
    current_saved_amount: float
    target_date: Optional[str] = None
    remaining_amount: float
    months_remaining: int
    required_monthly_saving: float
    current_saving_capacity: float
    monthly_shortfall: float
    status: str  # COMPLETED | ON_TRACK | SHORTFALL | INVALID


class DebtInput(BaseModel):
    """A debt/loan line item used by the debt optimizer."""

    loan_id: str
    bank: str
    principal: float
    interest_rate: float
    tenure_months: int
    existing_monthly_emi: float = 0.0


class DebtRecommendation(BaseModel):
    loan_id: str
    priority: int
    strategy: str
    reason_codes: List[str] = Field(default_factory=list)
    estimated_interest: float
    monthly_emi: float
    dti_impact: float
    bank: str = ""
    interest_rate: float = 0.0
    tenure_months: int = 0


class FinancialSnapshot(BaseModel):
    """A point-in-time financial state (used by the Digital Twin)."""

    monthly_income: float
    monthly_expenses: float
    existing_emi: float
    net_cash: float
    dti: Optional[float] = None
    new_emi: Optional[float] = None
    cash_flow: Optional[float] = None
    health_score: Optional[float] = None
    risk_level: Optional[str] = None


class TradeSignal(BaseModel):
    symbol: str
    signal: str
