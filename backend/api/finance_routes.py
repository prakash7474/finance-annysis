"""Finance API routes."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter
from pydantic import BaseModel, Field

import finance_engine as fe
from backend.api.deps import error_response, get_state
from backend.governance.tracing import new_id
from backend.schemas.common import StandardErrorCode
from backend.schemas.finance import (
    CashPosition,
    CategorySummary,
    EmiIncomeRatio,
    EmiSummary,
    FinancialHealthResult,
    MonthlySummary,
)

router = APIRouter(prefix="/api/finance", tags=["finance"])


def _current_month_range() -> tuple[str, str]:
    """Return (start_date, end_date) for the current month in YYYY-MM-DD format."""
    today = date.today()
    start = today.replace(day=1).isoformat()
    if today.month == 12:
        end = today.replace(month=12, day=31).isoformat()
    else:
        end = today.replace(month=today.month + 1, day=1).toordinal()
        end = date.fromordinal(end - 1).isoformat()
    return start, end


class DateRange(BaseModel):
    start_date: str = Field(default_factory=lambda: _current_month_range()[0])
    end_date: str = Field(default_factory=lambda: _current_month_range()[1])


@router.get("/cash-position", response_model=CashPosition)
async def cash_position():
    st = get_state()
    accounts = await st.services.get_accounts()
    transactions = await st.services.get_transactions()
    pos = fe.compute_cash_position(accounts, transactions)
    return CashPosition(**pos)


@router.get("/monthly-summary", response_model=MonthlySummary)
async def monthly_summary(start_date: str | None = None, end_date: str | None = None):
    if not start_date or not end_date:
        start_date, end_date = _current_month_range()
    st = get_state()
    transactions = await st.services.get_transactions(start_date=start_date, end_date=end_date)
    summary = fe.summarize_credit_debit(transactions, start_date, end_date)
    return MonthlySummary(**summary)


@router.get("/emi-summary", response_model=EmiSummary)
async def emi_summary(start_date: str | None = None, end_date: str | None = None):
    if not start_date or not end_date:
        start_date, end_date = _current_month_range()
    st = get_state()
    transactions = await st.services.get_transactions(start_date=start_date, end_date=end_date)
    data = fe.detect_emis(transactions, start_date, end_date)
    return EmiSummary(**data)


@router.get("/emi-ratio", response_model=EmiIncomeRatio)
async def emi_ratio(start_date: str | None = None, end_date: str | None = None):
    if not start_date or not end_date:
        start_date, end_date = _current_month_range()
    st = get_state()
    transactions = await st.services.get_transactions(start_date=start_date, end_date=end_date)
    ratio = fe.compute_emi_income_ratio(transactions, start_date, end_date)
    return EmiIncomeRatio(**ratio)


@router.get("/category-summary", response_model=CategorySummary)
async def category_summary(start_date: str | None = None, end_date: str | None = None):
    if not start_date or not end_date:
        start_date, end_date = _current_month_range()
    st = get_state()
    transactions = await st.services.get_transactions(start_date=start_date, end_date=end_date)
    data = fe.get_category_summary(transactions, start_date, end_date)
    return CategorySummary(**data)


@router.get("/transactions")
async def transactions(account_id: str | None = None,
                       start_date: str | None = None,
                       end_date: str | None = None):
    st = get_state()
    txns = await st.services.get_transactions(account_id=account_id,
                                              start_date=start_date, end_date=end_date)
    return {"transactions": sorted(txns, key=lambda t: t["date"], reverse=True)}


@router.get("/health-score", response_model=FinancialHealthResult)
async def health_score():
    from health_engine import compute_health_score

    st = get_state()
    accounts = await st.services.get_accounts()
    transactions = await st.services.get_transactions()
    pos = fe.compute_cash_position(accounts, transactions)
    baseline = st.services.baseline
    month_start, month_end = _current_month_range()
    summary = fe.summarize_credit_debit(transactions, month_start, month_end)
    health = compute_health_score(
        monthly_income=baseline["monthly_income"],
        existing_emi=baseline["existing_emi"],
        net_cash=pos["net_cash"],
        total_credit=summary["total_credit"],
        total_debit=summary["total_debit"],
    )
    return FinancialHealthResult(**health)
