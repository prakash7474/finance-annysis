"""Bank agent - cash position, account and transaction facts via the Bank MCP."""

from __future__ import annotations

from typing import Any, Dict

import finance_engine as fe
from backend.agents.base_agent import AgentContext, BaseAgent


class BankAgent(BaseAgent):
    name = "bank_agent"

    async def handle(self, ctx: AgentContext) -> Dict[str, Any]:
        try:
            accounts = await self.services.get_accounts()
            transactions = await self.services.get_transactions()
            pos = fe.compute_cash_position(accounts, transactions)
            start, end = "2026-08-01", "2026-08-31"
            summary = fe.summarize_credit_debit(transactions, start, end)
            emis = fe.detect_emis(transactions, start, end)
            return self.result({
                "net_cash": pos["net_cash"],
                "accounts": pos["accounts"],
                "monthly_summary": {
                    "total_credit": summary["total_credit"],
                    "total_debit": summary["total_debit"],
                    "net_change": summary["net_change"],
                },
                "emi_total": emis["total_emi"],
                "transaction_count": len(transactions),
            })
        except Exception as exc:  # noqa: BLE001 - structured failure, never crash the orchestrator
            return self.result({}, status="failed", error=f"Bank data unavailable: {exc}")
