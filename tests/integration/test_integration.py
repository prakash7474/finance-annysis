"""Integration test: the exact multi-domain affordability flow through the API."""

import pytest
from fastapi.testclient import TestClient

import loan_engine as le
from backend.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_multi_domain_affordability_flow(client):
    """'Based on my current cash, existing EMIs, monthly income, and a ₹300,000 loan
    for 36 months, can I afford it?' must exercise Chat API -> Orchestrator ->
    Bank MCP -> Finance Engine -> Loan Engine -> DTI/Risk -> Facts -> Narrator ->
    Chat Response."""

    message = (
        "Based on my current cash, existing EMIs, monthly income, "
        "and a ₹300,000 loan for 36 months, can I afford it?"
    )
    r = client.post("/api/chat", json={"message": message, "session_id": "integration-1"})
    assert r.status_code == 200
    body = r.json()

    # trace_id exists
    assert body["trace_id"] and body["trace_id"].startswith("trace_")
    # session_id exists (respects the provided one)
    assert body["session_id"] == "integration-1"

    # tools_used populated (finance baseline + loan + DTI + health)
    for tool in ("get_financial_baseline", "calculate_loan", "calculate_dti"):
        assert tool in body["tools_used"], body["tools_used"]

    # financial numbers match the deterministic engine - no Gemini arithmetic.
    facts = body["facts"]
    expected_emi = le.calculate_emi(300000, 12.0, 36)
    assert abs(facts["loan"]["emi"] - expected_emi) < 0.01

    parts = facts["loan"]
    assert parts["amount"] == 300000
    assert parts["rate"] == 12.0
    assert parts["tenure_months"] == 36
    assert abs(parts["total_interest"] - le.total_interest_and_cost(300000, 12.0, 36)["total_interest"]) < 0.01

    # health score present and deterministic
    assert facts["health"]["overall_score"] >= 0

    # the narrated message references the deterministic EMI value
    assert "9964" in body["message"] or "9,964" in body["message"]
    assert "Risk" in body["message"] or "risk" in body["message"].lower()

    # no Gemini-generated arithmetic: narrator should be fallback in tests
    assert body["narrator"] == "fallback"


def test_session_remembers_loan_across_turns(client):
    sid = "integration-multi"
    client.post("/api/chat", json={"message": "I want a 300000 loan", "session_id": sid})
    client.post("/api/chat", json={"message": "36 months", "session_id": sid})
    # A follow-up that references the remembered loan amount should not fail.
    r = client.post("/api/chat", json={"message": "Compare offers for it", "session_id": sid})
    assert r.status_code == 200
    assert any(t in r.json()["tools_used"] for t in ("compare_loan_offers", "calculate_loan"))


def test_missing_data_unavailable(client):
    """An unknown symbol returns a structured MARKET_DATA_NOT_FOUND error."""
    r = client.get("/api/market/price?symbol=NOTAREALSYM")
    assert r.status_code == 404
    assert r.json()["error_code"] == "MARKET_DATA_NOT_FOUND"


def test_sse_stream_is_event_source(client):
    """The events endpoint returns a text/event-stream StreamingResponse."""
    import asyncio

    from backend.api.events_routes import events_stream

    async def probe():
        resp = await events_stream()
        assert resp.media_type == "text/event-stream"
        agen = resp.body_iterator
        try:
            chunk = await anext(agen)
            assert "event: connected" in chunk
            assert "data:" in chunk
        finally:
            await agen.aclose()

    asyncio.run(probe())
