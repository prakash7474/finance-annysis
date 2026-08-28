"""Unit tests for the cash-flow / spending forecast engine."""

from forecast_engine import forecast_cash_flow, forecast_spending


def test_known_deterministic_30day():
    f = forecast_cash_flow(94687.50, 80000, 30000, 22300, 30)
    assert abs(f.projected_balance - (94687.50 + 80000 - 30000 - 22300)) < 0.01
    assert f.days == 30
    assert f.confidence == 0.5


def test_7day_forecast():
    f = forecast_cash_flow(100000, 80000, 30000, 22300, 7)
    factor = 7 / 30
    assert abs(f.projected_balance - (100000 + (80000 - 30000 - 22300) * factor)) < 0.01
    assert f.days == 7
    assert f.confidence == 0.7


def test_negative_balance_risk_critical():
    f = forecast_cash_flow(1000, 30000, 50000, 20000, 30)
    assert f.projected_balance < 0
    assert f.risk_level == "CRITICAL"


def test_no_transactions_spending():
    assert forecast_spending([]) == []


def test_missing_income_handled():
    f = forecast_cash_flow(10000, 0, 3000, 1000, 30)
    assert isinstance(f.projected_balance, float)
    assert f.projected_income == 0.0


def test_spending_forecast_per_category():
    txns = [
        {"date": "2026-08-01", "type": "DEBIT", "category": "FOOD", "amount": 300},
        {"date": "2026-08-02", "type": "DEBIT", "category": "FOOD", "amount": 300},
        {"date": "2026-08-03", "type": "DEBIT", "category": "FOOD", "amount": 300},
        {"date": "2026-08-04", "type": "DEBIT", "category": "TRANSPORT", "amount": 500},
    ]
    out = forecast_spending(txns, days=30)
    cats = {s.category for s in out}
    assert "FOOD" in cats and "TRANSPORT" in cats
    food = next(s for s in out if s.category == "FOOD")
    assert food.projected_amount > 0
    assert food.historical_average > 0


def test_spending_forecast_risk_sensitive_to_income():
    txns = [{"date": "2026-08-01", "type": "DEBIT", "category": "RENT", "amount": 50000},
            {"date": "2026-08-02", "type": "DEBIT", "category": "RENT", "amount": 50000}]
    out = forecast_spending(txns, days=30, monthly_income=80000)
    assert out[0].risk_level == "HIGH"
