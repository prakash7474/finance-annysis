"""Risk agent - deterministic financial risk assessment (never LLM-derived)."""

from __future__ import annotations

from typing import Any, Dict, List

from backend.agents.base_agent import AgentContext, BaseAgent

LIQUIDITY_MIN = 25000.0


def compute_risk_score(facts: Dict[str, Any]) -> Dict[str, Any]:
    """Deterministic 0-100 risk score + level + reasons from structured facts."""
    score = 0.0
    reasons: List[str] = []

    dti = facts.get("dti")
    if isinstance(dti, (int, float)) and dti > 0.5:
        score += 30
        reasons.append("DTI above 50% critical threshold")
    elif isinstance(dti, (int, float)) and dti > 0.4:
        score += 20
        reasons.append("DTI above 40% threshold")
    elif isinstance(dti, (int, float)) and dti > 0.3:
        score += 10
        reasons.append("DTI above 30% threshold")

    forecast = facts.get("forecast") or {}
    frisk = forecast.get("risk_level")
    if frisk == "CRITICAL":
        score += 25
        reasons.append("Projected cash-flow is critical")
    elif frisk == "HIGH":
        score += 18
        reasons.append("Projected liquidity decline")
    elif frisk == "MEDIUM":
        score += 10

    net_cash = facts.get("net_cash")
    if net_cash is not None and net_cash < 0:
        score += 25
        reasons.append("Net cash is negative")
    elif net_cash is not None and net_cash < LIQUIDITY_MIN:
        score += 15
        reasons.append("Liquidity below threshold")

    n_anomalies = len(facts.get("anomalies") or [])
    if n_anomalies:
        score += min(n_anomalies * 8, 16)
        reasons.append(f"{n_anomalies} transaction anomaly detected")

    health = facts.get("health") or {}
    if health and health.get("status") == "CRITICAL":
        score += 20
        reasons.append("Financial health is critical")
    elif health and health.get("status") == "AT_RISK":
        score += 10
        reasons.append("Financial health is at risk")

    score = round(max(0.0, min(100.0, score)), 1)
    if score >= 85:
        level = "CRITICAL"
    elif score >= 70:
        level = "HIGH"
    elif score >= 45:
        level = "MEDIUM"
    elif score >= 20:
        level = "MODERATE"
    else:
        level = "LOW"
    return {"risk_score": score, "risk_level": level, "reasons": reasons}


class RiskAgent(BaseAgent):
    name = "risk_agent"

    async def handle(self, ctx: AgentContext) -> Dict[str, Any]:
        facts = ctx.cache.get("phase5", {})
        loan = ctx.entities.get("loan_amount")
        income = facts.get("monthly_income")
        emi = facts.get("existing_emi")
        combined = {
            "dti": facts.get("dti"),
            "forecast": facts.get("forecast"),
            "net_cash": facts.get("net_cash"),
            "anomalies": facts.get("anomalies"),
            "health": facts.get("health"),
        }
        risk = compute_risk_score(combined)
        # If a new loan is in play, factor it in.
        if loan and income:
            import loan_engine as le

            new_emi = le.calculate_emi(loan, ctx.entities.get("rate") or 12.0,
                                       ctx.entities.get("tenure_months") or 36)
            dti_with_loan = (emi + new_emi) / income
            combined["dti"] = dti_with_loan
            risk = compute_risk_score(combined)
            risk["new_loan_emi"] = round(new_emi, 2)
            risk["dti_with_loan"] = round(dti_with_loan, 4)
        return self.result(risk)
