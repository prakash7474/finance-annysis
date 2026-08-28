"""Unit tests for the Phase 5 financial health score."""

from health_engine import compute_financial_health


def test_excellent_health():
    h = compute_financial_health(
        monthly_income=200000, monthly_expenses=40000, existing_emi=10000, net_cash=600000)
    assert h["score"] >= 85
    assert h["status"] == "EXCELLENT"


def test_healthy_health():
    h = compute_financial_health(
        monthly_income=100000, monthly_expenses=30000, existing_emi=15000, net_cash=200000)
    assert h["status"] in ("EXCELLENT", "HEALTHY", "MODERATE")
    assert h["score"] >= 45


def test_critical_health():
    h = compute_financial_health(
        monthly_income=50000, monthly_expenses=60000, existing_emi=40000, net_cash=-10000)
    assert h["status"] == "CRITICAL"
    assert h["score"] < 40
    assert any("critical" in r.lower() for r in h["reasons"])
    assert any("negative" in r.lower() for r in h["reasons"])


def test_dti_threshold():
    h = compute_financial_health(
        monthly_income=100000, monthly_expenses=20000, existing_emi=0, net_cash=100000, new_emi=60000)
    # DTI = 60% -> debt component critical + reason.
    assert h["dti"] >= 0.5
    assert any("critical" in r.lower() or "elevated" in r.lower() for r in h["reasons"])


def test_liquidity_threshold():
    h = compute_financial_health(
        monthly_income=80000, monthly_expenses=30000, existing_emi=22300, net_cash=-5000)
    assert h["liquidity_score"] <= 20
    assert any("negative" in r.lower() or "runway" in r.lower() for r in h["reasons"])


def test_status_mapping_counts():
    # A strongly negative forecast balance should surface a reason.
    h = compute_financial_health(
        monthly_income=80000, monthly_expenses=30000, existing_emi=22300, net_cash=10000, forecast_balance=-5000)
    assert any("projected cash balance is negative" in r.lower() for r in h["reasons"])
