"""Loan API routes."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import ValidationError as PydanticValidationError

import loan_engine as le
from backend.api.deps import error_response, get_state
from backend.governance.tracing import new_id
from backend.schemas.common import StandardErrorCode
from backend.schemas.loans import (
    CompareLoansRequest,
    LoanComparisonResult,
    LoanRequest,
    LoanResult,
    ScenarioRequest,
    ScenarioResult,
)

router = APIRouter(tags=["loan"])


@router.post("/api/loan/analyze", response_model=LoanResult)
async def analyze_loan(req: LoanRequest):
    result = le.assess_loan_risk(
        principal=req.amount,
        annual_rate_pct=req.rate,
        tenure_months=req.tenure_months,
        monthly_income=req.monthly_income,
        existing_monthly_emi=req.existing_emi,
        processing_fee_pct=req.processing_fee_pct,
    )
    return LoanResult(**result)


@router.post("/api/loan/compare", response_model=LoanComparisonResult)
async def compare_loans(req: CompareLoansRequest):
    st = get_state()
    offers = await st.services.get_loan_offers()
    if req.banks:
        bank_list = [b.strip().upper() for b in req.banks]
        offers = [o for o in offers if any(bank in o["bank"].upper() for bank in bank_list)]
    results = le.compare_loan_offers(req.amount, offers, req.monthly_income, req.existing_emi)

    best_cost = min(results, key=lambda x: x["total_cost"]) if results else None
    lowest_risk = min(results, key=lambda x: {"LOW": 0, "MEDIUM": 1, "HIGH": 2}[x["risk_level"]]) if results else None
    items = []
    for i, r in enumerate(results, 1):
        items.append({
            **{k: r[k] for k in ("offer_id", "bank", "product", "interest_rate", "tenure_months",
                                 "emi", "total_cost", "total_interest", "processing_fee",
                                 "emi_income_ratio", "risk_level")},
            "rank": i,
            "is_best_cost": bool(best_cost) and r["offer_id"] == best_cost["offer_id"],
            "is_lowest_risk": bool(lowest_risk) and r["offer_id"] == lowest_risk["offer_id"],
        })
    return LoanComparisonResult(
        amount=req.amount, monthly_income=req.monthly_income, existing_emi=req.existing_emi,
        offers=items, best_by_cost=items[0] if items else None,
        lowest_risk=next((i for i in items if i["is_lowest_risk"]), None),
    )


@router.post("/api/scenario", response_model=ScenarioResult)
async def scenario(req: ScenarioRequest):
    from scenario_engine import Scenario, ScenarioDelta, apply_scenario

    st = get_state()
    baseline = st.services.baseline
    scenario = Scenario(
        monthly_income=req.monthly_income or baseline["monthly_income"],
        existing_emi=req.existing_emi or baseline["existing_emi"],
        net_cash=req.net_cash,
        total_credit=req.total_credit,
        total_debit=req.total_debit,
        loan_amount=req.loan_amount,
        loan_rate=req.rate,
        loan_tenure_months=req.tenure_months,
    )
    delta = ScenarioDelta(
        salary_change_percent=req.salary_change_percent,
        existing_emi_change_percent=req.existing_emi_change_percent,
        large_expense=req.large_expense,
    )
    result = apply_scenario(scenario, delta)
    return ScenarioResult(**result)
