"""Loan-domain Pydantic schemas (with strict validation)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, model_validator


class LoanRequest(BaseModel):
    amount: float = Field(gt=0, description="Loan principal in INR")
    rate: float = Field(gt=0, lt=100, description="Annual interest rate (%)")
    tenure_months: int = Field(gt=0, le=600, description="Loan tenure in months")
    monthly_income: float = Field(ge=0)
    existing_emi: float = Field(default=0.0, ge=0)
    processing_fee_pct: float = Field(default=0.0, ge=0, lt=100)

    @model_validator(mode="after")
    def _reject_non_positive(self):
        if self.amount <= 0:
            raise ValueError("loan amount must be positive")
        if self.tenure_months <= 0:
            raise ValueError("tenure must be a positive number of months")
        return self


class LoanResult(BaseModel):
    emi: float
    total_interest: float
    total_cost: float
    processing_fee: float
    emi_income_ratio: float
    risk_level: str
    risk_flags: List[Dict[str, Any]] = Field(default_factory=list)
    total_payment: Optional[float] = None


class LoanOffer(BaseModel):
    offer_id: str
    bank: str
    product: str
    interest_rate: float
    tenure_months: int
    processing_fee_pct: float = 0.0


class CompareLoansRequest(BaseModel):
    amount: float = Field(gt=0)
    monthly_income: float = Field(ge=0)
    existing_emi: float = Field(default=0.0, ge=0)
    banks: List[str] = Field(default_factory=list)


class LoanComparisonItem(BaseModel):
    offer_id: str
    bank: str
    product: str
    interest_rate: float
    tenure_months: int
    emi: float
    total_cost: float
    total_interest: float
    processing_fee: float
    emi_income_ratio: float
    risk_level: str
    rank: int
    is_best_cost: bool = False
    is_lowest_risk: bool = False


class LoanComparisonResult(BaseModel):
    amount: float
    monthly_income: float
    existing_emi: float
    offers: List[LoanComparisonItem]
    best_by_cost: Optional[LoanComparisonItem] = None
    lowest_risk: Optional[LoanComparisonItem] = None


class ScenarioRequest(BaseModel):
    loan_amount: float = Field(gt=0, description="Loan amount in INR")
    tenure_months: int = Field(gt=0, le=600)
    rate: float = Field(gt=0, lt=100)
    monthly_income: float = Field(ge=0)
    existing_emi: float = Field(default=0.0, ge=0)
    net_cash: float = Field(default=0.0)
    total_credit: float = Field(default=0.0, ge=0)
    total_debit: float = Field(default=0.0, ge=0)
    salary_change_percent: float = Field(default=0.0, ge=-100)
    existing_emi_change_percent: float = Field(default=0.0, ge=-100)
    large_expense: float = Field(default=0.0, ge=0)
    tenure_change_percent: Optional[float] = None

    @model_validator(mode="after")
    def _validate(self):
        if self.loan_amount <= 0:
            raise ValueError("loan_amount must be positive")
        if self.tenure_months <= 0:
            raise ValueError("tenure_months must be positive")
        return self


class ScenarioResult(BaseModel):
    current: Dict[str, Any]
    scenario: Dict[str, Any]
    delta: Dict[str, Any]
    scenario_health: Dict[str, Any]
