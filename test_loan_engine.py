"""
test_loan_engine.py - Unit tests for loan_engine.py

Run with: python -m pytest test_loan_engine.py -v
"""

import json
from pathlib import Path

from loan_engine import (
    calculate_emi,
    total_interest_and_cost,
    assess_loan_risk,
    compare_loan_offers,
    format_loan_analysis,
    format_loan_comparison,
)


# ──────────────────────────────────────────────────────────────────────────────
# EMI Calculation Tests
# ──────────────────────────────────────────────────────────────────────────────

def test_emi_basic():
    """Known example: 100000 @ 12% for 12 months."""
    principal = 100_000
    rate = 12.0
    tenure = 12
    emi = calculate_emi(principal, rate, tenure)
    # Expected EMI ~ 8884.88
    assert 8880 < emi < 8890


def test_emi_zero_rate():
    """Zero interest should return principal / tenure."""
    principal = 120_000
    rate = 0.0
    tenure = 12
    emi = calculate_emi(principal, rate, tenure)
    assert abs(emi - (principal / tenure)) < 1e-6


def test_emi_high_rate():
    """Test with high interest rate."""
    emi = calculate_emi(500_000, 18.0, 24)
    assert emi > 0
    # Total payment should be more than principal
    total = emi * 24
    assert total > 500_000


def test_emi_long_tenure():
    """Long tenure should reduce EMI."""
    emi_36 = calculate_emi(200_000, 12.0, 36)
    emi_60 = calculate_emi(200_000, 12.0, 60)
    assert emi_60 < emi_36


def test_emi_invalid_inputs():
    """Zero tenure should return 0; zero rate returns principal/tolerance."""
    assert calculate_emi(100_000, 12, 0) == 0.0
    assert calculate_emi(100_000, 0, 0) == 0.0
    # Zero rate returns principal / tenure
    assert abs(calculate_emi(100_000, 0, 12) - (100_000 / 12)) < 1e-6


# ──────────────────────────────────────────────────────────────────────────────
# Total Cost Tests
# ──────────────────────────────────────────────────────────────────────────────

def test_total_cost_with_fee():
    """Verify total cost = total payment + processing fee."""
    principal = 200_000
    rate = 11.5
    tenure = 36
    proc_fee_pct = 1.0
    metrics = total_interest_and_cost(principal, rate, tenure, proc_fee_pct)

    assert metrics["processing_fee"] == principal * (proc_fee_pct / 100.0)
    assert metrics["total_cost"] > principal
    assert metrics["total_interest"] > 0
    assert metrics["total_cost"] == metrics["total_payment"] + metrics["processing_fee"]


def test_total_cost_no_fee():
    """Total cost without fees should equal total payment."""
    metrics = total_interest_and_cost(100_000, 12.0, 12)
    assert metrics["processing_fee"] == 0.0
    assert metrics["total_cost"] == metrics["total_payment"]


def test_total_interest_positive():
    """Interest should always be positive for positive rates."""
    metrics = total_interest_and_cost(300_000, 10.0, 60)
    assert metrics["total_interest"] > 0
    assert metrics["total_cost"] > 300_000


# ──────────────────────────────────────────────────────────────────────────────
# Risk Assessment Tests
# ──────────────────────────────────────────────────────────────────────────────

def test_high_emi_income_ratio():
    """High burden: large loan on low income with existing EMI."""
    result = assess_loan_risk(
        principal=500_000,
        annual_rate_pct=14.0,
        tenure_months=24,
        monthly_income=50_000,
        existing_monthly_emi=10_000,
    )
    # EMI ~24,868 + existing 10,000 = 34,868 / 50,000 = 69.7%
    assert result["emi_income_ratio"] > 0.5
    assert result["risk_level"] == "HIGH"
    assert any(f["code"] == "HIGH_EMI_INCOME_RATIO" for f in result["risk_flags"])


def test_moderate_interest_rate():
    """Moderate interest rate triggers LOW severity flag."""
    result = assess_loan_risk(
        principal=200_000,
        annual_rate_pct=12.5,
        tenure_months=36,
        monthly_income=100_000,
    )
    assert any(
        f["code"] in ("MODERATE_INTEREST_RATE", "HIGH_INTEREST_RATE")
        for f in result["risk_flags"]
    )


