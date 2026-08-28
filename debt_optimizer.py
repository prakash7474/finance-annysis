"""
debt_optimizer.py - Deterministic debt payoff prioritisation.

Analyses each loan/EMI and ranks them by a chosen objective (strategy).  It never
claims a strategy is *guaranteed* optimal beyond the defined objective.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import loan_engine as le
from models.financial_models import DebtInput, DebtRecommendation

STRATEGIES = ["LOWEST_TOTAL_COST", "LOWEST_INTEREST", "LOWEST_MONTHLY_EMI",
              "FASTEST_DEBT_REDUCTION", "LOWEST_DTI"]


def _metrics(loan: DebtInput, monthly_income: float, existing_emi: float) -> Dict[str, float]:
    emi = le.calculate_emi(loan.principal, loan.interest_rate, loan.tenure_months)
    total_payment = emi * loan.tenure_months
    total_interest = total_payment - loan.principal
    total_cost = total_payment + loan.existing_monthly_emi
    dti_burden = (loan.existing_monthly_emi + emi + existing_emi) / monthly_income if monthly_income > 0 else 99.0
    return {
        "emi": round(emi, 2),
        "total_payment": round(total_payment, 2),
        "total_interest": round(total_interest, 2),
        "total_cost": round(total_cost, 2),
        "dti_burden": round(dti_burden, 4),
    }


def _reason_codes(loan: DebtInput, m: Dict[str, float], monthly_income: float) -> List[str]:
    codes = []
    if loan.interest_rate >= 12:
        codes.append("HIGH_INTEREST_RATE")
    if loan.tenure_months > 36:
        codes.append("LONG_TENURE")
    if m["dti_burden"] > 0.3:
        codes.append("HIGH_DTI_IMPACT")
    if m["total_interest"] > loan.principal * 0.10:
        codes.append("HIGH_TOTAL_INTEREST")
    if monthly_income > 0 and m["emi"] > 0.3 * monthly_income:
        codes.append("HIGH_EMI_BURDEN")
    return codes


def optimize_debt(
    loans: List[DebtInput],
    monthly_income: float,
    existing_emi: float = 0.0,
    strategy: str = "LOWEST_TOTAL_COST",
) -> List[DebtRecommendation]:
    """Rank loans by the chosen ``strategy`` (priority 1 = act first).

    Strategy semantics:
      LOWEST_TOTAL_COST       : smallest total cost (principal + interest + fee)
      LOWEST_INTEREST          : lowest interest rate
      LOWEST_MONTHLY_EMI       : smallest EMI
      FASTEST_DEBT_REDUCTION   : shortest remaining tenure
      LOWEST_DTI               : smallest DTI contribution
    """
    if not loans:
        return []

    enrich = []
    for loan in loans:
        m = _metrics(loan, monthly_income, existing_emi)
        enrich.append({"loan": loan, "metrics": m, "codes": _reason_codes(loan, m, monthly_income)})

    # Value used to order each strategy (lower = more urgent to act on).
    def sort_key(item):
        loan = item["loan"]
        m = item["metrics"]
        if strategy == "LOWEST_INTEREST":
            return loan.interest_rate
        if strategy == "LOWEST_MONTHLY_EMI":
            return m["emi"]
        if strategy == "FASTEST_DEBT_REDUCTION":
            return loan.tenure_months
        if strategy == "LOWEST_DTI":
            return m["dti_burden"]
        return m["total_cost"]  # LOWEST_TOTAL_COST (default)

    enrich.sort(key=sort_key)

    recommendations = []
    for i, item in enumerate(enrich, 1):
        loan = item["loan"]
        m = item["metrics"]
        recommendations.append(DebtRecommendation(
            loan_id=loan.loan_id,
            priority=i,
            strategy=strategy,
            reason_codes=item["codes"],
            estimated_interest=m["total_interest"],
            monthly_emi=m["emi"],
            dti_impact=m["dti_burden"],
            bank=loan.bank,
            interest_rate=loan.interest_rate,
            tenure_months=loan.tenure_months,
        ))
    return recommendations


def all_strategy_rankings(loans: List[DebtInput], monthly_income: float,
                          existing_emi: float = 0.0) -> Dict[str, List[str]]:
    """Return loan_ids ranked per strategy."""
    rankings = {}
    for strategy in STRATEGIES:
        result = optimize_debt(loans, monthly_income, existing_emi, strategy)
        rankings[strategy] = [r.loan_id for r in result]
    return rankings
