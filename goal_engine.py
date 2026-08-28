"""
goal_engine.py - Deterministic financial goal planning.

Computes the required monthly saving for a target, the current saving capacity
and any shortfall.  Never provides an unsupported guarantee.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from models.financial_models import FinancialGoal


def plan_financial_goal(
    target_amount: float,
    current_saved_amount: float,
    months_remaining: int,
    monthly_income: float,
    monthly_expenses: float,
    monthly_emi: float,
    name: str = "Savings Goal",
    goal_id: Optional[str] = None,
) -> FinancialGoal:
    """Plan a savings goal deterministically."""
    import uuid

    goal_id = goal_id or f"goal_{uuid.uuid4().hex[:10]}"

    if target_amount <= 0 or months_remaining <= 0:
        return FinancialGoal(
            goal_id=goal_id, name=name, target_amount=target_amount,
            current_saved_amount=current_saved_amount, remaining_amount=0.0,
            months_remaining=max(months_remaining, 0), required_monthly_saving=0.0,
            current_saving_capacity=max(0.0, monthly_income - monthly_expenses - monthly_emi),
            monthly_shortfall=0.0, status="INVALID",
        )

    remaining = max(0.0, target_amount - current_saved_amount)
    required_monthly = remaining / months_remaining if months_remaining else 0.0
    saving_capacity = max(0.0, monthly_income - monthly_expenses - monthly_emi)
    shortfall = max(0.0, required_monthly - saving_capacity)

    if current_saved_amount >= target_amount:
        status = "COMPLETED"
    elif shortfall > 0:
        status = "SHORTFALL"
    else:
        status = "ON_TRACK"

    return FinancialGoal(
        goal_id=goal_id, name=name, target_amount=target_amount,
        current_saved_amount=current_saved_amount, remaining_amount=round(remaining, 2),
        months_remaining=int(months_remaining),
        required_monthly_saving=round(required_monthly, 2),
        current_saving_capacity=round(saving_capacity, 2),
        monthly_shortfall=round(shortfall, 2), status=status,
    )
