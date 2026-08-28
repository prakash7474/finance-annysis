"""Unit tests for the deterministic financial health engine."""

from health_engine import (
    HealthScoreConfig,
    cash_score_component,
    compute_health_score,
    dti_score_component,
    emi_score_component,
    liquidity_score_component,
)


def test_dti_bands():
    cfg = HealthScoreConfig()
    assert dti_score_component(0.20, cfg) == 100.0
    assert 80 < dti_score_component(0.35, cfg) < 90
    assert 50 < dti_score_component(0.45, cfg) < 60
    assert dti_score_component(0.60, cfg) == 15.0


def test_emi_score_uses_dti_bands():
    cfg = HealthScoreConfig()
    assert emi_score_component(0.25, cfg) == 100.0
    assert dti_score_component(0.25, cfg) == emi_score_component(0.25, cfg)


def test_cash_score_positive_savings():
    assert cash_score_component(0.30) == 100.0
    assert cash_score_component(0.0) == 100.0


def test_cash_score_negative_savings():
    assert cash_score_component(-0.2) < 40


def test_liquidity_score():
    cfg = HealthScoreConfig()
    assert liquidity_score_component(0.0, cfg) == 10.0
    assert liquidity_score_component(1.5, cfg) == 50.0  # 1.5/3 -> 50
    assert liquidity_score_component(6.0, cfg) == 100.0


def test_healthy_profile():
    """A healthy profile (low debt, high savings, runway) scores high."""
    result = compute_health_score(
        monthly_income=100000, existing_emi=15000, net_cash=400000,
        total_credit=120000, total_debit=30000,
    )
    assert result["overall_score"] >= 70
    assert result["risk_level"] in ("HEALTHY", "MODERATE")


def test_stressed_profile():
    """A stressed profile (huge debt vs low income) scores low and flags warning."""
    result = compute_health_score(
        monthly_income=40000, existing_emi=30000, net_cash=-5000,
        total_credit=40000, total_debit=50000,
    )
    assert result["overall_score"] < 50
    assert result["risk_level"] in ("HIGH", "CRITICAL")
    assert len(result["warnings"]) > 0


def test_zero_income_handled():
    result = compute_health_score(
        monthly_income=0, existing_emi=10000, net_cash=0,
        total_credit=0, total_debit=0,
    )
    assert result["overall_score"] >= 0
    assert result["risk_level"] in ("HIGH", "CRITICAL")


def test_new_emi_increases_burden():
    base = compute_health_score(80000, 22300, 50000, 100000, 60000)
    with_loan = compute_health_score(80000, 22300, 50000, 100000, 60000, new_emi=9964)
    assert with_loan["dti_ratio"] > base["dti_ratio"]
    assert with_loan["overall_score"] < base["overall_score"]


def test_custom_weights():
    cfg = HealthScoreConfig(weights={"dti": 1.0, "cash": 0.0, "emi": 0.0, "liquidity": 0.0})
    result = compute_health_score(100000, 10000, 50000, 100000, 50000, config=cfg)
    assert result["overall_score"] == round(result["dti_score"], 1)
