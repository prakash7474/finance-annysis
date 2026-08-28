"""
forecast_engine.py - Deterministic short-term cash-flow and spending forecasting.

Forecasts are projections from historical averages and known recurring
obligations.  They are NOT guarantees and are clearly labelled as such.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime
from statistics import fmean
from typing import Any, Dict, List, Optional

from models.financial_models import CashFlowForecast, SpendingForecast

LIQUIDITY_MIN = 25000.0


def _parse_date(value: str) -> date:
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return date.today()


def aggregate_monthly_cash(transactions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Aggregate monthly credit, debit and recurring EMI from transactions."""
    income_cats = {"SALARY", "FREELANCE", "INTEREST", "DIVIDEND"}
    total_credit = 0.0
    total_debit = 0.0
    emi_by_lender: Dict[str, float] = {}
    for t in transactions:
        amt = float(t.get("amount") or 0)
        is_emi = t.get("category") == "LOAN_EMI" or "EMI" in str(t.get("description", "")).upper()
        if is_emi:
            desc = str(t.get("description", "")).split(" - ", 1)
            lender = desc[1].strip() if len(desc) > 1 else str(t.get("description", "UNKNOWN"))
            emi_by_lender[lender] = amt
        if t.get("type") == "CREDIT":
            total_credit += amt
        else:
            total_debit += amt
    return {
        "total_credit": round(total_credit, 2),
        "total_debit": round(total_debit, 2),
        "recurring_emi": round(sum(emi_by_lender.values()), 2),
        "emi_breakdown": emi_by_lender,
    }


def forecast_cash_flow(
    current_balance: float,
    monthly_income: float,
    monthly_expenses: float,
    monthly_emi: float,
    days: int = 30,
) -> CashFlowForecast:
    """Project cash flow over ``days`` using monthly aggregates."""
    days = max(1, int(days))
    factor = days / 30.0
    projected_income = monthly_income * factor
    projected_expenses = monthly_expenses * factor
    projected_emi = monthly_emi * factor
    projected_balance = current_balance + projected_income - projected_expenses - projected_emi

    risk_level = "LOW"
    if projected_balance < 0:
        risk_level = "CRITICAL"
    elif projected_balance < LIQUIDITY_MIN:
        risk_level = "HIGH"
    elif projected_balance < LIQUIDITY_MIN * 2:
        risk_level = "MEDIUM"

    confidence = {7: 0.7, 14: 0.6, 30: 0.5, 60: 0.4, 90: 0.3}.get(days, 0.5)

    return CashFlowForecast(
        forecast_date=date.today().isoformat(),
        projected_balance=round(projected_balance, 2),
        projected_income=round(projected_income, 2),
        projected_expenses=round(projected_expenses, 2),
        projected_emi=round(projected_emi, 2),
        confidence=confidence,
        risk_level=risk_level,
        days=days,
    )


def forecast_spending(
    transactions: List[Dict[str, Any]],
    days: int = 30,
    monthly_income: Optional[float] = None,
    categories: Optional[List[str]] = None,
) -> List[SpendingForecast]:
    """Project spending per category over ``days``."""
    if not transactions:
        return []

    dates = [_parse_date(t.get("date")) for t in transactions]
    start = min(dates)
    end = max(dates)
    window_days = max((end - start).days + 1, 1)

    debits = [t for t in transactions if t.get("type") == "DEBIT" and float(t.get("amount") or 0) > 0]
    if not debits:
        return []

    total_by_cat: Dict[str, float] = defaultdict(float)
    for t in debits:
        cat = t.get("category") or "UNCATEGORIZED"
        if categories and cat not in categories:
            continue
        total_by_cat[cat] += float(t.get("amount") or 0)

    # Per-category daily rate -> normalize to a monthly average.
    results: List[SpendingForecast] = []
    for cat, total in total_by_cat.items():
        daily_rate = total / window_days
        historical_avg = daily_rate * 30.0
        projected = daily_rate * days
        change_pct = 0.0
        risk = "LOW"
        if monthly_income and monthly_income > 0:
            share = projected / monthly_income if monthly_income else 0
            if share > 0.5:
                risk = "HIGH"
            elif share > 0.3:
                risk = "MEDIUM"
        results.append(SpendingForecast(
            category=cat,
            historical_average=round(historical_avg, 2),
            projected_amount=round(projected, 2),
            change_percentage=round(change_pct, 2),
            risk_level=risk,
        ))

    results.sort(key=lambda r: r.projected_amount, reverse=True)
    return results
