"""Tests for the Phase 6 multi-agent system."""

import asyncio

import pytest

from backend.agents.bank_agent import BankAgent
from backend.agents.base_agent import AgentContext
from backend.agents.finance_agent import FinanceAgent
from backend.agents.governance_agent import GovernanceAgent
from backend.agents.loan_agent import LoanAgent
from backend.agents.market_agent import MarketAgent
from backend.agents.multi_agent_orchestrator import MultiAgentOrchestrator
from backend.agents.risk_agent import RiskAgent, compute_risk_score
from backend.governance import tracing
from backend.orchestrator.context import SessionContext
from backend.orchestrator.data_layer import Services
from backend.orchestrator.narrator import Narrator


def run(coro):
    return asyncio.run(coro)


def _services():
    return Services("mock")


def _ctx(services, entities=None, session=None):
    session = session or SessionContext(session_id="s1")
    session.services_baseline = services.baseline
    return AgentContext(services=services, session=session, trace=tracing.Tracer.start(),
                        entities=entities or {})


def test_bank_agent_returns_cash():
    async def go():
        svc = _services()
        result = await BankAgent(svc).handle(_ctx(svc))
        assert result["status"] == "ok"
        assert result["facts"]["net_cash"] is not None
        assert result["facts"]["transaction_count"] > 0
    run(go())


def test_loan_agent_calculates_emi():
    async def go():
        svc = _services()
        ctx = _ctx(svc, {"loan_amount": 300000, "rate": 12.0, "tenure_months": 36})
        result = await LoanAgent(svc).handle(ctx)
        assert result["status"] == "ok"
        assert abs(result["facts"]["emi"] - 9964.29) < 0.01
        assert result["facts"]["dti"] is not None
    run(go())


def test_loan_agent_needs_details():
    async def go():
        svc = _services()
        result = await LoanAgent(svc).handle(_ctx(svc))
        assert result["facts"].get("needs_details") is True
    run(go())


def test_market_agent_returns_facts():
    async def go():
        svc = _services()
        ctx = _ctx(svc, {"symbol": "RELIANCE"})
        result = await MarketAgent(svc).handle(ctx)
        assert result["status"] == "ok"
        assert result["facts"]["symbol"] == "RELIANCE"
        assert result["facts"]["trend"] in ("UPTREND", "DOWNTREND", "NEUTRAL")
    run(go())


def test_risk_score_deterministic():
    risk = compute_risk_score({"dti": 0.55, "forecast": {"risk_level": "CRITICAL"}, "net_cash": -1000})
    assert risk["risk_level"] == "HIGH" or risk["risk_level"] == "CRITICAL"
    assert risk["risk_score"] >= 60
    assert risk["reasons"]


def test_governance_approval_for_big_loan():
    async def go():
        svc = _services()
        ctx = _ctx(svc, {"loan_amount": 400000, "tenure_months": 36})
        ctx.cache["phase5"] = {"dti": 0.4}
        result = await GovernanceAgent(svc).handle(ctx)
        assert result["facts"]["requires_approval"] is True
    run(go())


def test_multi_agent_orchestrator_full_flow():
    async def go():
        svc = _services()
        await svc.connect()
        orch = MultiAgentOrchestrator(services=svc, narrator=Narrator(client=None))
        resp = await orch.route(
            "I want a 300000 loan for 36 months. Can I afford it while reaching my 200000 savings goal?")
        assert resp["success"] is True
        assert resp["trace_id"].startswith("trace_")
        for agent in ("finance_agent", "bank_agent", "loan_agent", "risk_agent", "governance_agent"):
            assert agent in resp["agents_used"], resp["agents_used"]
        assert abs(resp["facts"]["loan"]["emi"] - 9964.29) < 0.01
        assert resp["risk"]["risk_level"] in ("LOW", "MODERATE", "MEDIUM", "HIGH", "CRITICAL")
        assert resp["governance"]["requires_approval"] in (True, False)
    run(go())


def test_multi_agent_budget_exceeded():
    async def go():
        svc = _services()
        await svc.connect()
        orch = MultiAgentOrchestrator(services=svc, narrator=Narrator(client=None))
        resp = await orch.route("Can I afford a 300000 loan?", budget_max_tool_calls=1)
        assert resp["success"] is False
        assert resp["error_code"] == "BUDGET_EXCEEDED"
    run(go())


def test_market_agent_missing_symbol_handled():
    async def go():
        svc = _services()
        result = await MarketAgent(svc).handle(_ctx(svc))
        assert result["facts"].get("needs_symbol") is True
    run(go())
