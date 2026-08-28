"""API tests using FastAPI TestClient (offline: mock data + fallback narrator)."""

import pytest
from fastapi.testclient import TestClient

from backend.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] in ("healthy", "degraded")
    for svc in ("bank_mcp", "market_mcp", "loan_engine", "gemini"):
        assert svc in body["services"]


def test_health_does_not_expose_secret(client):
    r = client.get("/health")
    assert "GEMINI_API_KEY" not in r.text
    assert "your_key_here" not in r.text


def test_cash_position(client):
    r = client.get("/api/finance/cash-position")
    assert r.status_code == 200
    body = r.json()
    assert "net_cash" in body
    assert len(body["accounts"]) >= 1


def test_market_price(client):
    r = client.get("/api/market/price?symbol=RELIANCE")
    assert r.status_code == 200
    assert r.json()["price"] > 0


def test_loan_analyze(client):
    r = client.post("/api/loan/analyze",
                    json={"amount": 300000, "rate": 12.0, "tenure_months": 36,
                          "monthly_income": 80000, "existing_emi": 22300})
    assert r.status_code == 200
    body = r.json()
    assert abs(body["emi"] - 9964.29) < 0.01
    assert body["risk_level"] in ("LOW", "MEDIUM", "HIGH")


def test_loan_analyze_rejects_negative(client):
    r = client.post("/api/loan/analyze",
                    json={"amount": -50000, "rate": 12.0, "tenure_months": 36, "monthly_income": 80000})
    assert r.status_code == 422


def test_loan_analyze_rejects_zero_tenure(client):
    r = client.post("/api/loan/analyze",
                    json={"amount": 50000, "rate": 12.0, "tenure_months": 0, "monthly_income": 80000})
    assert r.status_code == 422


def test_scenario(client):
    r = client.post("/api/scenario", json={
        "loan_amount": 300000, "tenure_months": 36, "rate": 12.0, "monthly_income": 80000,
        "existing_emi": 22300, "salary_change_percent": -10})
    assert r.status_code == 200
    body = r.json()
    assert body["scenario"]["monthly_income"] == 72000.0
    assert body["scenario"]["dti_ratio"] > body["current"]["dti_ratio"]


def test_chat_finance(client):
    r = client.post("/api/chat", json={"message": "What is my current cash position?", "session_id": "api-1"})
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    assert body["session_id"] == "api-1"
    assert body["trace_id"].startswith("trace_")
    assert "get_cash_position" in body["tools_used"]
    assert body["facts"].get("cash_position", {}).get("net_cash") is not None


def test_chat_does_not_expose_key(client):
    r = client.post("/api/chat", json={"message": "What is my balance?"})
    assert "GEMINI_API_KEY" not in r.text


def test_chat_rejects_oversized(client):
    r = client.post("/api/chat", json={"message": "x" * 9000})
    assert r.status_code == 422


def test_chat_returns_request_id(client):
    r = client.post("/api/chat", json={"message": "What is my balance?"})
    assert r.json()["request_id"].startswith("req_")


def test_events_recent(client):
    r = client.get("/api/events/recent?limit=10")
    assert r.status_code == 200
    assert "events" in r.json()


def test_events_inject_and_analyze(client):
    r = client.post("/api/events/inject",
                    json={"account_id": "ACC001", "amount": 80000, "description": "LARGE DEBIT", "type": "DEBIT"})
    assert r.status_code == 200
    inj = r.json()
    assert any(e["event"] == "risk_alert" for e in inj["events"])
    assert inj["snapshot"]["net_cash"] < 10000

    a = client.post("/api/events/analyze", json={"account_id": "ACC001", "amount": 80000})
    assert a.status_code == 200
    assert a.json()["health"]["risk_level"] in ("MODERATE", "HIGH", "CRITICAL")


def test_root(client):
    r = client.get("/")
    assert r.status_code == 200
    assert r.json()["service"] == "FinPilot AI Finance Controller"
