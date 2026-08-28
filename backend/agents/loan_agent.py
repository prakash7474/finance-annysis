"""Loan agent - loan arithmetic via the deterministic loan engine."""

from __future__ import annotations

from typing import Any, Dict

import loan_engine as le
from backend.agents.base_agent import AgentContext, BaseAgent


class LoanAgent(BaseAgent):
    name = "loan_agent"

    async def handle(self, ctx: AgentContext) -> Dict[str, Any]:
        amount = ctx.entities.get("loan_amount")
        rate = ctx.entities.get("rate") or 12.0
        tenure = ctx.entities.get("tenure_months")
        if not amount or not tenure:
            return self.result({
                "available": True,
                "needs_details": True,
                "last_loan": ctx.session.last_loan_amount,
                "last_tenure": ctx.session.last_loan_tenure,
            })
        income = ctx.session.monthly_income or self.services.baseline.get("monthly_income")
        emi_baseline = ctx.session.existing_emi or self.services.baseline.get("existing_emi")
        result = le.assess_loan_risk(amount, rate, tenure, income or 0.0, emi_baseline or 0.0)
        dti = le.calculate_dti(income or 0.0, emi_baseline or 0.0, result["emi"])
        return self.result({
            "amount": round(amount, 2),
            "rate": rate,
            "tenure_months": tenure,
            "emi": round(result["emi"], 2),
            "total_interest": round(result["total_interest"], 2),
            "total_cost": round(result["total_cost"], 2),
            "emi_income_ratio": result["emi_income_ratio"],
            "dti": dti,
            "risk_level": result["risk_level"],
            "risk_flags": result["risk_flags"],
        })
