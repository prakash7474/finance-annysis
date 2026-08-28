"""
digital_twin.py - Financial Digital Twin (temporary simulation).

Simulates a user's financial state under a set of changes and returns a
baseline-vs-simulated comparison.  It NEVER mutates real/mock balances or
transactions: it works on a copy of the snapshot and returns new values.
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List

import loan_engine as le
from health_engine import compute_financial_health
from models.financial_models import FinancialSnapshot
from models.recommendation_models import MetricChange
from models.scenario_models import ScenarioInput, ScenarioResult


def _risk_from_dti(dti: float, status: str) -> str:
    if dti > 0.5 or status == "CRITICAL":
        return "CRITICAL"
    if dti > 0.4 or status == "AT_RISK":
        return "HIGH"
    if dti > 0.3 or status == "MODERATE":
        return "MODERATE"
    return "LOW"


def _recommendations(income: float, expenses: float, emi_burden: float, dti: float,
                     cash: float) -> List[str]:
    recs: List[str] = []
    if dti > 0.4:
        recs.append("Debt-to-income ratio is elevated; consider avoiding additional borrowing.")
    saving = income - expenses - emi_burden
    if saving <= 0:
        recs.append("Monthly saving capacity is non-positive; reduce discretionary spending.")
    if cash < 0:
        recs.append("Projected cash is negative; build a liquidity buffer.")
    if not recs:
        recs.append("The simulated scenario remains within healthy bounds.")
    return recs


def simulate_financial_scenario(baseline: FinancialSnapshot, scenario: ScenarioInput) -> ScenarioResult:
    """Run a temporary simulation. ``baseline`` is never mutated."""
    # Baseline health (from a copy of the input snapshot).
    base_health = compute_financial_health(
        monthly_income=baseline.monthly_income,
        monthly_expenses=baseline.monthly_expenses,
        existing_emi=baseline.existing_emi,
        net_cash=baseline.net_cash,
        new_emi=baseline.new_emi or 0.0,
    )
    base_dti = baseline.dti if baseline.dti is not None else (
        (baseline.existing_emi + (baseline.new_emi or 0.0)) / baseline.monthly_income
        if baseline.monthly_income > 0 else 0.0
    )
    base_flow = baseline.cash_flow if baseline.cash_flow is not None else (
        baseline.monthly_income - baseline.monthly_expenses - baseline.existing_emi - (baseline.new_emi or 0.0)
    )

    base_snapshot = FinancialSnapshot(
        monthly_income=round(baseline.monthly_income, 2),
        monthly_expenses=round(baseline.monthly_expenses, 2),
        existing_emi=round(baseline.existing_emi, 2),
        net_cash=round(baseline.net_cash, 2),
        dti=round(base_dti, 4),
        new_emi=round(baseline.new_emi or 0.0, 2),
        cash_flow=round(base_flow, 2),
        health_score=base_health["score"],
        risk_level=_risk_from_dti(base_dti, base_health["status"]),
    )

    # Apply scenario changes (all on new values - never mutate baseline).
    new_income = max(0.0, baseline.monthly_income * (1 + scenario.salary_change_percentage / 100.0)
                     + scenario.additional_monthly_income)
    new_expenses = max(0.0, baseline.monthly_expenses * (1 + scenario.expense_change_percentage / 100.0)
                       + scenario.additional_monthly_expense)
    new_loan_emi = le.calculate_emi(scenario.new_loan_amount, scenario.new_loan_rate,
                                    scenario.new_loan_tenure) if scenario.new_loan_amount > 0 else 0.0
    emi_burden = baseline.existing_emi + new_loan_emi
    new_dti = (emi_burden / new_income) if new_income > 0 else 99.0
    new_flow = new_income - new_expenses - baseline.existing_emi - new_loan_emi

    sim_health = compute_financial_health(
        monthly_income=new_income, monthly_expenses=new_expenses,
        existing_emi=baseline.existing_emi, net_cash=baseline.net_cash, new_emi=new_loan_emi,
    )

    simulated = FinancialSnapshot(
        monthly_income=round(new_income, 2),
        monthly_expenses=round(new_expenses, 2),
        existing_emi=round(baseline.existing_emi, 2),
        net_cash=round(baseline.net_cash, 2),
        dti=round(new_dti, 4),
        new_emi=round(new_loan_emi, 2),
        cash_flow=round(new_flow, 2),
        health_score=sim_health["score"],
        risk_level=_risk_from_dti(new_dti, sim_health["status"]),
    )

    changes = [
        _change("monthly_income", base_snapshot.monthly_income, simulated.monthly_income),
        _change("monthly_expenses", base_snapshot.monthly_expenses, simulated.monthly_expenses),
        _change("new_emi", base_snapshot.new_emi, simulated.new_emi),
        _change("dti", base_snapshot.dti, simulated.dti),
        _change("cash_flow", base_snapshot.cash_flow, simulated.cash_flow),
        _change("health_score", base_snapshot.health_score, simulated.health_score),
    ]

    return ScenarioResult(
        scenario_id=f"scn_{uuid.uuid4().hex[:10]}",
        baseline=base_snapshot,
        simulated=simulated,
        changes=changes,
        risk_level=simulated.risk_level,
        recommendations=_recommendations(new_income, new_expenses, emi_burden, new_dti, baseline.net_cash),
    )


def _change(metric: str, before: float, after: float) -> MetricChange:
    if before:
        pct = round((after - before) / abs(before) * 100.0, 2)
    else:
        pct = None
    return MetricChange(metric=metric, before=round(before, 2), after=round(after, 2), change_percentage=pct)
