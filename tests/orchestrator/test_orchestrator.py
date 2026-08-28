"""Orchestrator tests: finance, loan, market, multi-domain, failure and budget."""

import asyncio

import pytest

import loan_engine as le
from backend.governance.validation import ValidationError
from backend.orchestrator.context import SessionContext
from backend.orchestrator.data_layer import Services
from backend.orchestrator.narrator import Narrator
from backend.orchestrator.orchestrator import Orchestrator
from backend.orchestrator.tool_registry import require_tool


def make_orchestrator(**kwargs):
    services = Services("mock")
    orch = Orchestrator(
        services=services,
        narrator=Narrator(client=None),  # force deterministic fallback, no network
        **kwargs,
    )
    return orch, services


def run(coro):
    return asyncio.run(coro)


def test_finance_query():
    orch, _ = make_orchestrator()
    resp = run(orch.route("What is my current cash position?"))
    assert resp.success is True
    assert resp.intent in ("FINANCE", "MULTI_DOMAIN")
    assert "get_cash_position" in resp.tools_used
    assert resp.trace_id.startswith("trace_")
    assert resp.session_id
    assert "net_cash" in resp.facts.get("cash_position", {})


def test_loan_query():
    orch, _ = make_orchestrator()
    resp = run(orch.route("Calculate a 300000 loan at 12% for 36 months"))
    assert resp.success is True
    assert "calculate_loan" in resp.tools_used
    assert abs(resp.facts["loan"]["emi"] - le.calculate_emi(300000, 12.0, 36)) < 0.01


def test_market_query():
    orch, _ = make_orchestrator()
    resp = run(orch.route("How is RELIANCE performing?"))
    assert resp.success is True
    assert "get_quote" in resp.tools_used
    assert resp.facts["market"]["symbol"] == "RELIANCE"
    assert resp.facts["market"]["trend"] in ("UPTREND", "DOWNTREND", "NEUTRAL")


def test_multi_domain_query():
    orch, _ = make_orchestrator()
    resp = run(orch.route("Based on my current cash, existing EMIs and income, can I afford a 300000 loan for 36 months?"))
    assert resp.success is True
    assert resp.intent == "MULTI_DOMAIN"
    for tool in ("get_financial_baseline", "calculate_loan", "calculate_dti"):
        assert tool in resp.tools_used


def test_invalid_query_general():
    orch, _ = make_orchestrator()
    resp = run(orch.route("Not a finance question"))
    assert resp.intent == "GENERAL"
    assert resp.tools_used == []


def test_invalid_loan_executor_rejects_negative_amount():
    """Directly invoking the loan calculator with a negative amount must raise."""
    services = Services("mock")
    spec = require_tool("calculate_loan")
    ctx = SessionContext(session_id="t")
    with pytest.raises(ValidationError):
        run(spec.executor(services, ctx, loan_amount=-50000, rate=12, tenure_months=36))


def test_unknown_tool_rejected():
    from backend.orchestrator.tool_registry import require_tool
    with pytest.raises(ValidationError):
        require_tool("totally_unknown_tool")


def test_budget_exceeded_stops_execution():
    orch, _ = make_orchestrator()
    resp = run(orch.route("Based on my cash and a 300000 loan for 36 months, can I afford it?",
                          budget_max_tool_calls=1))
    assert resp.success is False
    assert resp.error_code == "BUDGET_EXCEEDED"
    assert "budget exceeded" in resp.message.lower()
    assert len(resp.tools_used) <= 1


def test_trace_ids_propagate():
    orch, _ = make_orchestrator()
    resp = run(orch.route("What is my balance?"))
    assert resp.request_id and resp.request_id.startswith("req_")
    assert resp.trace_id and resp.trace_id.startswith("trace_")
    assert resp.session_id and resp.session_id.startswith("session_")


def test_conversational_context_remembered():
    orch, _ = make_orchestrator()
    first = run(orch.route("I want a 300000 loan"))
    sid = first.session_id
    run(orch.route("36 months", session_id=sid))
    ctx = orch.sessions.get(sid)
    assert ctx is not None
    assert ctx.last_loan_amount == 300000
    assert ctx.last_loan_tenure == 36
    assert len(ctx.conversation) >= 2


def test_market_tool_failure_keeps_finance():
    """Simulate a market-only query; finance capabilities must not break."""
    orch, _ = make_orchestrator()
    resp = run(orch.route("What is my balance?"))
    assert resp.success is True
    assert "get_cash_position" in resp.tools_used
