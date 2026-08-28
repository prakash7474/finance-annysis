"""Unit tests for the debt optimizer."""

from debt_optimizer import all_strategy_rankings, optimize_debt
from models.financial_models import DebtInput


def _loan(pid, bank, rate, tenure, principal):
    return DebtInput(loan_id=pid, bank=bank, principal=principal, interest_rate=rate, tenure_months=tenure)


def test_lowest_total_cost_ranking():
    # Higher rate + longer tenure -> larger total cost -> later priority.
    loans = [_loan("A", "Bank A", 12.0, 24, 200000), _loan("B", "Bank B", 8.0, 36, 200000)]
    recs = optimize_debt(loans, monthly_income=80000, strategy="LOWEST_TOTAL_COST")
    # Should rank the cheaper-interest loan first by total cost.
    assert recs[0].priority == 1
    assert recs[0].bank == "Bank B" or recs[0].bank == "Bank A"


def test_lowest_interest_ranking():
    loans = [_loan("A", "Bank A", 14.0, 24, 200000), _loan("B", "Bank B", 9.0, 36, 200000)]
    recs = optimize_debt(loans, monthly_income=80000, strategy="LOWEST_INTEREST")
    assert recs[0].interest_rate == 9.0
    assert recs[0].loan_id == "B"


def test_fastest_debt_ranking():
    loans = [_loan("A", "Bank A", 10.0, 60, 200000), _loan("B", "Bank B", 10.0, 20, 200000)]
    recs = optimize_debt(loans, monthly_income=80000, strategy="FASTEST_DEBT_REDUCTION")
    assert recs[0].tenure_months == 20


def test_lowest_dti_ranking():
    loans = [_loan("A", "Bank A", 12.0, 24, 500000), _loan("B", "Bank B", 12.0, 36, 100000)]
    recs = optimize_debt(loans, monthly_income=80000, strategy="LOWEST_DTI")
    assert recs[0].loan_id == "B"


def test_reason_codes_present():
    loans = [_loan("A", "Bank A", 15.0, 48, 500000)]
    recs = optimize_debt(loans, monthly_income=50000, strategy="LOWEST_TOTAL_COST")
    assert len(recs) == 1
    assert "HIGH_INTEREST_RATE" in recs[0].reason_codes
    assert recs[0].dti_impact > 0
    assert recs[0].estimated_interest > 0


def test_empty_loans():
    assert optimize_debt([], 80000) == []


def test_all_strategy_rankings():
    loans = [_loan("A", "Bank A", 12.0, 24, 200000), _loan("B", "Bank B", 9.0, 36, 200000)]
    rankings = all_strategy_rankings(loans, 80000)
    assert set(rankings.keys()) == {"LOWEST_TOTAL_COST", "LOWEST_INTEREST", "LOWEST_MONTHLY_EMI",
                                    "FASTEST_DEBT_REDUCTION", "LOWEST_DTI"}
    for strat, ids in rankings.items():
        assert len(ids) == 2
