"""Unit tests for the deterministic intent router."""

from backend.orchestrator.router import (
    detect_intent,
    parse_entities,
    _parse_amount,
    _parse_rate,
    _parse_tenure,
    _parse_symbol,
    _parse_salary_change,
    DOMAIN_FINANCE,
    DOMAIN_LOAN,
    DOMAIN_MARKET,
    DOMAIN_MULTI,
    DOMAIN_GENERAL,
)


def test_finance_intent():
    result, _ = detect_intent("What is my balance?")
    assert result.intent == DOMAIN_FINANCE
    assert "get_cash_position" in result.required_tools


def test_loan_intent():
    result, _ = detect_intent("Calculate a 3 lakh loan")
    assert result.intent == DOMAIN_LOAN
    assert "calculate_loan" in result.required_tools


def test_market_intent():
    result, _ = detect_intent("How is TCS performing?")
    assert result.intent == DOMAIN_MARKET
    assert "get_quote" in result.required_tools


def test_multi_domain_intent():
    result, _ = detect_intent("Can I afford a loan based on my current salary and cash?")
    assert result.intent == DOMAIN_MULTI
    for tool in ("get_financial_baseline", "calculate_dti", "calculate_loan"):
        assert tool in result.required_tools


def test_general_intent():
    result, _ = detect_intent("Hello")
    assert result.intent == DOMAIN_GENERAL
    assert result.required_tools == []


def test_parse_amount_lakh():
    assert _parse_amount("3 lakh") == 300000
    assert _parse_amount("2 lac loan") == 200000


def test_parse_amount_numeric():
    assert _parse_amount("300000") == 300000


def test_parse_rate():
    assert _parse_rate("12%") == 12.0


def test_parse_tenure():
    assert _parse_tenure("36 months") == 36
    assert _parse_tenure("2 years") == 24


def test_parse_symbol():
    assert _parse_symbol("how is TCS doing") == "TCS"
    assert _parse_symbol("price of RELIANCE") == "RELIANCE"


def test_parse_salary_change():
    assert _parse_salary_change("salary falls by 10%") == -10.0
    assert _parse_salary_change("income drops by 15%") == -15.0
