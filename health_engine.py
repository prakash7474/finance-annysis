"""
health_engine.py - Deterministic financial health scoring.

The LLM (Gemini) is never asked to compute these values.  The health score is
derived purely from validated financial facts using configurable rules.

Score components (each 0-100):
  - cash_score      : based on net monthly cash-flow (credit minus debit)
  - emi_score       : based on the recurring EMI burden relative to income
  - dti_score       : based on the Debt-To-Income ratio
  - liquidity_score : based on months of cash runway against income

The overall score is a weighted average of the components.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

# Sub-component weights (configurable).
DEFAULT_WEIGHTS: Dict[str, float] = {
    "cash": 0.25,
    "emi": 0.20,
    "dti": 0.35,
    "liquidity": 0.20,
}


def _clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, value))


@dataclass
class HealthScoreConfig:
    """Configurable rules / weights for the financial health score."""

    weights: Dict[str, float] = field(default_factory=lambda: dict(DEFAULT_WEIGHTS))
    dti_healthy: float = 0.30
    dti_moderate: float = 0.40
    dti_high: float = 0.50
    target_cash_months: float = 3.0


def dti_score_component(dti_ratio: float, config: HealthScoreConfig) -> float:
    """Map a DTI ratio to a 0-100 score using the configured bands."""
    if dti_ratio <= config.dti_healthy:
        return 100.0
    if dti_ratio <= config.dti_moderate:
        # healthy(100) -> moderate(70)
        span = config.dti_moderate - config.dti_healthy
        frac = (dti_ratio - config.dti_healthy) / span if span else 1.0
        return _clamp(100.0 - frac * 30.0)
    if dti_ratio <= config.dti_high:
        # moderate(70) -> high(40)
        span = config.dti_high - config.dti_moderate
        frac = (dti_ratio - config.dti_moderate) / span if span else 1.0
        return _clamp(70.0 - frac * 30.0)
    # critical (>50%)
    return 15.0


def emi_score_component(emi_ratio: float, config: HealthScoreConfig) -> float:
    """Map an EMI/income ratio to a 0-100 score."""
    # EMI burden is treated with the same bands as DTI by default.
    return dti_score_component(emi_ratio, config)


def cash_score_component(savings_rate: float) -> float:
    """Map a savings rate (credit-debit)/credit to a 0-100 score."""
    if savings_rate >= 0.20:
        return 100.0
    if savings_rate >= 0.0:
        return _clamp(100.0 + savings_rate * 250.0)  # 0.0 -> 100, 0.2 -> 150->clamp 100
    # negative savings rate -> down to 30
    return _clamp(100.0 + savings_rate * 350.0)  # -0.2 -> 30


def liquidity_score_component(cash_months: float, config: HealthScoreConfig) -> float:
    """Map months of cash runway to a 0-100 score."""
    if cash_months <= 0:
        return 10.0
    return _clamp(cash_months / config.target_cash_months * 100.0)


def _recompute_weights(weights: Dict[str, float]) -> Dict[str, float]:
    if not weights:
        return dict(DEFAULT_WEIGHTS)
    total = sum(weights.values()) or 1.0
    return {k: v / total for k, v in weights.items()}


def compute_health_score(
    monthly_income: float,
    existing_emi: float,
    net_cash: float,
    total_credit: float,
    total_debit: float,
    new_emi: float = 0.0,
    config: HealthScoreConfig | None = None,
) -> Dict[str, Any]:
    """Compute the deterministic financial health result.

    Args:
        monthly_income: Gross monthly income (INR).
        existing_emi: Current recurring monthly EMI obligations (INR).
        net_cash: Current net cash balance (INR).
        total_credit: Total monthly credit (INR).
        total_debit: Total monthly debit (INR).
        new_emi: Optional additional EMI from a proposed loan (INR).
        config: Optional scoring configuration/weights.

    Returns:
        FinancialHealthResult as a dict with cash_score, emi_score, dti_score,
        liquidity_score, overall_score, risk_level and warnings.
    """
    cfg = config or HealthScoreConfig()
    weights = _recompute_weights(cfg.weights)

    monthly_income = float(monthly_income or 0.0)
    existing_emi = float(existing_emi or 0.0)
    net_cash = float(net_cash or 0.0)
    total_credit = float(total_credit or 0.0)
    total_debit = float(total_debit or 0.0)
    new_emi = float(new_emi or 0.0)

    total_emi_burden = existing_emi + new_emi

    # DTI
    dti_ratio = (total_emi_burden / monthly_income) if monthly_income > 0 else float("inf")
    dti_score = dti_score_component(dti_ratio if dti_ratio != float("inf") else 99.0, cfg)

    # EMI burden
    emi_ratio = (total_emi_burden / monthly_income) if monthly_income > 0 else 99.0
    emi_score = emi_score_component(emi_ratio, cfg)

    # Cash / savings rate
    savings_rate = ((total_credit - total_debit) / total_credit) if total_credit > 0 else 0.0
    cash_score = cash_score_component(savings_rate)

    # Liquidity / runway
    runway_income = max(monthly_income - total_emi_burden, 1.0)
    cash_months = net_cash / runway_income if runway_income > 0 else 0.0
    liquidity_score = liquidity_score_component(cash_months, cfg)

    overall_score = (
        cash_score * weights.get("cash", 0.0)
        + emi_score * weights.get("emi", 0.0)
        + dti_score * weights.get("dti", 0.0)
        + liquidity_score * weights.get("liquidity", 0.0)
    )
    overall_score = round(_clamp(overall_score), 1)

    warnings: List[str] = []
    if dti_ratio == float("inf") or dti_ratio > 0.5:
        warnings.append("Debt-to-income ratio is critical (>50%).")
    elif dti_ratio > 0.4:
        warnings.append("Debt-to-income ratio is elevated (40-50%).")
    elif dti_ratio > 0.3:
        warnings.append("Debt-to-income ratio is moderate (30-40%).")

    if net_cash < 0:
        warnings.append("Net cash position is negative.")
    elif cash_months < 1.0:
        warnings.append("Cash runway is below one month.")
    elif cash_months < 3.0:
        warnings.append("Cash runway is below the recommended 3-month buffer.")

    if total_emi_burden > 0 and emi_ratio > 0.4:
        warnings.append("EMI obligations exceed 40% of monthly income.")

    # Risk level deterministically from overall score + DTI rule.
    if dti_ratio > cfg.dti_high or overall_score < 35.0:
        risk_level = "CRITICAL"
    elif dti_ratio > cfg.dti_moderate or overall_score < 50.0:
        risk_level = "HIGH"
    elif dti_ratio > cfg.dti_healthy or overall_score < 75.0:
        risk_level = "MODERATE"
    else:
        risk_level = "HEALTHY"

    return {
        "cash_score": round(cash_score, 1),
        "emi_score": round(emi_score, 1),
        "dti_score": round(dti_score, 1),
        "liquidity_score": round(liquidity_score, 1),
        "overall_score": overall_score,
        "risk_level": risk_level,
        "warnings": warnings,
        "dti_ratio": dti_ratio if dti_ratio != float("inf") else None,
        "emi_ratio": round(emi_ratio, 4),
        "cash_months": round(cash_months, 2),
        "savings_rate": round(savings_rate, 4),
    }
