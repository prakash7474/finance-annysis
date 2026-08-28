"""Digital-twin scenario Pydantic models for FinPilot Phase 5."""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field

from models.financial_models import FinancialSnapshot
from models.recommendation_models import MetricChange


class ScenarioInput(BaseModel):
    """Inputs a user can tweak for a financial simulation (the Digital Twin)."""

    salary_change_percentage: float = Field(default=0.0, ge=-100, le=100)
    expense_change_percentage: float = Field(default=0.0, ge=-100, le=100)
    new_loan_amount: float = Field(default=0.0, ge=0)
    new_loan_rate: float = Field(default=12.0, gt=0, lt=100)
    new_loan_tenure: int = Field(default=36, ge=1, le=600)
    additional_monthly_income: float = Field(default=0.0, ge=0)
    additional_monthly_expense: float = Field(default=0.0, ge=0)


class ScenarioResult(BaseModel):
    scenario_id: str
    baseline: FinancialSnapshot
    simulated: FinancialSnapshot
    changes: List[MetricChange] = Field(default_factory=list)
    risk_level: str
    recommendations: List[str] = Field(default_factory=list)
