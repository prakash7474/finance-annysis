"""
scenario_engine.py - Deterministic what-if scenario simulator.

Given a current financial profile and a set of user-chosen changes (a "what-if"),
it recomputes EMI, DTI, risk, remaining cash and the health score entirely with
deterministic engine functions.  The LLM is never involved in the arithmetic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict

import loan_engine as le
from health_engine import HealthScoreConfig, compute_health_score


@dataclass
class Scenario:
    """Current financial profile (baseline)."""

    monthly_income: float
    existing_emi: float
    net_cash: float
    total_credit: float
    total_debit: float
    loan_amount: float = 0.0
    loan_rate: float = 0.0
    loan_tenure_months: int = 0


@dataclass
class ScenarioDelta:
    """Overrides / changes to apply (what-if)."""

    salary_change_percent: float = 0.0
    loan_amount: float | None = None
    loan_rate: float | None = None
    loan_tenure_months: int | None = None
    existing_emi_change_percent: float = 0.0
    large_expense: float = 0.0
    extra_debit_percent: float = 0.0


def apply_scenario(
    scenario: Scenario,
    delta: ScenarioDelta,
    config: HealthScoreConfig | None = None,
) -> Dict[str, Any]:
    """Compute the deterministic current-vs-scenario result."""
    base_emi = le.calculate_emi(scenario.loan_amount, scenario.loan_rate, scenario.loan_tenure_months)

    # Apply delta
    new_income = scenario.monthly_income * (1 + delta.salary_change_percent / 100.0)
    new_loan_amount = delta.loan_amount if delta.loan_amount is not None else scenario.loan_amount
    new_rate = delta.loan_rate if delta.loan_rate is not None else scenario.loan_rate
    new_tenure = delta.loan_tenure_months if delta.loan_tenure_months is not None else scenario.loan_tenure_months
    new_existing_emi = scenario.existing_emi * (1 + delta.existing_emi_change_percent / 100.0)
    new_existing_emi = max(new_existing_emi, 0.0)

    new_emi = le.calculate_emi(new_loan_amount, new_rate, new_tenure)
    new_total_emi_burden = new_existing_emi + new_emi

    # Deterministic loan risk for the scenario.
    risk = le.assess_loan_risk(
        principal=new_loan_amount,
        annual_rate_pct=new_rate,
        tenure_months=new_tenure,
        monthly_income=new_income,
        existing_monthly_emi=new_existing_emi,
    )

    dti_ratio = (new_total_emi_burden / new_income) if new_income > 0 else 0.0

    # Remaining cash after the large expense and the first EMI.
    scenario_cash = scenario.net_cash - delta.large_expense - new_emi
    scenario_credit = scenario.total_credit
    scenario_debit = scenario.total_debit * (1 + delta.extra_debit_percent / 100.0) + delta.large_expense

    scenario_health = compute_health_score(
        monthly_income=new_income,
        existing_emi=new_existing_emi,
        net_cash=scenario_cash,
        total_credit=scenario_credit,
        total_debit=scenario_debit,
        new_emi=new_emi,
        config=config,
    )

    base_health = compute_health_score(
        monthly_income=scenario.monthly_income,
        existing_emi=scenario.existing_emi,
        net_cash=scenario.net_cash,
        total_credit=scenario.total_credit,
        total_debit=scenario.total_debit,
        new_emi=base_emi if scenario.loan_amount else 0.0,
        config=config,
    )

    def _risk_value(level: str) -> int:
        return {"HEALTHY": 0, "MODERATE": 1, "HIGH": 2, "CRITICAL": 3}.get(level, 0)

    return {
        "current": {
            "monthly_income": round(scenario.monthly_income, 2),
            "existing_emi": round(scenario.existing_emi, 2),
            "loan_amount": round(scenario.loan_amount, 2),
            "loan_rate": scenario.loan_rate,
            "loan_tenure_months": scenario.loan_tenure_months,
            "emi": round(base_emi, 2),
            "dti_ratio": round(
                ((scenario.existing_emi + base_emi) / scenario.monthly_income)
                if scenario.monthly_income > 0 else 0, 4
            ),
            "risk": risk["risk_level"] if scenario.loan_amount else "N/A",
            "health_score": base_health["overall_score"],
            "health_risk": base_health["risk_level"],
            "remaining_cash": round(scenario.net_cash, 2),
        },
        "scenario": {
            "monthly_income": round(new_income, 2),
            "existing_emi": round(new_existing_emi, 2),
            "loan_amount": round(new_loan_amount, 2),
            "loan_rate": new_rate,
            "loan_tenure_months": new_tenure,
            "emi": round(new_emi, 2),
            "dti_ratio": round(dti_ratio, 4),
            "risk": risk["risk_level"],
            "health_score": scenario_health["overall_score"],
            "health_risk": scenario_health["risk_level"],
            "remaining_cash": round(scenario_cash, 2),
        },
        "delta": {
            "income_change": round(new_income - scenario.monthly_income, 2),
            "income_change_percent": round(delta.salary_change_percent, 2),
            "emi_change": round(new_emi - base_emi, 2),
            "dti_change": round((dti_ratio - base_health["dti_ratio"]) * 100, 2)
            if base_health["dti_ratio"] is not None else 0.0,
            "health_change": round(scenario_health["overall_score"] - base_health["overall_score"], 2),
            "risk_change": _risk_value(scenario_health["risk_level"]) - _risk_value(base_health["risk_level"]),
        },
        "scenario_health": scenario_health,
    }
