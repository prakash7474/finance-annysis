"""Finance API routes."""

from __future__ import annotations

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


class DateRange(BaseModel):
    start_date: str = Field(default="2026-08-01")
    end_date: str = Field(default="2026-08-31")


@router.get("/cash-position", response_model=CashPosition)
async def cash_position():
    st = get_state()
    accounts = await st.services.get_accounts()
    transactions = await st.services.get_transactions()
    pos = fe.compute_cash_position(accounts, transactions)
    return CashPosition(**pos)


@router.get("/monthly-summary", response_model=MonthlySummary)
async def monthly_summary(start_date: str = "2026-08-01", end_date: str = "2026-08-31"):
    st = get_state()
    transactions = await st.services.get_transactions(start_date=start_date, end_date=end_date)
    summary = fe.summarize_credit_debit(transactions, start_date, end_date)
    return MonthlySummary(**summary)


@router.get("/emi-summary", response_model=EmiSummary)
async def emi_summary(start_date: str = "2026-08-01", end_date: str = "2026-08-31"):
    st = get_state()
    transactions = await st.services.get_transactions(start_date=start_date, end_date=end_date)
    data = fe.detect_emis(transactions, start_date, end_date)
    return EmiSummary(**data)


@router.get("/emi-ratio", response_model=EmiIncomeRatio)
async def emi_ratio(start_date: str = "2026-08-01", end_date: str = "2026-08-31"):
    st = get_state()
    transactions = await st.services.get_transactions(start_date=start_date, end_date=end_date)
    ratio = fe.compute_emi_income_ratio(transactions, start_date, end_date)
    return EmiIncomeRatio(**ratio)


@router.get("/category-summary", response_model=CategorySummary)
async def category_summary(start_date: str = "2026-08-01", end_date: str = "2026-08-31"):
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
    summary = fe.summarize_credit_debit(transactions, "2026-08-01", "2026-08-31")
    health = compute_health_score(
        monthly_income=baseline["monthly_income"],
        existing_emi=baseline["existing_emi"],
        net_cash=pos["net_cash"],
        total_credit=summary["total_credit"],
        total_debit=summary["total_debit"],
    )
    return FinancialHealthResult(**health)
