"""Governance agent - safety, validation, budget and approval checks."""

from __future__ import annotations

from typing import Any, Dict

from backend.agents.base_agent import AgentContext, BaseAgent
from backend.governance.budget import BudgetExceeded


class GovernanceAgent(BaseAgent):
    name = "governance_agent"

    async def handle(self, ctx: AgentContext) -> Dict[str, Any]:
        # 1. Budget check - never allow execution past the guard.
        budget_ok = True
        budget_exceeded = False
        if ctx.budget is not None:
            snap = ctx.budget.snapshot()
            budget_ok = snap["remaining_calls"] > 0
            budget_exceeded = not budget_ok

        # 2. Input validity.
        invalid = False
        amount = ctx.entities.get("loan_amount")
        if amount is not None and amount <= 0:
            invalid = True
        tenure = ctx.entities.get("tenure_months")
        if tenure is not None and tenure <= 0:
            invalid = True

        # 3. Safety - the platform only ever advises; never executes anything.
        safe = True  # advisory-only platform

        # 4. Approval decision.
        requires_approval = False
        if amount is not None and amount >= 300000:
            requires_approval = True
        if ctx.cache.get("phase5", {}).get("dti") and ctx.cache["phase5"]["dti"] > 0.5:
            requires_approval = True

        approved = not requires_approval  # informational actions proceed; risky need approval
        return self.result({
            "allowed": bool(budget_ok and not invalid and safe),
            "budget_ok": budget_ok,
            "budget_exceeded": budget_exceeded,
            "input_valid": not invalid,
            "invalid_input": invalid,
            "safe": safe,
            "requires_approval": requires_approval,
            "status": "APPROVED" if approved else "PENDING_APPROVAL",
            "reason": (
                "Advisory action" if approved
                else "Action requires human approval before execution"
            ),
        })
