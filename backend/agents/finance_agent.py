"""Finance agent - health, forecast, spending, goals, debt and anomalies."""

from __future__ import annotations

from typing import Any, Dict

from backend.agents.base_agent import AgentContext, BaseAgent
from intelligence import compute_phase5_facts


class FinanceAgent(BaseAgent):
    name = "finance_agent"

    async def handle(self, ctx: AgentContext) -> Dict[str, Any]:
        if "phase5" in ctx.cache:
            return self.result({"phase5": ctx.cache["phase5"]})
        accounts = await self.services.get_accounts()
        transactions = await self.services.get_transactions()
        offers = await self.services.get_loan_offers()
        facts = compute_phase5_facts(accounts, transactions, offers)
        ctx.cache["phase5"] = facts
        return self.result({"phase5": facts})
