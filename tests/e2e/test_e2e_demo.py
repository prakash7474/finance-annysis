"""End-to-end demo test: the 8-step acceptance workflow against the API."""

import pytest
from fastapi.testclient import TestClient

from backend.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_e2e_demo_workflow(client):
    # STEP 1: dashboard / health — system online
    health = client.get("/health").json()
    assert health["status"] in ("healthy", "degraded")

    # STEP 2: cash position
    r = client.post("/api/chat", json={"message": "What is my current cash position?", "session_id": "demo"})
    b = r.json()
    assert b["success"] and "get_cash_position" in b["tools_used"]
    assert b["facts"]["cash_position"]["net_cash"] is not None

    # STEP 3: can I afford ₹300,000 for 36 months?
    r = client.post("/api/chat", json={"message": "Can I afford a ₹300,000 loan for 36 months?", "session_id": "demo"})
    b = r.json()
    assert b["success"]
    assert any(t in b["tools_used"] for t in ("calculate_loan", "calculate_dti", "get_financial_baseline"))
    assert b["facts"]["loan"]["amount"] == 300000
    assert b["facts"]["loan"]["tenure_months"] == 36

    # STEP 4: what if I reduce to ₹200,000?
    r = client.post("/api/chat", json={"message": "What if I reduce the loan to ₹200,000?", "session_id": "demo"})
    b = r.json()
    assert b["success"] and "run_scenario" in b["tools_used"]

    # STEP 5: compare HDFC and ICICI
    r = client.post("/api/chat", json={"message": "Compare HDFC and ICICI.", "session_id": "demo"})
    b = r.json()
    assert b["success"] and "compare_loan_offers" in b["tools_used"]
    assert len(b["facts"].get("offers", [])) >= 1

    # STEP 6: how is RELIANCE performing?
    r = client.post("/api/chat", json={"message": "How is RELIANCE performing?", "session_id": "demo"})
    b = r.json()
    assert b["success"] and "get_quote" in b["tools_used"]
    assert b["facts"]["market"]["symbol"] == "RELIANCE"
    assert b["facts"]["market"]["trend"] in ("UPTREND", "DOWNTREND", "NEUTRAL")

    # STEP 7: inject ₹80,000 debit -> Risk Observer -> alerts
    r = client.post("/api/events/inject", json={"account_id": "ACC001", "amount": 80000,
                                                "description": "LARGE DEBIT", "type": "DEBIT"})
    inj = r.json()
    assert any(e["event"] == "risk_alert" for e in inj["events"])

    # STEP 8: Analyze impact -> updated cash / health / affordability / risk warning
    a = client.post("/api/events/analyze", json={"account_id": "ACC001", "amount": 80000}).json()
    assert a["health"]["overall_score"] >= 0
    assert "net_cash" in a["snapshot"]
    assert len(a["risk"]["warnings"]) >= 1
