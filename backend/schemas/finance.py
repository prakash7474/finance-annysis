"""Finance-domain Pydantic schemas."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AccountBalance(BaseModel):
    account_id: str
    account_name: str
    account_type: str
    balance: float


class CashPosition(BaseModel):
    accounts: List[AccountBalance]
    net_cash: float


class MonthlySummary(BaseModel):
    start_date: str
    end_date: str
    total_credit: float
    total_debit: float
    net_change: float
    transaction_count: int


class EmiEntry(BaseModel):
    txn_id: str
    date: str
    description: str
    amount: float
    category: str


class EmiSummary(BaseModel):
    start_date: str
    end_date: str
    total_emi: float
    emi_count: int
    emi_breakdown: Dict[str, float]
    emis: List[EmiEntry] = Field(default_factory=list)


class EmiIncomeRatio(BaseModel):
    total_emi: float
    total_income: float
    emi_income_ratio_pct: float
    is_stressed: bool


class CategorySummary(BaseModel):
    start_date: str
    end_date: str
    categories: Dict[str, Dict[str, Any]]


class FinancialHealthResult(BaseModel):
    cash_score: float
    emi_score: float
    dti_score: float
    liquidity_score: float
    overall_score: float
    risk_level: str
    warnings: List[str] = Field(default_factory=list)
    dti_ratio: Optional[float] = None
    emi_ratio: Optional[float] = None
    cash_months: Optional[float] = None
    savings_rate: Optional[float] = None


class FinanceMetrics(BaseModel):
    """Aggregate finance facts used for dashboard and narration."""

    monthly_income: float
    existing_emi: float
    net_cash: float
    total_credit: float
    total_debit: float
    health: Optional[FinancialHealthResult] = None
