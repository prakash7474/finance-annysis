"""API tests for the AI Trading Allocation add-on (paper only)."""

import pytest
from fastapi.testclient import TestClient

from backend.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_accounts_list(client):
    r = client.get("/api/trading/accounts")
    assert r.status_code == 200
    assert len(r.json()["accounts"]) >= 3


def test_account_unknown_returns_not_linked(client):
    r = client.get("/api/trading/accounts/NOPE")
    assert r.status_code == 404
    assert r.json()["error_code"] == "ACCOUNT_NOT_LINKED"


def test_market_facts(client):
    assert client.get("/api/trading/market/RELIANCE/latest").json()["price"] > 0
    assert "sma" in client.get("/api/trading/market/RELIANCE/sma?window=20").json()
    assert "realized_volatility" in client.get("/api/trading/market/RELIANCE/volatility").json()
    assert client.get("/api/trading/trend/RELIANCE").json()["trend"] in ("UPTREND", "DOWNTREND", "NEUTRAL")


def test_allocate_conservative_resized(client):
    r = client.post("/api/trading/allocate",
                    json={"account_id": "ACC_CONSERVATIVE", "symbol": "RELIANCE"})
    assert r.status_code == 200
    body = r.json()
    assert body["decision"]["status"] in ("RESIZED", "REJECTED")
    assert body["decision"]["status"] == "RESIZED"
    # The oversized LLM proposal must be capped by the position-size rule.
    assert "max_position_size" in body["adjusted_for"]
    assert body["trace_id"].startswith("TRACE_")
    assert body["proposal"]["proposed_quantity"] > body["decision"]["final_quantity"]


def test_override_limits_still_blocked(client):
    r = client.post("/api/trading/allocate",
                    json={"account_id": "ACC_CONSERVATIVE", "symbol": "RELIANCE", "override_limits": True})
    body = r.json()
    assert body["decision"]["status"] in ("RESIZED", "REJECTED")
    # "ignore the limits / go all in" must be capped, not executed at full size.
    assert body["decision"]["final_quantity"] <= body["proposal"]["proposed_quantity"]


def test_profiles_differ(client):
    cons = client.post("/api/trading/allocate", json={"account_id": "ACC_CONSERVATIVE", "symbol": "RELIANCE"}).json()
    aggr = client.post("/api/trading/allocate", json={"account_id": "ACC_AGGRESSIVE", "symbol": "RELIANCE"}).json()
    assert cons["decision"]["final_value"] != aggr["decision"]["final_value"]


def test_paper_order_fills_and_updates(client):
    before = client.get("/api/trading/accounts/ACC_CONSERVATIVE").json()["cash_balance"]
    r = client.post("/api/trading/orders",
                    json={"account_id": "ACC_CONSERVATIVE", "symbol": "RELIANCE", "side": "BUY", "quantity": 3})
    assert r.status_code == 200
    body = r.json()
    assert body["order"]["status"] == "FILLED"
    assert body["snapshot"]["cash_balance"] < before
    # Order status reflects FILLED.
    oid = body["order"]["order_id"]
    status = client.get(f"/api/trading/orders/{oid}").json()
    assert status["status"] == "FILLED"


def test_oversized_order_defense_in_depth(client):
    r = client.post("/api/trading/orders",
                    json={"account_id": "ACC_CONSERVATIVE", "symbol": "RELIANCE", "side": "BUY", "quantity": 100000})
    assert r.status_code == 409
    assert r.json()["error_code"] == "INSUFFICIENT_CASH"


def test_trace_detail_and_list(client):
    alloc = client.post("/api/trading/allocate", json={"account_id": "ACC_CONSERVATIVE", "symbol": "RELIANCE"}).json()
    trace_id = alloc["trace_id"]
    detail = client.get(f"/api/trading/trace/{trace_id}")
    assert detail.status_code == 200
    assert any(e["operation"] == "allocation_decision" for e in detail.json()["audit"])
    assert any(e["operation"] in ("allocation_decision", "paper_order")
               for e in client.get("/api/trading/trace").json()["trace_items"])
