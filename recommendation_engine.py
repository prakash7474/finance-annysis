"""
recommendation_engine.py - Deterministic recommendation engine.

Generates explainable recommendations (with reason codes + supporting facts)
from the structured facts produced by the other Phase 5 engines.  Gemini may
explain them but must never invent the supporting facts.
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List

from models.recommendation_models import Recommendation

LIQUIDITY_MIN = 25000.0


def _rec(category: str, priority: int, title: str, reason_codes: List[str],
         supporting_facts: Dict[str, Any], confidence: float,
         requires_approval: bool = False) -> Recommendation:
    return Recommendation(
        recommendation_id=f"REC_{uuid.uuid4().hex[:10]}",
        priority=priority, category=category, title=title,
        reason_codes=reason_codes, supporting_facts=supporting_facts,
        confidence=confidence, requires_approval=requires_approval,
    )


def generate_recommendations(facts: Dict[str, Any]) -> List[Recommendation]:
    """Build recommendations from deterministic facts."""
    recs: List[Recommendation] = []
    priority = 1

    dti = facts.get("dti")
    projected_balance = (facts.get("forecast") or {}).get("projected_balance")
    net_cash = facts.get("net_cash")
    goal_shortfall = facts.get("goal_shortfall", 0.0)
    has_anomaly = bool(facts.get("anomalies"))
    spending_spikes = [s for s in facts.get("spending", []) if s.get("risk_level") == "HIGH"]
    debt_high_interest = [d for d in facts.get("debt", [])
                          if "HIGH_INTEREST_RATE" in d.get("reason_codes", [])]
    health_status = (facts.get("health") or {}).get("status")

    # 1. Borrowing warning
    if dti is not None and dti > 0.4:
        recs.append(_rec(
            "DEBT", priority, "Avoid additional borrowing",
            ["HIGH_DTI"], {"dti": round(dti, 4), "monthly_income": facts.get("monthly_income")},
            0.9, requires_approval=True,
        ))
        priority += 1

    # 2. Liquidity
    liquidity_value = projected_balance if projected_balance is not None else net_cash
    if liquidity_value is not None and liquidity_value < LIQUIDITY_MIN:
        recs.append(_rec(
            "LIQUIDITY", priority, "Build a liquidity buffer",
            ["LOW_LIQUIDITY"], {"projected_or_current_balance": round(liquidity_value, 2)},
            0.85, requires_approval=True,
        ))
        priority += 1

    # 3. Savings shortfall
    if goal_shortfall and goal_shortfall > 0:
        recs.append(_rec(
            "SAVINGS", priority, f"Increase monthly savings by {goal_shortfall:,.2f}",
            ["GOAL_SHORTFALL"], {"goal_shortfall": round(goal_shortfall, 2)},
            0.8, requires_approval=False,
        ))
        priority += 1

    # 4. Spending discipline
    if has_anomaly or spending_spikes:
        recs.append(_rec(
            "SPENDING", priority, "Reduce discretionary spending",
            ["SPENDING_ANOMALY" if has_anomaly else "SPENDING_SPIKE"],
            {"anomaly_count": len(facts.get("anomalies", [])),
             "spending_spikes": len(spending_spikes)},
            0.75, requires_approval=False,
        ))
        priority += 1

    # 5. Debt payoff
    if debt_high_interest:
        recs.append(_rec(
            "DEBT", priority, "Prepay the highest-cost debt",
            ["HIGH_INTEREST_RATE"], {"high_interest_loans": [d.get("loan_id") for d in debt_high_interest]},
            0.8, requires_approval=True,
        ))
        priority += 1

    # 6. Professional guidance
    if health_status in ("AT_RISK", "CRITICAL"):
        recs.append(_rec(
            "GUIDANCE", priority, "Seek financial guidance",
            ["HEALTH_RISK"], {"health_status": health_status, "health_score": (facts.get("health") or {}).get("score")},
            0.6, requires_approval=False,
        ))
        priority += 1

    if not recs:
        recs.append(_rec(
            "GENERAL", 1, "Maintain current financial habits",
            ["NO_ISSUES_DETECTED"], {}, 0.5, requires_approval=False,
        ))

    return recs
