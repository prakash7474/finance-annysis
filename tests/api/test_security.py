"""Security tests: secrets stay server-side, invalid input is rejected."""

import pytest
from fastapi.testclient import TestClient

from backend.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_api_key_not_returned_by_health(client):
    body = client.get("/health").text
    low = body.lower()
    assert "gemini_api_key" not in low
    assert "api_key" not in low.lower()


def test_api_key_not_returned_by_chat(client):
    body = client.post("/api/chat", json={"message": "What is my balance?"}).text
    assert "gemini_api_key" not in body.lower()


def test_api_key_not_in_health_details(client):
    data = client.get("/health").json()
    for svc in data["services"].values():
        assert not any(k in str(svc).lower() for k in ("api_key", "token", "secret", "password"))


def test_invalid_loan_rejected(client):
    for payload, code in [
        ({"amount": -50000, "rate": 12, "tenure_months": 36, "monthly_income": 80000}, 422),
        ({"amount": 100000, "rate": 12, "tenure_months": 0, "monthly_income": 80000}, 422),
        ({"amount": 100000, "rate": 12.5, "tenure_months": 36, "monthly_income": -1}, 422),
    ]:
        r = client.post("/api/loan/analyze", json=payload)
        assert r.status_code == code


def test_oversized_chat_rejected(client):
    r = client.post("/api/chat", json={"message": "a" * 9000})
    assert r.status_code == 422


def test_unknown_tool_not_exposed(client):
    """The frontend tool listing must only contain known tools, no secrets."""
    r = client.get("/api/chat/tools")
    assert r.status_code == 200
    names = [t["name"] for t in r.json()["tools"]]
    assert "get_cash_position" in names
    assert all("key" not in n and "token" not in n for n in names)


def test_error_response_has_no_stacktrace(client):
    # An oversized/malformed request returns a structured error, never a traceback.
    r = client.post("/api/chat", json={"message": ""})
    assert r.status_code == 422
    assert "Traceback" not in r.text and "File \"" not in r.text and "line " not in r.text
