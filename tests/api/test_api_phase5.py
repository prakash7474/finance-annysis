"""API tests for Phase 5 intelligence endpoints."""

import pytest
from fastapi.testclient import TestClient

from backend.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_finance_health(client):
    r = client.get("/api/finance/health")
    assert r.status_code == 200
    body = r.json()
    assert "score" in body and "status" in body
    assert body["score"] >= 0
    for k in ("liquidity_score", "debt_score", "expense_score", "savings_score"):
        assert k in body


def test_anomalies(client):
    r = client.get("/api/finance/anomalies")
    assert r.status_code == 200
    assert "anomalies" in r.json()


def test_cashflow_forecast(client):
    r = client.get("/api/finance/forecast/cashflow?days=30")
    assert r.status_code == 200
    body = r.json()
    for k in ("projected_balance", "projected_income", "projected_expenses", "projected_emi", "confidence"):
        assert k in body


def test_spending_forecast(client):
    r = client.get("/api/finance/forecast/spending?days=30")
    assert r.status_code == 200
    assert "spending" in r.json()


def test_goals_list_and_create(client):
    r = client.get("/api/finance/goals")
    assert r.status_code == 200
    r = client.post("/api/finance/goals", json={
        "target_amount": 200000, "months_remaining": 8, "current_saved_amount": 40000, "name": "Test Goal"})
    assert r.status_code == 201
    goal = r.json()
    assert goal["required_monthly_saving"] > 0
    assert "goal_id" in goal


def test_scenario(client):
    r = client.post("/api/finance/scenario", json={
        "salary_change_percentage": -10, "expense_change_percentage": 15, "new_loan_amount": 200000})
    assert r.status_code == 200
    body = r.json()
    assert body["baseline"]["net_cash"] >= 0
    assert body["simulated"]["monthly_income"] < body["baseline"]["monthly_income"]
    assert "scenario_id" in body


def test_debt(client):
    r = client.get("/api/finance/debt")
    assert r.status_code == 200
    assert "debt" in r.json()


def test_alerts(client):
    r = client.get("/api/finance/alerts")
    assert r.status_code == 200
    assert "alerts" in r.json()


def test_recommendations_and_approval(client):
    r = client.get("/api/finance/recommendations")
    assert r.status_code == 200
    recs = r.json()["recommendations"]
    assert len(recs) >= 1
    rec = recs[0]
    rid = rec["recommendation_id"]

    ap = client.post(f"/api/finance/recommendations/{rid}/approve")
    assert ap.status_code == 200
    assert ap.json()["status"] == "APPROVED"

    # Cannot approve twice.
    ap2 = client.post(f"/api/finance/recommendations/{rid}/approve")
    assert ap2.status_code == 409


def test_recommendation_reject(client):
    r = client.get("/api/finance/recommendations")
    rid = r.json()["recommendations"][1]["recommendation_id"]
    rj = client.post(f"/api/finance/recommendations/{rid}/reject")
    assert rj.status_code == 200
    assert rj.json()["status"] == "REJECTED"


def test_audit_lookup(client):
    trace = client.post("/api/finance/scenario", json={"salary_change_percentage": -10}).json()["trace_id"]
    r = client.get(f"/api/finance/audit/{trace}")
    assert r.status_code == 200
    assert any(e["operation"] == "financial_scenario" for e in r.json()["audit"])


def test_audit_not_found(client):
    r = client.get("/api/finance/audit/DOES_NOT_EXIST")
    assert r.status_code == 404


def test_emit_alerts_to_sse(client):
    r = client.post("/api/finance/alerts/emit")
    assert r.status_code == 200
    recent = client.get("/api/events/recent?limit=50").json()["events"]
    assert any(e["event"] == "financial_alert" for e in recent)


def test_narrate_intelligence(client):
    r = client.post("/api/finance/narrate", json={"message": "Summarise my health"})
    assert r.status_code == 200
    assert "message" in r.json()


def test_health_score_is_deterministic(client):
    a = client.get("/api/finance/health").json()["score"]
    b = client.get("/api/finance/health").json()["score"]
    assert a == b
