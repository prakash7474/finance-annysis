"""Unit tests for the smart alert engine."""

from alert_engine import SEVERITY_RANK, generate_financial_alerts


def test_transaction_anomaly_alert():
    alerts = generate_financial_alerts({"anomalies": [{"severity": "HIGH", "category": "FOOD", "reason": "Outlier"}]})
    assert any(a.category == "TRANSACTION_ANOMALY" for a in alerts)


def test_low_liquidity_alert():
    alerts = generate_financial_alerts({"forecast": {"projected_balance": 10000, "risk_level": "MEDIUM"}})
    assert any(a.category == "LOW_LIQUIDITY" for a in alerts)


def test_high_dti_alert():
    alerts = generate_financial_alerts({"dti": 0.55})
    assert any(a.category == "HIGH_DTI" for a in alerts)
    assert any(a.severity == "CRITICAL" for a in alerts)


def test_goal_shortfall_alert():
    alerts = generate_financial_alerts({"goals": [{"name": "Fund", "monthly_shortfall": 5000}]})
    assert any(a.category == "GOAL_SHORTFALL" for a in alerts)


def test_market_change_alert():
    alerts = generate_financial_alerts({"market_alerts": [{"symbol": "TCS", "alert_type": "TREND_FLIP",
                                                           "severity": "MEDIUM", "message": "flip"}]})
    assert any(a.category == "MARKET_CHANGE" for a in alerts)


def test_alerts_priority_ordered():
    alerts = generate_financial_alerts({
        "dti": 0.6, "net_cash": -5000,
        "anomalies": [{"severity": "HIGH", "category": "FOOD", "reason": "x"}],
        "goals": [{"name": "g", "monthly_shortfall": 3000}],
    })
    ranks = [SEVERITY_RANK[a.severity] for a in alerts]
    assert ranks == sorted(ranks)
    assert alerts[0].severity == "CRITICAL"


def test_each_alert_has_required_fields():
    alerts = generate_financial_alerts({"dti": 0.6})
    for a in alerts:
        for field in ("alert_id", "timestamp", "category", "severity", "title", "description", "source"):
            assert field in a.model_dump()