def test_low_risk_scenario():
    """Low rate, long tenure, high income = low risk."""
    result = assess_loan_risk(
        principal=150_000,
        annual_rate_pct=10.5,
        tenure_months=36,
        monthly_income=120_000,
    )
    assert result["emi_income_ratio"] < 0.4
    assert result["risk_level"] in ("LOW", "MEDIUM")


def test_short_tenure_high_burden():
    """Short tenure + high EMI ratio triggers SHORT_TENURE_HIGH_BURDEN."""
    result = assess_loan_risk(
        principal=200_000,
        annual_rate_pct=15.0,
        tenure_months=12,
        monthly_income=40_000,
    )
    # EMI at 15% for 12 months on 200k is ~18,041 => 45% ratio
    assert any(f["code"] == "SHORT_TENURE_HIGH_BURDEN" for f in result["risk_flags"])


def test_existing_emi_adds_burden():
    """Existing EMI should increase the ratio and risk."""
    without_emi = assess_loan_risk(
        principal=200_000, annual_rate_pct=12.0, tenure_months=36,
        monthly_income=80_000, existing_monthly_emi=0,
    )
    with_emi = assess_loan_risk(
        principal=200_000, annual_rate_pct=12.0, tenure_months=36,
        monthly_income=80_000, existing_monthly_emi=20_000,
    )
    assert with_emi["emi_income_ratio"] > without_emi["emi_income_ratio"]


def test_zero_income():
    """Zero income should give inf ratio and HIGH risk."""
    result = assess_loan_risk(
        principal=100_000, annual_rate_pct=12.0, tenure_months=12,
        monthly_income=0,
    )
    assert result["emi_income_ratio"] == float("inf")
    assert result["risk_level"] == "HIGH"


# ──────────────────────────────────────────────────────────────────────────────
# Loan Comparison Tests
# ──────────────────────────────────────────────────────────────────────────────

def test_compare_loans_ranking():
    """Results should be sorted by total_cost ascending."""
    offers = [
        {"offer_id": "A", "bank": "Bank A", "interest_rate": 12.0, "tenure_months": 24, "processing_fee_pct": 1.0},
        {"offer_id": "B", "bank": "Bank B", "interest_rate": 10.0, "tenure_months": 36, "processing_fee_pct": 0.5},
    ]
    results = compare_loan_offers(200_000, offers, 80_000)

    for i in range(len(results) - 1):
        assert results[i]["total_cost"] <= results[i + 1]["total_cost"]


def test_compare_loans_fields():
    """All results should have required fields."""
    offers = [
        {"offer_id": "X", "bank": "X Bank", "interest_rate": 11.0, "tenure_months": 36},
    ]
    results = compare_loan_offers(100_000, offers, 50_000)
    assert len(results) == 1
    r = results[0]
    for key in ("emi", "total_cost", "total_interest", "risk_level", "risk_flags", "bank"):
        assert key in r


def test_compare_with_mock_loan_offers():
    """Integration test with actual mock_data.json."""
    data_file = Path(__file__).parent / "mock_data.json"
    data = json.loads(data_file.read_text(encoding="utf-8"))
    offers = data["loan_offers"]

    results = compare_loan_offers(250_000, offers, 90_000)
    assert len(results) >= 2

    for r in results:
        assert "emi" in r
        assert "total_cost" in r
        assert "risk_level" in r
        assert "risk_flags" in r


# ──────────────────────────────────────────────────────────────────────────────
# Formatting Tests
# ──────────────────────────────────────────────────────────────────────────────

def test_format_loan_analysis():
    """format_loan_analysis should produce readable output."""
    result = assess_loan_risk(300_000, 12.0, 36, 80_000)
    output = format_loan_analysis(result)
    assert "EMI:" in output
    assert "Risk level:" in output
    assert "Suggestion:" in output


def test_format_loan_comparison():
    """format_loan_comparison should produce a table."""
    offers = [
        {"offer_id": "A", "bank": "HDFC", "interest_rate": 11.5, "tenure_months": 36, "processing_fee_pct": 1.0},
        {"offer_id": "B", "bank": "ICICI", "interest_rate": 12.25, "tenure_months": 24, "processing_fee_pct": 1.5},
    ]
    results = compare_loan_offers(200_000, offers, 80_000)
    output = format_loan_comparison(results, 200_000, 80_000, 0)
    assert "Rank" in output
    assert "HDFC" in output
    assert "ICICI" in output
    assert "Best by total cost:" in output
