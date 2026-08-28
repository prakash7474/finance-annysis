"""
multi_agent_orchestrator.py - Phase 6 central multi-agent mediator.

Determines the required agents for a request, runs the independent ones in
parallel, then risk + governance, applies the operational budget, narrates the
aggregated facts with Gemini (or the deterministic fallback) and returns a
structured response with a trace ID.  Agents never mutate global state.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any, Dict, List, Optional, Tuple

from backend.agents.bank_agent import BankAgent
from backend.agents.base_agent import AgentContext
from backend.agents.finance_agent import FinanceAgent
from backend.agents.governance_agent import GovernanceAgent
from backend.agents.loan_agent import LoanAgent
from backend.agents.market_agent import MarketAgent
from backend.agents.risk_agent import RiskAgent
from backend.config import settings
from backend.governance import tracing
from backend.governance.audit import AuditLog
from backend.governance.budget import BudgetExceeded, OperationalBudgetTracker
from audit_logger import record_decision
from backend.orchestrator import router as intent_router
from backend.orchestrator.data_layer import Services, get_services
from backend.orchestrator.narrator import Narrator, make_narrator
from backend.orchestrator.session import SessionManager

# intent -> ordered agent plan (the phases that must run first).
AGENTS = ["finance_agent", "bank_agent", "loan_agent", "market_agent", "risk_agent", "governance_agent"]

# Agents that can run in parallel (risk depends on the facts they produce).
_PARALLEL_AGENTS = ["finance_agent", "bank_agent", "loan_agent", "market_agent"]

# Map intent label to the agent set to execute.
_AGENT_PLAN = {
    "FINANCE": ["finance_agent", "bank_agent", "risk_agent", "governance_agent"],
    "LOAN": ["finance_agent", "bank_agent", "loan_agent", "risk_agent", "governance_agent"],
    "MARKET": ["finance_agent", "market_agent", "risk_agent", "governance_agent"],
    "MULTI_DOMAIN": ["finance_agent", "bank_agent", "loan_agent", "market_agent", "risk_agent", "governance_agent"],
    "GENERAL": ["finance_agent", "governance_agent"],
}


class MultiAgentOrchestrator:
    def __init__(self, services: Optional[Services] = None, narrator: Optional[Narrator] = None,
                 session_manager: Optional[SessionManager] = None, emit_events: bool = True,
                 max_iterations: int = 5):
        self.services = services or get_services()
        self.narrator = narrator or make_narrator()
        self.sessions = session_manager or SessionManager()
        self.emit_events = emit_events
        self.max_iterations = max_iterations
        self.agents = self._build_agents()

    def _build_agents(self):
        return {
            "bank_agent": BankAgent(self.services),
            "loan_agent": LoanAgent(self.services),
            "market_agent": MarketAgent(self.services),
            "finance_agent": FinanceAgent(self.services),
            "risk_agent": RiskAgent(self.services),
            "governance_agent": GovernanceAgent(self.services),
        }

    def agent_status(self) -> List[Dict[str, Any]]:
        return [{"name": n, "status": "ready"} for n in AGENTS]

    async def route(self, message: str, session_id: Optional[str] = None,
                    budget_max_tool_calls: Optional[int] = None,
                    budget_max_cost_usd: Optional[float] = None) -> Dict[str, Any]:
        trace = tracing.Tracer.start(session_id)
        session = self.sessions.get_or_create(session_id, self.services)
        intent_result, entities = intent_router.detect_intent(message, session)
        trace.step("ROUTER", "detect_intent", "SUCCESS")

        for key in ("loan_amount", "rate", "tenure_months", "symbol", "salary_change_percent"):
            if key in entities:
                session.set(f"_parsed_{key}", entities[key])

        budget = OperationalBudgetTracker(max_tool_calls=budget_max_tool_calls,
                                          max_cost_usd=budget_max_cost_usd, trace_id=trace.trace_id)
        ctx = AgentContext(services=self.services, session=session, trace=trace,
                           entities=entities, message=message, budget=budget)

        plan = _AGENT_PLAN.get(intent_result.intent, _AGENT_PLAN["GENERAL"])
        agent_results: Dict[str, Dict[str, Any]] = {}

        parallel = [a for a in plan if a in _PARALLEL_AGENTS]
        try:
            results = await self._run_concurrent(parallel, ctx, budget, trace)
            for name, result in results.items():
                agent_results[name] = result
        except BudgetExceeded as exc:
            return self._budget_response(trace, session, intent_result.intent, exc)

        # Risk (depends on the facts produced above).
        if "risk_agent" in plan:
            try:
                budget.consume(tracing.new_id("tool"), "risk_agent", domain="risk")
            except BudgetExceeded as exc:
                return self._budget_response(trace, session, intent_result.intent, exc)
            agent_results["risk_agent"] = await self.agents["risk_agent"].handle(ctx)
            trace.step("RISK", "risk_agent", "SUCCESS")

        # Governance (depends on facts + risk).
        if "governance_agent" in plan:
            try:
                budget.consume(tracing.new_id("tool"), "governance_agent", domain="governance")
            except BudgetExceeded as exc:
                return self._budget_response(trace, session, intent_result.intent, exc)
            agent_results["governance_agent"] = await self.agents["governance_agent"].handle(ctx)
            trace.step("GOVERNANCE", "governance_agent", "SUCCESS")

        facts = self._merge_facts(agent_results)
        self._persist_context(session, entities, facts)
        session.add_message("user", message)

        # Narration.
        message_text, narrator_source = self.narrator.narrate(
            facts, intent=intent_result.intent, user_message=message, session_id=session.session_id)
        trace.step("GEMINI", "narration", "SUCCESS")
        session.add_message("assistant", message_text)

        agents_used = [r["agent"] for r in agent_results.values() if r.get("status") == "ok"]
        tools_used = self._tools_from_agents(agents_used)
        tracing.Tracer.end(trace.trace_id, "completed")

        record_decision(trace.trace_id, "multi_agent_route", "success",
                        facts={"intent": intent_result.intent, "agents": agents_used})

        # Generate recommendations / alerts for the response if finance facts exist.
        recs, alerts = self._extract_recommendations_and_alerts(facts)

        return {
            "success": True,
            "session_id": session.session_id,
            "request_id": trace.request_id,
            "trace_id": trace.trace_id,
            "message": message_text,
            "intent": intent_result.intent,
            "agents_used": agents_used,
            "tools_used": tools_used,
            "facts": facts,
            "risk": agent_results.get("risk_agent", {}).get("facts", {}),
            "governance": agent_results.get("governance_agent", {}).get("facts", {}),
            "recommendations": recs,
            "alerts": alerts,
            "narrator": narrator_source,
        }

    async def _run_concurrent(self, agent_names: List[str], ctx: AgentContext, budget: Any,
                              trace: tracing.RequestTrace) -> Dict[str, Dict[str, Any]]:
        if not agent_names:
            return {}

        async def run(name: str) -> Tuple[str, Dict[str, Any]]:
            budget.consume(tracing.new_id("tool"), name, domain=name.split("_")[0])
            start = time.monotonic()
            agent = self.agents[name]
            try:
                result = await agent.handle(ctx)
                trace.step(name.upper(), name, "SUCCESS",
                           duration_ms=round((time.monotonic() - start) * 1000, 2))
                AuditLog.record(trace.trace_id, name, "handle", status="success", session_id=ctx.session.session_id)
            except Exception as exc:  # noqa: BLE001
                result = {"agent": name, "facts": {}, "status": "failed", "error": str(exc)}
                trace.step(name.upper(), name, "FAILED")
                AuditLog.record(trace.trace_id, name, "handle", status="failed", session_id=ctx.session.session_id)
            return name, result

        results = await asyncio.gather(*[run(n) for n in agent_names])
        return dict(results)

    def _merge_facts(self, agent_results: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        facts: Dict[str, Any] = {}
        phase5 = agent_results.get("finance_agent", {}).get("facts", {}).get("phase5")
        if phase5:
            facts.update(phase5)
            facts["domain"] = "INTELLIGENCE"
        bank = agent_results.get("bank_agent", {}).get("facts", {})
        if bank:
            facts["net_cash"] = bank.get("net_cash")
            facts["cash_position"] = {"net_cash": bank.get("net_cash"), "accounts": bank.get("accounts", [])}
            facts["monthly_summary"] = bank.get("monthly_summary")
        loan = agent_results.get("loan_agent", {}).get("facts", {})
        if loan and "dti" in loan:
            facts["loan"] = loan
            facts["dti"] = loan.get("dti")
            facts["new_loan_emi"] = loan.get("emi")
        market = agent_results.get("market_agent", {}).get("facts", {})
        if market and "price" in market:
            facts["market"] = market
        risk = agent_results.get("risk_agent", {}).get("facts", {})
        if risk:
            facts["risk"] = risk
        return facts

    def _persist_context(self, session, entities, facts) -> None:
        if entities.get("loan_amount"):
            session.set("last_loan_amount", float(entities["loan_amount"]))
        if entities.get("rate"):
            session.set("last_loan_rate", float(entities["rate"]))
        if entities.get("tenure_months"):
            session.set("last_loan_tenure", int(entities["tenure_months"]))
        if entities.get("symbol"):
            session.set("last_market_symbol", entities["symbol"])
        if facts.get("monthly_income") is not None:
            session.set("monthly_income", facts.get("monthly_income"))
        if facts.get("existing_emi") is not None:
            session.set("existing_emi", facts.get("existing_emi"))

    def _tools_from_agents(self, agents: List[str]) -> List[str]:
        tool_map = {
            "bank_agent": ["get_accounts", "get_cash_position"],
            "loan_agent": ["calculate_loan", "calculate_dti"],
            "market_agent": ["get_price", "get_trend", "get_momentum"],
            "finance_agent": ["calculate_health_score", "forecast_cash_flow", "plan_financial_goal"],
            "risk_agent": ["compute_risk_score"],
            "governance_agent": ["validate", "budget_check"],
        }
        return [t for a in agents for t in tool_map.get(a, [])]

    def _extract_recommendations_and_alerts(self, facts: Dict[str, Any]):
        return facts.get("recommendations", []), facts.get("alerts", [])

    def _budget_response(self, trace, session, intent, exc):
        tracing.Tracer.end(trace.trace_id, "budget_exceeded")
        record_decision(trace.trace_id, "multi_agent_route", "budget_exceeded")
        return {
            "success": False, "session_id": session.session_id, "request_id": trace.request_id,
            "trace_id": trace.trace_id, "message": exc.message, "intent": intent,
            "error_code": "BUDGET_EXCEEDED", "agents_used": [], "tools_used": [],
            "facts": {}, "risk": {}, "governance": {}, "recommendations": [], "alerts": [],
            "narrator": None,
        }
