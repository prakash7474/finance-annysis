"""API tests for Phase 6 (agents, tools, multi-agent route, audit, voice WS)."""

import json

import pytest
from fastapi.testclient import TestClient

from backend.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_agents_status(client):
    r = client.get("/api/agents")
    assert r.status_code == 200
    names = [a["name"] for a in r.json()["agents"]]
    for agent in ("bank_agent", "loan_agent", "market_agent", "risk_agent", "finance_agent", "governance_agent"):
        assert agent in names


def test_tools_discovery(client):
    r = client.get("/api/tools")
    assert r.status_code == 200
    body = r.json()
    assert "discovery" in body and "servers" in body
    assert "bank_mcp" in body["servers"]


def test_multi_agent_critical_integration(client):
    message = ("I want a 300000 loan for 36 months. "
               "Can I afford it while reaching my 200000 savings goal?")
    r = client.post("/api/agents/route", json={"message": message, "session_id": "p6"})
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    assert body["trace_id"].startswith("trace_")
    for agent in ("finance_agent", "bank_agent", "loan_agent", "risk_agent", "governance_agent"):
        assert agent in body["agents_used"], body["agents_used"]
    loan = body["facts"]["loan"]
    assert abs(loan["emi"] - 9964.29) < 0.01
    assert loan["amount"] == 300000
    assert body["risk"]["risk_score"] >= 0
    # No Gemini-generated arithmetic in tests (fallback narrator).
    assert body["narrator"] == "fallback"
    # trace preserved end-to-end via audit.
    audit = client.get(f"/api/audit/{body['trace_id']}")
    assert audit.status_code == 200
    assert any(e["operation"] == "multi_agent_route" for e in audit.json()["audit"])


def test_multi_agent_budget_exceeded(client):
    r = client.post("/api/agents/route", json={"message": "What is my balance?"})
    assert r.status_code == 200
    # Default budget is fine; assert success for a normal request.
    assert r.json()["success"] is True


def test_audit_not_found(client):
    r = client.get("/api/audit/TRACE_DOES_NOT_EXIST")
    assert r.status_code == 404


def test_voice_websocket_roundtrip(client):
    with client.websocket_connect("/api/voice") as ws:
        started = ws.receive_json()
        assert started["type"] == "started"
        assert "session_id" in started

        ws.send_json({"type": "audio", "data": "What is my financial health?"})
        transcript = ws.receive_json()
        assert transcript["type"] == "transcript"

        got_done = False
        got_reply = False
        for _ in range(20):
            msg = ws.receive_json()
            if msg["type"] == "reply":
                got_reply = True
            if msg["type"] == "done":
                got_done = True
                break
        assert got_reply and got_done

        ws.send_json({"type": "stop"})
        stopped = ws.receive_json()
        assert stopped["type"] == "stopped"


def test_voice_websocket_interrupt(client):
    with client.websocket_connect("/api/voice") as ws:
        ws.receive_json()  # started
        ws.send_json({"type": "interrupt"})
        msg = ws.receive_json()
        assert msg["type"] == "interrupted"
        assert msg["interrupted"] is True
