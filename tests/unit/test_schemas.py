"""Unit tests for Pydantic schema validation (malformed input rejected)."""

import pytest
from pydantic import ValidationError as PydanticValidationError

from backend.schemas.chat import ChatRequest, ChatResponse, IntentResult
from backend.schemas.loans import LoanRequest, ScenarioRequest


def test_chat_request_requires_message():
    with pytest.raises(PydanticValidationError):
        ChatRequest(message="")
    assert ChatRequest(message="hi").message == "hi"
    assert ChatRequest(message="hi", session_id="s").session_id == "s"


def test_intent_result_structured():
    result = IntentResult(intent="MULTI_DOMAIN", required_tools=["get_cash_position"], confidence=0.9)
    assert result.intent == "MULTI_DOMAIN"
    assert len(result.required_tools) == 1


def test_chat_response_shape():
    resp = ChatResponse(success=True, session_id="s", trace_id="t", message="m",
                        tools_used=["a"], facts={}, risk={})
    assert resp.success is True
    assert resp.trace_id == "t"


def test_loan_request_rejects_negative_amount():
    with pytest.raises(PydanticValidationError):
        LoanRequest(amount=-50000, rate=12, tenure_months=36, monthly_income=80000)


def test_loan_request_rejects_zero_tenure():
    with pytest.raises(PydanticValidationError):
        LoanRequest(amount=100000, rate=12, tenure_months=0, monthly_income=80000)


def test_loan_request_rejects_high_rate():
    with pytest.raises(PydanticValidationError):
        LoanRequest(amount=100000, rate=120, tenure_months=12, monthly_income=80000)


def test_loan_request_valid():
    req = LoanRequest(amount=300000, rate=12.5, tenure_months=36, monthly_income=80000, existing_emi=22300)
    assert req.amount == 300000


def test_scenario_request_rejects_invalid():
    with pytest.raises(PydanticValidationError):
        ScenarioRequest(loan_amount=-1, tenure_months=36, rate=12, monthly_income=80000)
    with pytest.raises(PydanticValidationError):
        ScenarioRequest(loan_amount=300000, tenure_months=0, rate=12, monthly_income=80000)
